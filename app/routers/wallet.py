"""
Wallet router: balance, transactions, and Razorpay payment flow.

Razorpay payment flow:
  1. POST /wallet/payment/initiate  → create Razorpay order, return order details
  2. [Frontend opens Razorpay checkout modal — user pays]
  3. POST /wallet/payment/verify    → verify HMAC signature → credit coins

The HMAC verification in step 3 is non-negotiable. Without it, anyone could
fake a payment by just sending random strings to the verify endpoint.
"""
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limiter import limiter
from app.models.user import User
from app.models.wallet import Transaction
from app.models.coin_package import CoinPackage
from app.schemas.wallet import (
    WalletOut,
    TransactionListResponse,
    TransactionOut,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentVerifyRequest,
)
from app.services import wallet_service
from app.services.razorpay_service import create_order, verify_payment_signature
from app.config import settings

router = APIRouter()


@router.get("", response_model=WalletOut)
def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's coin balance and locked balance."""
    wallet = wallet_service.get_wallet(db, str(current_user.id))
    return WalletOut.from_wallet(wallet)


@router.get("/transactions", response_model=TransactionListResponse)
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Paginated transaction history for the current user.
    Ordered newest-first. Max 100 per page.
    """
    total, transactions = wallet_service.get_transactions(
        db, str(current_user.id), page=page, limit=limit
    )
    return TransactionListResponse(
        total=total,
        page=page,
        limit=limit,
        transactions=[TransactionOut.model_validate(t) for t in transactions],
    )


@router.post("/payment/initiate", response_model=PaymentInitiateResponse)
@limiter.limit("10/minute")
def initiate_payment(
    request: Request,
    body: PaymentInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Razorpay order from a coin package ID.
    Frontend fetches packages from GET /coin-packages, user picks one,
    frontend sends the package UUID here.

    Returns:
      - razorpay_order_id: needed by frontend for checkout
      - amount_paise: the charge amount in paise
      - razorpay_key_id: public key for the Razorpay modal
      - coins: coins to credit on successful payment (from the package)
    """
    # Look up the package — must be active
    package = (
        db.query(CoinPackage)
        .filter(CoinPackage.id == body.package_id, CoinPackage.is_active == True)
        .first()
    )
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coin package not found or is no longer available.",
        )

    order = create_order(amount_inr=package.price_inr, coins=package.coins)
    return PaymentInitiateResponse(
        razorpay_order_id=order["id"],
        amount_paise=order["amount"],
        currency=order["currency"],
        coins=package.coins,
        razorpay_key_id=settings.razorpay_key_id,
    )


@router.post("/payment/verify")
@limiter.limit("10/minute")
def verify_payment(
    request: Request,
    body: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify Razorpay payment signature and credit coins.

    CRITICAL SECURITY STEP:
    The HMAC-SHA256 signature is verified using our Razorpay secret.
    If the signature doesn't match, the request is rejected — no coins credited.
    This prevents anyone from faking a successful payment.

    Idempotency: razorpay_payment_id is stored as the transaction reference.
    If the same payment_id arrives twice, the DB unique index on reference
    will prevent double-crediting (add this index to Transaction.reference if needed).
    """
    signature_valid = verify_payment_signature(
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        razorpay_signature=body.razorpay_signature,
    )

    if not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed. Invalid signature.",
        )

    # Check for duplicate payment (idempotency)
    duplicate = db.query(Transaction).filter(
        Transaction.reference == body.razorpay_payment_id
    ).first()
    if duplicate:
        return {
            "message": "Payment already processed.",
            "coins_credited": body.coins,
        }

    # Credit coins
    wallet_service.credit_coins(
        db,
        user_id=str(current_user.id),
        amount=body.coins,
        description=f"Coin purchase via Razorpay ({body.razorpay_order_id})",
        reference=body.razorpay_payment_id,  # stored for idempotency
    )

    return {
        "message": f"Payment successful! {body.coins} coins have been added to your wallet.",
        "coins_credited": body.coins,
    }
