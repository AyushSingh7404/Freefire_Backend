"""
Auth router: registration, login, OTP, token refresh, password reset.

OTP flow for registration:
  1. POST /auth/register  → create user (unverified) + send OTP
  2. POST /auth/verify-register → verify OTP → mark verified → return tokens

Login (direct, no OTP):
  POST /auth/login → validate credentials → return tokens immediately

Password reset:
  1. POST /auth/forgot-password → send OTP (always 200, never reveals if email exists)
  2. POST /auth/reset-password → verify OTP + set new password
"""
from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError

from app.database import get_db
from app.core.rate_limiter import limiter
from app.core.security import decode_refresh_token, create_access_token, create_refresh_token
from app.core.exceptions import CredentialsException
from app.schemas.auth import (
    RegisterRequest, SendOTPRequest, VerifyRegisterRequest,
    LoginRequest, VerifyLoginRequest, ForgotPasswordRequest,
    ResetPasswordRequest, RefreshTokenRequest, TokenResponse, MessageResponse,
)
from app.schemas.user import UserAuthResponse
from app.services import auth_service, otp_service
from app.services.email_service import send_otp_email
from app.models.user import User
from pydantic import BaseModel
from typing import Optional


class LoginWithTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserAuthResponse


router = APIRouter()


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=MessageResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Step 1 of registration.
    Creates an unverified user account and sends OTP to their email.
    Uses BackgroundTasks so the HTTP response is returned immediately
    without waiting for SMTP to complete.
    """
    user = auth_service.register_user(
        db,
        username=body.username,
        email=body.email,
        password=body.password,
        age=body.age,
        free_fire_id=body.free_fire_id,
        free_fire_name=body.free_fire_name,
    )

    raw_otp = otp_service.create_otp_record(
        db,
        email=body.email,
        purpose="register",
        user_id=str(user.id),
    )

    background_tasks.add_task(send_otp_email, body.email, raw_otp, "register")

    return {"message": "Account created. Please check your email for the OTP to verify your account."}


@router.post("/verify-register", response_model=LoginWithTokenResponse)
@limiter.limit("10/minute")
async def verify_register(
    request: Request,
    body: VerifyRegisterRequest,
    db: Session = Depends(get_db),
):
    """Step 2 of registration: verify OTP and receive auth tokens."""
    user, access_token, refresh_token = auth_service.verify_registration(
        db, email=body.email, otp=body.otp
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserAuthResponse.model_validate(user),
    }


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginWithTokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login with email and password. Returns tokens immediately.
    No OTP required for login.
    """
    user = auth_service.initiate_login(db, email=body.email, password=body.password)

    access_token = create_access_token(str(user.id), user.is_admin)
    refresh_token = create_refresh_token(str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserAuthResponse.model_validate(user),
    }


# ── OTP Resend ────────────────────────────────────────────────────────────────

@router.post("/send-otp", response_model=MessageResponse)
@limiter.limit("3/minute")
async def send_otp(
    request: Request,
    body: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Resend OTP for registration or password reset purposes.
    For registration resend: user must have initiated registration first.
    Always returns 200 to prevent email enumeration.
    """
    user = db.query(User).filter(User.email == body.email).first()
    user_id = str(user.id) if user else None

    raw_otp = otp_service.create_otp_record(
        db,
        email=body.email,
        purpose=body.purpose,
        user_id=user_id,
    )

    background_tasks.add_task(send_otp_email, body.email, raw_otp, body.purpose)

    return {"message": "OTP sent. Please check your email."}


# ── Token Refresh ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token + refresh token.
    Refresh token rotation: old refresh token is not stored/invalidated
    (stateless JWTs). For revocation, add a token blacklist (Redis) later.
    """
    try:
        payload = decode_refresh_token(body.refresh_token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise CredentialsException()
    except InvalidTokenError:
        raise CredentialsException("Invalid or expired refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.is_banned:
        raise CredentialsException()

    new_access = create_access_token(str(user.id), user.is_admin)
    new_refresh = create_refresh_token(str(user.id))

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


# ── Forgot / Reset Password ───────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Send password reset OTP.
    ALWAYS returns 200 OK even if email doesn't exist — never reveal account existence.
    """
    user = db.query(User).filter(User.email == body.email).first()
    if user:  # only send if user exists, but don't tell the caller either way
        raw_otp = otp_service.create_otp_record(
            db,
            email=body.email,
            purpose="forgot_password",
            user_id=str(user.id),
        )
        background_tasks.add_task(send_otp_email, body.email, raw_otp, "forgot_password")

    return {"message": "If an account with that email exists, a reset OTP has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Verify OTP and set a new password."""
    auth_service.reset_password(db, email=body.email, otp=body.otp, new_password=body.new_password)
    return {"message": "Password reset successfully. You can now login with your new password."}
