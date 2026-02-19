import uuid
from sqlalchemy import Boolean, Column, String, Integer, Text, TIMESTAMP, ForeignKey, JSON, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    free_fire_id = Column(String(50), nullable=True, index=True)
    free_fire_name = Column(String(100), nullable=True)
    rank = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Flags
    is_admin = Column(Boolean, server_default="False", nullable=False)
    is_banned = Column(Boolean, server_default="False", nullable=False)
    is_verified = Column(Boolean, server_default="False", nullable=False)

    # Timestamps
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    room_players = relationship("RoomPlayer", back_populates="user", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="user", cascade="all, delete-orphan")
    otp_records = relationship("OTPRecord", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship(
        "AuditLog",
        back_populates="admin",
        foreign_keys="[AuditLog.admin_id]",
    )
    created_rooms = relationship(
        "Room",
        back_populates="creator",
        foreign_keys="[Room.created_by]",
    )
