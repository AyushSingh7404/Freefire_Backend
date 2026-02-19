"""
Rooms router: room detail, join, leave.

Security rule enforced here:
  admin_room_id (the actual in-game room code) is ONLY revealed to a user
  who has successfully joined that room. This prevents players from
  accessing the game room without paying the entry fee.
"""
import asyncio
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException
from app.core.rate_limiter import limiter
from app.models.user import User
from app.schemas.room import RoomOut, RoomPlayerOut, JoinRoomRequest, JoinRoomResponse
from app.services import room_service
from app.services.websocket_manager import manager

router = APIRouter()


@router.get("/{room_id}", response_model=RoomOut)
async def get_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get room detail including player list.

    admin_room_id is conditionally revealed:
      - If the requesting user has joined the room → included
      - Otherwise → None (hidden)

    This is the key security gate: you can't get the in-game room code
    without having paid the entry fee and been registered as a room_player.
    """
    room = room_service.get_room_or_404(db, room_id)

    # Check if this user has joined
    user_has_joined = room_service.is_user_in_room(db, room_id, str(current_user.id))

    # Build player list with usernames
    players = [RoomPlayerOut.from_room_player(rp) for rp in room.players]

    return RoomOut(
        id=str(room.id),
        league_id=str(room.league_id),
        name=room.name,
        entry_fee=room.entry_fee,
        division=room.division,
        max_players=room.max_players,
        current_players=room.current_players,
        status=room.status,
        # KEY: only reveal admin_room_id to joined players
        admin_room_id=room.admin_room_id if user_has_joined else None,
        starts_at=room.starts_at,
        created_at=room.created_at,
        players=players,
    )


@router.post("/{room_id}/join", response_model=JoinRoomResponse)
@limiter.limit("5/minute")
async def join_room(
    request: Request,
    room_id: str,
    body: JoinRoomRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Join a room and pay the entry fee.

    Full atomic operation:
      1. Validate room is open and not full (under DB lock)
      2. Validate user has sufficient coins (under DB lock)
      3. Deduct entry fee
      4. Create room_player record
      5. Increment current_players
      6. Auto-close room if full
      7. Broadcast WebSocket update to all watchers

    Rate limited to 5 attempts/minute to prevent spam joining.

    Returns admin_room_id immediately after successful join, since
    the user is now a registered player.
    """
    room = room_service.join_room(
        db,
        room_id=room_id,
        user_id=str(current_user.id),
        free_fire_id=body.free_fire_id,
    )

    # Broadcast WebSocket update HERE — we're in an async context so
    # asyncio.create_task works correctly. Fire-and-forget: don't await
    # so the HTTP response is not delayed by WebSocket delivery.
    asyncio.create_task(manager.broadcast_room_update(room))

    return JoinRoomResponse(
        message="Successfully joined the room!",
        room_name=room.name,
        admin_room_id=room.admin_room_id,  # safe to reveal now — user has joined
        current_players=room.current_players,
        max_players=room.max_players,
    )


@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Leave a room before the match starts.

    Refund policy:
      - Room status is 'open' → full refund of entry fee
      - Room status is 'closed', 'in_progress', or 'completed' → no refund

    Once the admin starts the match (status → in_progress), leaving
    is noted but no coins are returned.
    """
    result = room_service.leave_room(
        db,
        room_id=room_id,
        user_id=str(current_user.id),
    )

    # Broadcast updated player count to WebSocket watchers
    room = room_service.get_room_or_404(db, room_id)
    asyncio.create_task(manager.broadcast_room_update(room))

    msg = (
        f"Left the room. {result['entry_fee']} coins refunded."
        if result["refunded"]
        else "Left the room. No refund (match already started or room closed)."
    )
    return {"message": msg, **result}
