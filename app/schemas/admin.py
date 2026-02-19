from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class LeaderboardEntryOut(BaseModel):
    rank: int
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    total_winnings: int      # total coins won across all matches
    games_played: int
    win_rate: float          # percentage, e.g. 68.5
    average_kills: float
    points: int              # total points for ranking


class GlobalLeaderboardResponse(BaseModel):
    total: int
    entries: List[LeaderboardEntryOut]


class LeagueLeaderboardResponse(BaseModel):
    league_id: str
    league_name: str
    total: int
    entries: List[LeaderboardEntryOut]


class AdminStatsResponse(BaseModel):
    """Dashboard stats for admin panel."""
    total_rooms: int
    open_rooms: int
    total_players: int
    total_coins_in_circulation: int   # sum of all wallet balances
    total_transactions: int
    total_matches_played: int


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    limit: int
    users: List[dict]  # UserOut dicts — avoid circular import by using dict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    admin_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime

    @field_validator("id", "admin_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v) -> Optional[str]:
        if v is None:
            return None
        return str(v)


class AuditLogListResponse(BaseModel):
    total: int
    page: int
    limit: int
    logs: List[AuditLogOut]
