import uuid
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from app.database import Base


class AuditLog(Base):
    """
    Immutable audit trail for all admin actions.
    Records are INSERT-only — never updated or deleted.
    The admin panel exposes this as a read-only view.

    Examples of actions recorded:
      BAN_USER, UNBAN_USER, CREDIT_COINS, DEBIT_COINS,
      CREATE_ROOM, UPDATE_ROOM, SETTLE_MATCH, CREATE_LEAGUE,
      UPDATE_LEAGUE, PUBLISH_ROOM, UNPUBLISH_ROOM
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    admin_id = Column(
        UUID(as_uuid=True),
        # SET NULL: preserve log even if admin account is deleted
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String(100), nullable=False, index=True)
    # What kind of entity was affected: "user", "room", "wallet", "league", "match"
    target_type = Column(String(50), nullable=True)
    # UUID (as string) of the affected entity for easy lookups
    target_id = Column(String(100), nullable=True, index=True)
    # Flexible JSON blob for additional context:
    # e.g. {"amount": 500, "reason": "Tournament win bonus", "previous_balance": 1000}
    details = Column(JSON, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True,
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    admin = relationship("User", back_populates="audit_logs", foreign_keys=[admin_id])
