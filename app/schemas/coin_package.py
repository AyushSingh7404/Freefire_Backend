from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional
from datetime import datetime


class CoinPackageOut(BaseModel):
    """Public-facing package response — returned by GET /coin-packages."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    coins: int
    price_inr: int
    is_popular: bool
    sort_order: int

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)


class CoinPackageAdminOut(CoinPackageOut):
    """Admin view — includes is_active and created_at."""
    is_active: bool
    created_at: datetime


class CoinPackageCreateRequest(BaseModel):
    """Admin: create a new coin package."""
    coins: int
    price_inr: int
    is_active: bool = True
    is_popular: bool = False
    sort_order: int = 0

    @field_validator("coins")
    @classmethod
    def coins_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("coins must be positive")
        return v

    @field_validator("price_inr")
    @classmethod
    def price_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("price_inr must be positive")
        return v


class CoinPackageUpdateRequest(BaseModel):
    """Admin: update a coin package. All fields optional."""
    coins: Optional[int] = None
    price_inr: Optional[int] = None
    is_active: Optional[bool] = None
    is_popular: Optional[bool] = None
    sort_order: Optional[int] = None

    @field_validator("coins")
    @classmethod
    def coins_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("coins must be positive")
        return v

    @field_validator("price_inr")
    @classmethod
    def price_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("price_inr must be positive")
        return v
