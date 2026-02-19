"""
Auth schemas: request bodies and responses for registration, login, OTP, and token operations.
"""
from pydantic import BaseModel, EmailStr, field_validator, model_validator, ConfigDict
from typing import Optional
import re


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    age: int
    free_fire_id: Optional[str] = None
    free_fire_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Username must be between 3 and 30 characters")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("age")
    @classmethod
    def age_valid(cls, v: int) -> int:
        if v < 13 or v > 100:
            raise ValueError("Age must be between 13 and 100")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class SendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str  # "register" | "login" | "forgot_password"

    @field_validator("purpose")
    @classmethod
    def purpose_valid(cls, v: str) -> str:
        allowed = {"register", "login", "forgot_password"}
        if v not in allowed:
            raise ValueError(f"purpose must be one of: {', '.join(allowed)}")
        return v


class VerifyRegisterRequest(BaseModel):
    email: EmailStr
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyLoginRequest(BaseModel):
    email: EmailStr
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
