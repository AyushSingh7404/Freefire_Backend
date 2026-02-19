"""
Leagues router: list and fetch leagues and their divisions.

All league-list and division endpoints are public (no auth needed) so the
landing page can show league tiers without requiring login.
Room listing inside a league requires auth (users must be logged in to join).
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException
from app.models.league import League, Division
from app.models.room import Room
from app.models.user import User
from app.schemas.league import LeagueOut, DivisionOut
from app.schemas.room import RoomOut, RoomPlayerOut

router = APIRouter()


@router.get("", response_model=List[LeagueOut])
def list_leagues(
    db: Session = Depends(get_db),
    active_only: bool = Query(True, description="Return only active leagues"),
):
    """
    List all leagues. Public endpoint — no auth required.
    Inactive leagues are hidden from users by default (active_only=True).
    Admin can pass ?active_only=false to see everything (but this endpoint
    has no admin restriction — filtering is just a convenience).
    """
    query = db.query(League)
    if active_only:
        query = query.filter(League.is_active == True)
    return query.order_by(League.created_at).all()


@router.get("/{league_id}", response_model=LeagueOut)
def get_league(league_id: str, db: Session = Depends(get_db)):
    """Get a single league by ID. Public endpoint."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundException("League")
    return league


@router.get("/{league_id}/divisions", response_model=List[DivisionOut])
def get_league_divisions(league_id: str, db: Session = Depends(get_db)):
    """
    Get division fee/reward configuration for a league.
    Used by the frontend to render the division selector on league detail page.
    Public endpoint.
    """
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundException("League")

    divisions = (
        db.query(Division)
        .filter(Division.league_id == league_id)
        .all()
    )
    return divisions


@router.get("/{league_id}/rooms", response_model=List[RoomOut])
def get_league_rooms(
    league_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status: open|closed|in_progress|completed"),
    division: Optional[str] = Query(None, description="Filter by division: 1v1|2v2|3v3|4v4|br"),
):
    """
    List rooms in a league. Requires auth.

    Filters:
      ?status=open      → only open rooms (most common use)
      ?division=1v1     → only 1v1 rooms
      Both can be combined.

    admin_room_id is NEVER included in this list response — only revealed
    on the individual room detail endpoint to users who have joined.
    """
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundException("League")

    query = db.query(Room).filter(Room.league_id == league_id)

    if status:
        valid_statuses = {"open", "closed", "in_progress", "completed"}
        if status not in valid_statuses:
            from fastapi import HTTPException
            raise HTTPException(400, f"Invalid status. Use one of: {', '.join(valid_statuses)}")
        query = query.filter(Room.status == status)

    if division:
        query = query.filter(Room.division == division)

    rooms = query.order_by(Room.starts_at).all()

    # Build response — never expose admin_room_id in list view
    result = []
    for room in rooms:
        room_dict = RoomOut(
            id=str(room.id),
            league_id=str(room.league_id),
            name=room.name,
            entry_fee=room.entry_fee,
            division=room.division,
            max_players=room.max_players,
            current_players=room.current_players,
            status=room.status,
            admin_room_id=None,   # intentionally hidden in list view
            starts_at=room.starts_at,
            created_at=room.created_at,
            players=[],           # don't load players in list view (performance)
        )
        result.append(room_dict)

    return result
