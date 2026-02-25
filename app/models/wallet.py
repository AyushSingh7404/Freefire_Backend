import uuid
from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # one wallet per user — enforced at DB level
        nullable=False,
        index=True,
    )
    # All coin values stored as integers — never use floats for currency.
    # 1 coin = 1 unit. No decimal coins in this system.
    # Aurex uses a closed coin economy — no withdrawals, no TDS, no payout system.
    balance = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    wallet_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(
        SAEnum("credit", "debit", name="txn_type"),
        nullable=False,
    )
    amount = Column(Integer, nullable=False)
    description = Column(String(255), nullable=False)
    # External reference: Razorpay payment ID, room ID, admin action ID, etc.
    reference = Column(String(150), nullable=True, index=True)
    status = Column(
        SAEnum("pending", "completed", "failed", name="txn_status"),
        nullable=False,
        server_default="pending",
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    wallet = relationship("Wallet", back_populates="transactions")
    user = relationship("User", back_populates="transactions")
