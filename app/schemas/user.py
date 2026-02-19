"""
User schemas: public profile views and update requests.
"""
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
import re


class UserOut(BaseModel):
    """
    Public-safe user representation.
    hashed_password is never included — Pydantic only exposes fields declared here.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    age: Optional[int] = None
    free_fire_id: Optional[str] = None
    free_fire_name: Optional[str] = None
    rank: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: bool
    is_verified: bool
    is_banned: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    # UUID → str conversion for JSON serialization
    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)


class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    age: Optional[int] = None
    free_fire_id: Optional[str] = None
    free_fire_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Username must be between 3 and 30 characters")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v

    @field_validator("age")
    @classmethod
    def age_valid(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 13 or v > 100):
            raise ValueError("Age must be between 13 and 100")
        return v


class AvatarUploadResponse(BaseModel):
    avatar_url: str
    message: str = "Avatar updated successfully"


class UserAuthResponse(BaseModel):
    """Returned alongside tokens after successful login/register verification."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    is_admin: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    free_fire_id: Optional[str] = None

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)
