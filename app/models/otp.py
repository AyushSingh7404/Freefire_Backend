import uuid
from sqlalchemy import Boolean, Column, String, TIMESTAMP, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from app.database import Base


class OTPRecord(Base):
    """
    Stores hashed OTPs for email verification, login, and password reset.

    Security notes:
    - Raw OTP is NEVER stored — only the bcrypt hash.
    - Each new OTP request invalidates all previous unused OTPs for the same
      email + purpose combination (prevents replay attacks).
    - OTPs expire after OTP_EXPIRY_MINUTES (10 min by default).
    - user_id is nullable because during registration the user doesn't exist yet
      when the OTP is first created.
    """
    __tablename__ = "otp_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # nullable: user may not exist yet (registration flow)
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String, nullable=False)  # bcrypt hash of the raw 6-digit OTP
    purpose = Column(
        SAEnum("login", "register", "forgot_password", name="otp_purpose"),
        nullable=False,
    )
    is_used = Column(Boolean, server_default="False", nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="otp_records")
