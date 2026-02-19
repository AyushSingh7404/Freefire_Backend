"""
OTP service: generation, storage (hashed), and verification.

Security design decisions:
  1. Raw OTP is NEVER stored — only bcrypt hash. If DB is breached, OTPs are useless.
  2. New OTP request invalidates all previous unused OTPs for same email+purpose.
  3. OTPs expire after 10 minutes (server-side check + DB-level expiry).
  4. secrets.randbelow() is cryptographically secure (unlike random.randint).
  5. Brute-force of 6-digit code is prevented by slowapi rate limiting at the HTTP layer.
"""
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.otp import OTPRecord
from app.core.security import pwd_context

OTP_EXPIRY_MINUTES = 10


def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit OTP.
    secrets.randbelow(900000) gives 0–899999, +100000 gives 100000–999999.
    Always 6 digits — no leading zero issues.
    """
    return str(secrets.randbelow(900000) + 100000)


def create_otp_record(
    db: Session,
    email: str,
    purpose: str,
    user_id=None,
) -> str:
    """
    Creates a new OTP record in the DB and returns the raw OTP.

    Steps:
    1. Invalidate any previous unused OTPs for this email+purpose (prevent replay).
    2. Generate new raw OTP.
    3. Hash it with bcrypt.
    4. Store hash, expiry, and metadata.
    5. Return the raw OTP to the caller (who passes it to email_service).

    user_id is nullable because during registration the user doesn't exist yet.
    """
    # Step 1: invalidate previous OTPs for this email+purpose
    db.query(OTPRecord).filter(
        OTPRecord.email == email,
        OTPRecord.purpose == purpose,
        OTPRecord.is_used == False,
    ).update({"is_used": True}, synchronize_session=False)

    # Step 2 & 3: generate and hash
    raw_otp = generate_otp()
    otp_hash = pwd_context.hash(raw_otp)

    # Step 4: create record
    record = OTPRecord(
        email=email,
        user_id=user_id,
        otp_hash=otp_hash,
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(record)
    db.commit()

    # Step 5: return raw OTP (never stored; will be sent via email)
    return raw_otp


def verify_otp_record(db: Session, email: str, otp: str, purpose: str) -> bool:
    """
    Verifies an OTP against the stored hash.

    Returns True if valid, False otherwise.
    On success, marks the record as used (one-time use).

    Checks:
    - Record exists for this email+purpose
    - Record is not already used
    - Record has not expired
    - bcrypt.verify(submitted_otp, stored_hash) passes
    """
    record = (
        db.query(OTPRecord)
        .filter(
            OTPRecord.email == email,
            OTPRecord.purpose == purpose,
            OTPRecord.is_used == False,
            OTPRecord.expires_at > datetime.now(timezone.utc),
        )
        .order_by(OTPRecord.created_at.desc())  # use the most recently created OTP
        .first()
    )

    if not record:
        return False

    if not pwd_context.verify(otp, record.otp_hash):
        return False

    # Mark as used — one-time use enforced
    record.is_used = True
    db.commit()
    return True
