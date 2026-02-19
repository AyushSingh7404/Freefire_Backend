"""
Wallet service: all coin credit/debit operations.

CRITICAL: Every operation that modifies balance uses SELECT FOR UPDATE to lock
the wallet row. This prevents race conditions where two concurrent requests
(e.g., double-clicking "Join Room") both read the same balance, both pass the
availability check, and both deduct — leaving the wallet in negative balance.

Locking order convention (to prevent deadlocks):
  ALWAYS lock wallet BEFORE locking room (in join_room, this order is respected).
  Never reverse this order in any code path.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.wallet import Wallet, Transaction
from app.models.user import User
from app.core.exceptions import InsufficientCoinsException, NotFoundException


def get_or_create_wallet(db: Session, user_id: str) -> Wallet:
    """
    Returns the user's wallet, creating one if it doesn't exist.
    Called during registration to ensure every user has a wallet.
    """
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0, locked_balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def get_wallet(db: Session, user_id: str) -> Wallet:
    """Get wallet, raise 404 if not found."""
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        raise NotFoundException("Wallet")
    return wallet


def credit_coins(
    db: Session,
    user_id: str,
    amount: int,
    description: str,
    reference: str = None,
) -> Transaction:
    """
    Credit coins to a user's wallet atomically.
    Uses SELECT FOR UPDATE to lock the wallet row during the transaction.
    """
    # Lock the wallet row to prevent concurrent modifications
    wallet = (
        db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
        .scalar_one_or_none()
    )
    if not wallet:
        raise NotFoundException("Wallet")

    wallet.balance += amount

    txn = Transaction(
        wallet_id=wallet.id,
        user_id=user_id,
        type="credit",
        amount=amount,
        description=description,
        reference=reference,
        status="completed",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def debit_coins(
    db: Session,
    user_id: str,
    amount: int,
    description: str,
    reference: str = None,
) -> Transaction:
    """
    Debit coins from a user's wallet atomically.
    Checks available balance (balance - locked_balance) before deducting.
    Raises InsufficientCoinsException if not enough available coins.
    """
    wallet = (
        db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
        .scalar_one_or_none()
    )
    if not wallet:
        raise NotFoundException("Wallet")

    available = wallet.balance - wallet.locked_balance
    if available < amount:
        raise InsufficientCoinsException(available=available, required=amount)

    wallet.balance -= amount

    txn = Transaction(
        wallet_id=wallet.id,
        user_id=user_id,
        type="debit",
        amount=amount,
        description=description,
        reference=reference,
        status="completed",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def get_transactions(
    db: Session,
    user_id: str,
    page: int = 1,
    limit: int = 20,
) -> tuple[int, list[Transaction]]:
    """
    Paginated transaction history for a user.
    Returns (total_count, list_of_transactions).
    """
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    total = query.count()
    transactions = (
        query.order_by(Transaction.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return total, transactions


def admin_credit_coins(
    db: Session,
    target_user_id: str,
    amount: int,
    reason: str,
    admin_id: str,
) -> Transaction:
    """
    Admin-initiated coin credit. Also logs the action to audit_logs.
    """
    txn = credit_coins(
        db,
        user_id=target_user_id,
        amount=amount,
        description=f"Admin credit: {reason}",
        reference=f"admin_{admin_id}",
    )
    # Audit log is written by the router using the middleware helper
    return txn


def admin_debit_coins(
    db: Session,
    target_user_id: str,
    amount: int,
    reason: str,
    admin_id: str,
) -> Transaction:
    """Admin-initiated coin debit."""
    txn = debit_coins(
        db,
        user_id=target_user_id,
        amount=amount,
        description=f"Admin debit: {reason}",
        reference=f"admin_{admin_id}",
    )
    return txn
