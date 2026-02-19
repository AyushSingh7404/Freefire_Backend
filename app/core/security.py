"""
Security utilities: password hashing and JWT token management.
Uses PyJWT (not python-jose) — actively maintained, no known CVEs as of 2026.
"""
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from app.config import settings

# ── Password Hashing ──────────────────────────────────────────────────────────
# bcrypt is the industry standard for password hashing.
# deprecated="auto" means passlib will auto-upgrade old hashes on next login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Creation ────────────────────────────────────────────────────────

def create_access_token(user_id: str, is_admin: bool = False) -> str:
    """
    Short-lived access token (default 30 min).
    Contains user_id (as 'sub') and is_admin flag.

    PyJWT 2.x note: jwt.encode() returns str directly — no need to call .decode().
    Always use timezone-aware datetimes to avoid PyJWT deprecation warnings.
    """
    payload = {
        "sub": user_id,           # 'sub' is the standard JWT subject claim
        "is_admin": is_admin,
        "type": "access",         # custom claim to distinguish token types
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        ),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    Long-lived refresh token (default 7 days).
    Does NOT contain is_admin — admin status is re-checked on every access token refresh.
    """
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        ),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decodes and validates an access token.
    Raises jwt.exceptions.InvalidTokenError (or subclass) on any failure.
    The caller is responsible for converting this into an HTTPException.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("type") != "access":
        raise InvalidTokenError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    """
    Decodes and validates a refresh token.
    Raises jwt.exceptions.InvalidTokenError on failure.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("type") != "refresh":
        raise InvalidTokenError("Not a refresh token")
    return payload
