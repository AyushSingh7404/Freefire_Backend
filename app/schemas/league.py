from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class DivisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    league_id: str
    division_type: str
    entry_fee: int
    rewards_description: Optional[str] = None

    @field_validator("id", "league_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)


class LeagueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tier: str
    entry_fee: int
    description: Optional[str] = None
    max_players: int
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)


class LeagueCreateRequest(BaseModel):
    """Admin use only."""
    name: str
    tier: str
    entry_fee: int = 0
    description: Optional[str] = None
    max_players: int
    image_url: Optional[str] = None

    @field_validator("tier")
    @classmethod
    def tier_valid(cls, v: str) -> str:
        allowed = {"silver", "gold", "diamond", "br"}
        if v not in allowed:
            raise ValueError(f"tier must be one of: {', '.join(allowed)}")
        return v

    @field_validator("entry_fee")
    @classmethod
    def entry_fee_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("entry_fee cannot be negative")
        return v

    @field_validator("max_players")
    @classmethod
    def max_players_valid(cls, v: int) -> int:
        if v < 2:
            raise ValueError("max_players must be at least 2")
        return v


class LeagueUpdateRequest(BaseModel):
    """Admin use only — all fields optional."""
    name: Optional[str] = None
    entry_fee: Optional[int] = None
    description: Optional[str] = None
    max_players: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
