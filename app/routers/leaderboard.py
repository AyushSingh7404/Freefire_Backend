"""
Leaderboard router: global and per-league leaderboards.

Leaderboards are computed by aggregating the matches table:
  - total_winnings: SUM(coins_won) per user
  - games_played: COUNT(match records) per user
  - win_rate: COUNT(where result='win') / games_played * 100
  - average_kills: AVG(kills) per user
  - points: SUM(coins_won) as ranking proxy (can be changed to a custom formula)

These are computed on-read with SQL aggregation. For a production app with
millions of matches, replace this with a pre-computed leaderboard table that
updates via a cron job or DB trigger. For this scale, live queries are fine.
"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException
from app.models.match import Match
from app.models.user import User
from app.models.league import League
from app.schemas.admin import (
    LeaderboardEntryOut,
    GlobalLeaderboardResponse,
    LeagueLeaderboardResponse,
)

router = APIRouter()


def _build_leaderboard_query(db: Session, league_id: str = None, limit: int = 50):
    """
    Shared aggregation logic for both global and league leaderboards.
    Returns a list of dicts with aggregated stats per user.
    """
    query = (
        db.query(
            Match.user_id,
            User.username,
            User.avatar_url,
            func.sum(Match.coins_won).label("total_winnings"),
            func.count(Match.id).label("games_played"),
            func.sum(
                # case() is the correct SQLAlchemy 2.0 way to conditionally aggregate.
                # Counts 1 for every 'win' result, 0 for everything else.
                case((Match.result == "win", 1), else_=0)
            ).label("wins"),
            func.avg(Match.kills).label("avg_kills"),
        )
        .join(User, User.id == Match.user_id)
        .filter(User.is_banned == False)
    )

    if league_id:
        query = query.filter(Match.league_id == league_id)

    rows = (
        query
        .group_by(Match.user_id, User.username, User.avatar_url)
        .order_by(func.sum(Match.coins_won).desc())
        .limit(limit)
        .all()
    )
    return rows


def _rows_to_entries(rows) -> List[LeaderboardEntryOut]:
    """Convert DB aggregate rows to LeaderboardEntryOut objects."""
    entries = []
    for rank, row in enumerate(rows, start=1):
        games = row.games_played or 1  # avoid division by zero
        # wins may be None if cast fails in some dialects — default to 0
        wins = int(row.wins or 0)
        win_rate = round((wins / games) * 100, 1)
        avg_kills = round(float(row.avg_kills or 0), 1)
        total_winnings = int(row.total_winnings or 0)

        entries.append(
            LeaderboardEntryOut(
                rank=rank,
                user_id=str(row.user_id),
                username=row.username,
                avatar_url=row.avatar_url,
                total_winnings=total_winnings,
                games_played=int(games),
                win_rate=win_rate,
                average_kills=avg_kills,
                points=total_winnings,  # points = total winnings (simple formula)
            )
        )
    return entries


@router.get("/global", response_model=GlobalLeaderboardResponse)
def get_global_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=200, description="Number of entries to return"),
):
    """
    Top players globally by total coins won across all leagues.
    Banned users are excluded.
    """
    rows = _build_leaderboard_query(db, league_id=None, limit=limit)
    entries = _rows_to_entries(rows)
    return GlobalLeaderboardResponse(total=len(entries), entries=entries)


@router.get("/league/{league_id}", response_model=LeagueLeaderboardResponse)
def get_league_leaderboard(
    league_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Top players in a specific league by coins won within that league.
    """
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundException("League")

    rows = _build_leaderboard_query(db, league_id=league_id, limit=limit)
    entries = _rows_to_entries(rows)

    return LeagueLeaderboardResponse(
        league_id=str(league.id),
        league_name=league.name,
        total=len(entries),
        entries=entries,
    )
