"""
Room service: join, leave, and admin operations with full atomicity.

The join_room function is the most critical in the entire codebase.
It must atomically:
  1. Lock the room row (prevent double-fill)
  2. Lock the wallet row (prevent double-spend)
  3. Deduct coins
  4. Create room_player record
  5. Increment current_players
  6. Auto-close room if full
  7. Commit everything in one transaction
  8. Broadcast WebSocket update

If ANY step fails, the entire transaction rolls back.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.room import Room, RoomPlayer
from app.models.wallet import Wallet
from app.core.exceptions import (
    NotFoundException, RoomFullException, ConflictException, InsufficientCoinsException
)
from app.services.wallet_service import debit_coins, credit_coins


def get_room_or_404(db: Session, room_id: str) -> Room:
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise NotFoundException("Room")
    return room


def join_room(
    db: Session,
    room_id: str,
    user_id: str,
    free_fire_id: str,
) -> Room:
    """
    Atomically joins a user to a room with coin deduction.

    Locking order: wallet FIRST, then room.
    This order must never be reversed anywhere in the codebase — deadlock prevention.
    """
    # ── Pre-checks (without locking, fast path) ───────────────────────────────
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise NotFoundException("Room")
    if room.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room is not open (current status: {room.status})",
        )

    # Check if user already joined (before locking, cheap check)
    existing = db.query(RoomPlayer).filter(
        RoomPlayer.room_id == room_id,
        RoomPlayer.user_id == user_id,
    ).first()
    if existing:
        raise ConflictException("You have already joined this room")

    # ── Lock wallet first, then room (consistent order) ───────────────────────
    wallet = (
        db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
        .scalar_one_or_none()
    )
    if not wallet:
        raise NotFoundException("Wallet")

    available = wallet.balance - wallet.locked_balance
    if available < room.entry_fee:
        raise InsufficientCoinsException(available=available, required=room.entry_fee)

    # Now lock the room row
    room = (
        db.execute(
            select(Room).where(Room.id == room_id).with_for_update()
        )
        .scalar_one_or_none()
    )

    # Re-check status and capacity under lock (another request may have filled it)
    if room.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room is not open (current status: {room.status})",
        )
    if room.current_players >= room.max_players:
        raise RoomFullException()

    # ── Perform mutations ─────────────────────────────────────────────────────
    # Deduct coins from wallet
    wallet.balance -= room.entry_fee

    # Create transaction record
    from app.models.wallet import Transaction
    txn = Transaction(
        wallet_id=wallet.id,
        user_id=user_id,
        type="debit",
        amount=room.entry_fee,
        description=f"Entry fee for {room.name}",
        reference=str(room.id),
        status="completed",
    )
    db.add(txn)

    # Add player to room
    room_player = RoomPlayer(
        room_id=room_id,
        user_id=user_id,
        free_fire_id=free_fire_id,
    )
    db.add(room_player)

    # Increment player count
    room.current_players += 1

    # Auto-close if full
    if room.current_players >= room.max_players:
        room.status = "closed"

    db.commit()
    db.refresh(room)
    # WebSocket broadcast is intentionally NOT done here.
    # This service function is synchronous — asyncio.create_task cannot be called
    # safely from a thread pool. The router (which is async) handles the broadcast
    # after this function returns. See rooms.py router.
    return room


def leave_room(db: Session, room_id: str, user_id: str) -> dict:
    """
    Leave a room. Refunds the entry fee ONLY if:
    - Room status is still 'open' (match hasn't started)
    - User is actually in the room
    No refund if room is in_progress or completed.
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise NotFoundException("Room")

    room_player = db.query(RoomPlayer).filter(
        RoomPlayer.room_id == room_id,
        RoomPlayer.user_id == user_id,
    ).first()
    if not room_player:
        raise NotFoundException("Room membership")

    refunded = False
    if room.status == "open":
        # Refund coins
        credit_coins(
            db,
            user_id=user_id,
            amount=room.entry_fee,
            description=f"Refund: left {room.name} before match start",
            reference=str(room.id),
        )
        room.current_players = max(0, room.current_players - 1)
        refunded = True

    db.delete(room_player)
    db.commit()
    # Broadcast handled by the async router after this returns.
    return {"refunded": refunded, "entry_fee": room.entry_fee if refunded else 0}


def is_user_in_room(db: Session, room_id: str, user_id: str) -> bool:
    """Check if a user has joined a specific room (used for admin_room_id reveal)."""
    return db.query(RoomPlayer).filter(
        RoomPlayer.room_id == room_id,
        RoomPlayer.user_id == user_id,
    ).first() is not None
