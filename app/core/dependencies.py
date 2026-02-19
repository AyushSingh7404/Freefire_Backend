"""
FastAPI dependencies used across routers.
Keep this file lean — only auth/DB dependencies go here.
Business logic belongs in services/.
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError

from app.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import CredentialsException, BannedUserException, ForbiddenException
from app.models.user import User

# tokenUrl must match the actual login endpoint path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validates the JWT access token and returns the authenticated User.

    Checks performed (in order):
    1. Token is a valid JWT signed with our secret key
    2. Token type is 'access' (not refresh)
    3. 'sub' claim exists and maps to a real user
    4. User account is not banned

    Corner case: is_banned check happens on EVERY request, not just at login.
    This means a banned user's existing valid JWT is immediately rejected.
    """
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise CredentialsException()
    except InvalidTokenError:
        raise CredentialsException()

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise CredentialsException()

    if user.is_banned:
        raise BannedUserException()

    return user


def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Extends get_current_user — additionally requires the account to be verified.
    Use on endpoints that should be blocked for unverified accounts.
    """
    if not current_user.is_verified:
        from app.core.exceptions import UnverifiedAccountException
        raise UnverifiedAccountException()
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Requires the authenticated user to be an admin.
    Returns the User object so admin routes can access it normally.
    """
    if not current_user.is_admin:
        raise ForbiddenException("Admin access required")
    return current_user
