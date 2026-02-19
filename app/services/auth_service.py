"""
Auth service: higher-level auth operations that combine multiple lower-level services.
Keeps routers thin — routers only handle HTTP, services handle logic.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.wallet import Wallet
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, pwd_context
from app.core.exceptions import ConflictException, CredentialsException, InvalidOTPException, NotFoundException
from app.services.otp_service import create_otp_record, verify_otp_record
from app.services.wallet_service import get_or_create_wallet
from datetime import datetime, timezone

# Pre-computed bcrypt hash used ONLY for constant-time comparison when the user
# doesn't exist — prevents timing attacks that reveal valid email addresses.
# Generated once at module load. Never stored anywhere or used for real auth.
_DUMMY_HASH: str = pwd_context.hash("__dummy_timing_prevention__")


def register_user(db: Session, username: str, email: str, password: str, age: int,
                  free_fire_id: str = None, free_fire_name: str = None) -> User:
    """
    Creates a new user account + wallet in one commit.
    Does NOT mark the user as verified — that happens after OTP verification.
    Returns the created User object.
    """
    # Check uniqueness before any DB writes
    if db.query(User).filter(User.email == email).first():
        raise ConflictException("An account with this email already exists")
    if db.query(User).filter(User.username == username).first():
        raise ConflictException("This username is already taken")

    # Create user
    new_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        age=age,
        free_fire_id=free_fire_id,
        free_fire_name=free_fire_name,
        is_verified=False,
    )
    db.add(new_user)
    db.flush()  # flush to get the UUID assigned without committing

    # Create wallet in the same transaction — atomicity guaranteed
    wallet = Wallet(user_id=new_user.id, balance=0, locked_balance=0)
    db.add(wallet)

    db.commit()
    db.refresh(new_user)
    return new_user


def verify_registration(db: Session, email: str, otp: str) -> tuple[User, str, str]:
    """
    Verifies OTP for registration. Marks user as verified.
    Returns (user, access_token, refresh_token).
    """
    if not verify_otp_record(db, email, otp, "register"):
        raise InvalidOTPException()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise NotFoundException("User")

    user.is_verified = True
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id), user.is_admin)
    refresh_token = create_refresh_token(str(user.id))
    return user, access_token, refresh_token


def initiate_login(db: Session, email: str, password: str) -> User:
    """
    Validates credentials. Returns user if valid.
    The caller then sends an OTP — token is NOT issued yet.

    Security: always use the same error message regardless of whether
    the email exists or the password is wrong (prevents user enumeration).
    """
    user = db.query(User).filter(User.email == email).first()
    # Always run verify_password regardless of whether the user exists.
    # This makes the response time identical for "wrong email" vs "wrong password",
    # preventing timing-based user enumeration attacks.
    # _DUMMY_HASH is a real valid bcrypt hash — passlib won't raise on it.
    password_ok = verify_password(password, user.hashed_password if user else _DUMMY_HASH)

    if not user or not password_ok:
        raise CredentialsException("Invalid email or password")
    if user.is_banned:
        from app.core.exceptions import BannedUserException
        raise BannedUserException()
    return user


def verify_login(db: Session, email: str, otp: str) -> tuple[User, str, str]:
    """
    Verifies OTP for login. Updates last_login_at. Returns tokens.
    """
    if not verify_otp_record(db, email, otp, "login"):
        raise InvalidOTPException()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise NotFoundException("User")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id), user.is_admin)
    refresh_token = create_refresh_token(str(user.id))
    return user, access_token, refresh_token


def reset_password(db: Session, email: str, otp: str, new_password: str) -> None:
    """Verifies OTP then updates the user's password."""
    if not verify_otp_record(db, email, otp, "forgot_password"):
        raise InvalidOTPException()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Silent success — don't reveal that email doesn't exist
        return

    user.hashed_password = hash_password(new_password)
    db.commit()
