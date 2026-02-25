from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class WalletOut(BaseModel):
    """
    Closed coin economy: users have a single balance.
    No withdrawal, no TDS, no split between deposit vs winning coins.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    balance: int
    updated_at: datetime

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)

    @classmethod
    def from_wallet(cls, wallet) -> "WalletOut":
        return cls(
            id=str(wallet.id),
            user_id=str(wallet.user_id),
            balance=wallet.balance,
            updated_at=wallet.updated_at,
        )


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    amount: int
    description: str
    reference: Optional[str] = None
    status: str
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)


class TransactionListResponse(BaseModel):
    total: int
    page: int
    limit: int
    transactions: List[TransactionOut]


class PaymentInitiateRequest(BaseModel):
    """
    Initiate a Razorpay order using a CoinPackage ID.
    Frontend fetches available packages from GET /coin-packages,
    then sends the chosen package's ID here.
    """
    package_id: str     # UUID of the CoinPackage to purchase


class PaymentInitiateResponse(BaseModel):
    """Returned to frontend to open Razorpay checkout modal."""
    razorpay_order_id: str
    amount_paise: int         # Razorpay works in paise (rupees × 100)
    currency: str = "INR"
    coins: int
    razorpay_key_id: str      # frontend needs this to open the checkout


class PaymentVerifyRequest(BaseModel):
    """
    Frontend sends this after user completes Razorpay payment.
    All three fields come from Razorpay's checkout callback.
    """
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    coins: int                # coins to credit — must match the original order


class AdminWalletActionRequest(BaseModel):
    """Admin-initiated credit or debit."""
    user_id: str
    amount: int
    reason: str

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
