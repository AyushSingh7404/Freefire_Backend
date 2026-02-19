from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    balance: int
    locked_balance: int
    available_balance: int  # computed field: balance - locked_balance
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
            locked_balance=wallet.locked_balance,
            available_balance=wallet.balance - wallet.locked_balance,
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
    """Initiate a Razorpay order for coin purchase."""
    amount_inr: float   # in rupees (min ₹1)
    coins: int          # how many coins they're buying for that amount

    @field_validator("amount_inr")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v < 1:
            raise ValueError("Minimum payment is ₹1")
        return v

    @field_validator("coins")
    @classmethod
    def coins_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Must purchase at least 1 coin")
        return v


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
