from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    room_id: Optional[str] = None
    league_id: Optional[str] = None
    division: str
    room_name: Optional[str] = None
    result: str
    coins_won: int
    kills: int
    position: Optional[int] = None
    played_at: datetime

    @field_validator("id", "room_id", "league_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> Optional[str]:
        if v is None:
            return None
        return str(v)


class MatchHistoryResponse(BaseModel):
    total: int
    page: int
    limit: int
    matches: List[MatchOut]


class SettleMatchPlayerResult(BaseModel):
    """Per-player result sent by admin when settling a room."""
    user_id: str
    position: int
    kills: int
    coins_won: int
    result: str  # "win" | "loss" | "draw"

    @field_validator("result")
    @classmethod
    def result_valid(cls, v: str) -> str:
        if v not in {"win", "loss", "draw"}:
            raise ValueError("result must be 'win', 'loss', or 'draw'")
        return v

    @field_validator("position")
    @classmethod
    def position_valid(cls, v: int) -> int:
        if v < 1:
            raise ValueError("position must be >= 1")
        return v


class SettleRoomRequest(BaseModel):
    """Admin sends this to settle a completed room and credit winners."""
    results: List[SettleMatchPlayerResult]
