from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class RoomPlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    free_fire_id: str
    joined_at: datetime
    position: Optional[int] = None
    kills: Optional[int] = None
    points: Optional[int] = None
    # Include username from relationship for convenience
    username: Optional[str] = None

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)

    @classmethod
    def from_room_player(cls, rp) -> "RoomPlayerOut":
        """Helper to include username from the user relationship."""
        return cls(
            id=str(rp.id),
            user_id=str(rp.user_id),
            free_fire_id=rp.free_fire_id,
            joined_at=rp.joined_at,
            position=rp.position,
            kills=rp.kills,
            points=rp.points,
            username=rp.user.username if rp.user else None,
        )


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    league_id: str
    name: str
    entry_fee: int
    division: str
    max_players: int
    current_players: int
    status: str
    # admin_room_id is only included when the requesting user has joined the room.
    # The router/service is responsible for conditionally including it.
    admin_room_id: Optional[str] = None
    starts_at: datetime
    created_at: datetime
    players: List[RoomPlayerOut] = []

    @field_validator("id", "league_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> str:
        return str(v)


class RoomCreateRequest(BaseModel):
    """Admin use only."""
    league_id: str
    name: str
    entry_fee: int
    division: str
    max_players: int
    starts_at: datetime

    @field_validator("division")
    @classmethod
    def division_valid(cls, v: str) -> str:
        allowed = {"1v1", "2v2", "3v3", "4v4", "br"}
        if v not in allowed:
            raise ValueError(f"division must be one of: {', '.join(allowed)}")
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


class RoomUpdateRequest(BaseModel):
    """Admin use only — all fields optional."""
    name: Optional[str] = None
    status: Optional[str] = None
    admin_room_id: Optional[str] = None
    starts_at: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"open", "closed", "in_progress", "completed"}
        if v not in allowed:
            raise ValueError(f"status must be one of: {', '.join(allowed)}")
        return v


class JoinRoomRequest(BaseModel):
    free_fire_id: str

    @field_validator("free_fire_id")
    @classmethod
    def ff_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("free_fire_id cannot be empty")
        return v.strip()


class JoinRoomResponse(BaseModel):
    message: str
    room_name: str
    admin_room_id: Optional[str] = None  # revealed only after successful join
    current_players: int
    max_players: int
