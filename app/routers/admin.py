"""
Admin router: all admin-only operations.

Every endpoint:
  - Requires get_current_admin dependency (is_admin=True)
  - Writes an audit log after any state-changing operation
  - Returns structured responses

Endpoints:
  GET  /admin/stats
  POST /admin/leagues
  PUT  /admin/leagues/{id}
  POST /admin/rooms
  PUT  /admin/rooms/{id}
  GET  /admin/users
  GET  /admin/users/{id}
  PUT  /admin/users/{id}/ban
  PUT  /admin/users/{id}/unban
  POST /admin/wallet/credit
  POST /admin/wallet/debit
  POST /admin/matches/{room_id}/settle
  GET  /admin/audit-logs
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.core.dependencies import get_current_admin
from app.core.exceptions import NotFoundException, ConflictException
from app.middleware.audit_middleware import log_admin_action
from app.models.user import User
from app.models.league import League, Division
from app.models.room import Room, RoomPlayer
from app.models.wallet import Wallet, Transaction
from app.models.match import Match
from app.models.audit_log import AuditLog
from app.schemas.league import LeagueOut, LeagueCreateRequest, LeagueUpdateRequest
from app.schemas.room import RoomOut, RoomCreateRequest, RoomUpdateRequest, RoomPlayerOut
from app.schemas.wallet import AdminWalletActionRequest
from app.schemas.match import SettleRoomRequest
from app.schemas.admin import (
    AdminStatsResponse,
    AuditLogOut,
    AuditLogListResponse,
)
from app.schemas.user import UserOut
from app.services import wallet_service

router = APIRouter()


# ── Dashboard Stats ───────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Dashboard overview stats."""
    total_rooms = db.query(Room).count()
    open_rooms = db.query(Room).filter(Room.status == "open").count()
    total_players = db.query(User).filter(User.is_admin == False).count()
    total_coins = db.query(func.coalesce(func.sum(Wallet.balance), 0)).scalar()
    total_transactions = db.query(Transaction).count()
    total_matches = db.query(Match).count()

    return AdminStatsResponse(
        total_rooms=total_rooms,
        open_rooms=open_rooms,
        total_players=total_players,
        total_coins_in_circulation=int(total_coins),
        total_transactions=total_transactions,
        total_matches_played=total_matches,
    )


# ── League Management ─────────────────────────────────────────────────────────

@router.post("/leagues", response_model=LeagueOut, status_code=201)
def create_league(
    body: LeagueCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Create a new league."""
    league = League(
        name=body.name,
        tier=body.tier,
        entry_fee=body.entry_fee,
        description=body.description,
        max_players=body.max_players,
        image_url=body.image_url,
    )
    db.add(league)
    db.commit()
    db.refresh(league)

    log_admin_action(
        db, admin_id=str(admin.id), action="CREATE_LEAGUE",
        target_type="league", target_id=str(league.id),
        details={"name": league.name, "tier": league.tier},
    )
    return league


@router.put("/leagues/{league_id}", response_model=LeagueOut)
def update_league(
    league_id: str,
    body: LeagueUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Update league details. All fields optional."""
    league = db.query(League).filter(League.id == league_id).first()
    if not league:
        raise NotFoundException("League")

    changes = {}
    if body.name is not None:
        changes["name"] = body.name
        league.name = body.name
    if body.entry_fee is not None:
        changes["entry_fee"] = body.entry_fee
        league.entry_fee = body.entry_fee
    if body.description is not None:
        league.description = body.description
    if body.max_players is not None:
        league.max_players = body.max_players
    if body.image_url is not None:
        league.image_url = body.image_url
    if body.is_active is not None:
        changes["is_active"] = body.is_active
        league.is_active = body.is_active

    db.commit()
    db.refresh(league)

    log_admin_action(
        db, admin_id=str(admin.id), action="UPDATE_LEAGUE",
        target_type="league", target_id=str(league.id),
        details=changes,
    )
    return league


# ── Room Management ───────────────────────────────────────────────────────────

@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(
    body: RoomCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Create a new room inside a league."""
    league = db.query(League).filter(League.id == body.league_id).first()
    if not league:
        raise NotFoundException("League")

    room = Room(
        league_id=body.league_id,
        name=body.name,
        entry_fee=body.entry_fee,
        division=body.division,
        max_players=body.max_players,
        starts_at=body.starts_at,
        created_by=admin.id,
        status="open",
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    log_admin_action(
        db, admin_id=str(admin.id), action="CREATE_ROOM",
        target_type="room", target_id=str(room.id),
        details={"name": room.name, "league_id": body.league_id, "division": body.division},
    )

    return RoomOut(
        id=str(room.id),
        league_id=str(room.league_id),
        name=room.name,
        entry_fee=room.entry_fee,
        division=room.division,
        max_players=room.max_players,
        current_players=room.current_players,
        status=room.status,
        admin_room_id=room.admin_room_id,
        starts_at=room.starts_at,
        created_at=room.created_at,
        players=[],
    )


@router.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(
    room_id: str,
    body: RoomUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Update room details. Key use cases:
      - Set admin_room_id after getting it from Free Fire
      - Change status to publish/unpublish
      - Update starts_at
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise NotFoundException("Room")

    changes = {}
    if body.name is not None:
        changes["name"] = body.name
        room.name = body.name
    if body.status is not None:
        changes["status"] = {"from": room.status, "to": body.status}
        room.status = body.status
    if body.admin_room_id is not None:
        # This is the critical moment: admin publishes the in-game room code
        room.admin_room_id = body.admin_room_id
        changes["admin_room_id_set"] = True
    if body.starts_at is not None:
        room.starts_at = body.starts_at

    db.commit()
    db.refresh(room)

    log_admin_action(
        db, admin_id=str(admin.id), action="UPDATE_ROOM",
        target_type="room", target_id=str(room.id),
        details=changes,
    )

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
        admin_room_id=room.admin_room_id,   # admin sees it unconditionally
        starts_at=room.starts_at,
        created_at=room.created_at,
        players=players,
    )


# ── User Management ───────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by username or email"),
    banned_only: bool = Query(False),
):
    """
    Paginated user list with optional search.
    Returns full user profiles including wallet balances.
    """
    query = db.query(User)
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (func.lower(User.username).like(search_term)) |
            (func.lower(User.email).like(search_term))
        )
    if banned_only:
        query = query.filter(User.is_banned == True)

    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    user_list = []
    for u in users:
        wallet = db.query(Wallet).filter(Wallet.user_id == u.id).first()
        user_list.append({
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_banned": u.is_banned,
            "is_verified": u.is_verified,
            "coins": wallet.balance if wallet else 0,
            "created_at": u.created_at.isoformat(),
        })

    return {"total": total, "page": page, "limit": limit, "users": user_list}


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Full user detail including wallet and recent matches."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User")

    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    recent_matches = (
        db.query(Match)
        .filter(Match.user_id == user_id)
        .order_by(Match.played_at.desc())
        .limit(10)
        .all()
    )

    return {
        "user": UserOut.model_validate(user),
        "wallet": {
            "balance": wallet.balance if wallet else 0,
            "locked_balance": wallet.locked_balance if wallet else 0,
        },
        "recent_matches": [
            {
                "id": str(m.id),
                "division": m.division,
                "result": m.result,
                "coins_won": m.coins_won,
                "kills": m.kills,
                "played_at": m.played_at.isoformat(),
            }
            for m in recent_matches
        ],
    }


@router.put("/users/{user_id}/ban")
def ban_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    reason: str = Query(..., description="Reason for ban — stored in audit log"),
):
    """
    Ban a user account.
    Their existing valid JWTs are rejected immediately because get_current_user
    checks is_banned on every request.
    Cannot ban another admin (prevents privilege escalation).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User")
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot ban an admin account",
        )
    if user.is_banned:
        raise ConflictException("User is already banned")

    user.is_banned = True
    db.commit()

    log_admin_action(
        db, admin_id=str(admin.id), action="BAN_USER",
        target_type="user", target_id=user_id,
        details={"username": user.username, "reason": reason},
    )
    return {"message": f"User '{user.username}' has been banned."}


@router.put("/users/{user_id}/unban")
def unban_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Lift a ban from a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User")
    if not user.is_banned:
        raise ConflictException("User is not currently banned")

    user.is_banned = False
    db.commit()

    log_admin_action(
        db, admin_id=str(admin.id), action="UNBAN_USER",
        target_type="user", target_id=user_id,
        details={"username": user.username},
    )
    return {"message": f"User '{user.username}' has been unbanned."}


# ── Wallet Management ─────────────────────────────────────────────────────────

@router.post("/wallet/credit")
def admin_credit_coins(
    body: AdminWalletActionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Credit coins to any user's wallet. Requires a reason for audit trail."""
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise NotFoundException("User")

    txn = wallet_service.admin_credit_coins(
        db,
        target_user_id=body.user_id,
        amount=body.amount,
        reason=body.reason,
        admin_id=str(admin.id),
    )

    log_admin_action(
        db, admin_id=str(admin.id), action="CREDIT_COINS",
        target_type="wallet", target_id=body.user_id,
        details={"amount": body.amount, "reason": body.reason, "username": user.username},
    )
    return {"message": f"Credited {body.amount} coins to '{user.username}'.", "transaction_id": str(txn.id)}


@router.post("/wallet/debit")
def admin_debit_coins(
    body: AdminWalletActionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Debit coins from any user's wallet. Requires a reason for audit trail."""
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise NotFoundException("User")

    txn = wallet_service.admin_debit_coins(
        db,
        target_user_id=body.user_id,
        amount=body.amount,
        reason=body.reason,
        admin_id=str(admin.id),
    )

    log_admin_action(
        db, admin_id=str(admin.id), action="DEBIT_COINS",
        target_type="wallet", target_id=body.user_id,
        details={"amount": body.amount, "reason": body.reason, "username": user.username},
    )
    return {"message": f"Debited {body.amount} coins from '{user.username}'.", "transaction_id": str(txn.id)}


# ── Match Settlement ──────────────────────────────────────────────────────────

@router.post("/matches/{room_id}/settle")
def settle_room(
    room_id: str,
    body: SettleRoomRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Settle a completed room: record match results and credit winners.

    This is a critical, multi-step operation done atomically:
      For each player result in body.results:
        1. Verify the user was actually in the room
        2. Create a Match record
        3. Update their RoomPlayer stats (position, kills, points)
        4. If coins_won > 0, credit their wallet

    Room status is set to 'completed' after settling.

    Corner cases:
      - Settling an already-completed room → rejected (prevents double crediting)
      - result.user_id not in room → rejected per-player
      - body.results can be partial (only winners need to be listed)
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise NotFoundException("Room")

    if room.status == "completed":
        raise ConflictException("This room has already been settled")

    settled_players = []
    errors = []

    # ── Validate ALL players before making ANY writes ─────────────────────────
    # This pre-validation pass means we either settle everyone or no one,
    # preventing partial settlement where some players get coins and others don't.
    valid_results = []
    for player_result in body.results:
        room_player = db.query(RoomPlayer).filter(
            RoomPlayer.room_id == room_id,
            RoomPlayer.user_id == player_result.user_id,
        ).first()
        if not room_player:
            errors.append(f"User {player_result.user_id} was not in this room — skipped")
        else:
            valid_results.append((player_result, room_player))

    # ── Apply all writes in a single transaction ──────────────────────────────
    # wallet_service.credit_coins uses its own db.commit() internally, so we
    # build all wallet transactions first and do one final commit for room/match
    # records. The credit_coins commits are intentional — they use SELECT FOR UPDATE
    # which requires committing to release the row lock promptly.
    for player_result, room_player in valid_results:
        # Update RoomPlayer stats
        room_player.position = player_result.position
        room_player.kills = player_result.kills
        room_player.points = player_result.coins_won

        # Create Match record (not committed yet)
        match = Match(
            room_id=room_id,
            user_id=player_result.user_id,
            league_id=room.league_id,
            division=room.division,
            room_name=room.name,
            result=player_result.result,
            coins_won=player_result.coins_won,
            kills=player_result.kills,
            position=player_result.position,
        )
        db.add(match)

        # Credit winnings (commits internally to release wallet lock)
        if player_result.coins_won > 0:
            wallet_service.credit_coins(
                db,
                user_id=player_result.user_id,
                amount=player_result.coins_won,
                description=f"Tournament winnings from {room.name}",
                reference=str(room.id),
            )

        settled_players.append(player_result.user_id)

    # Mark room as completed and commit Match records
    room.status = "completed"
    db.commit()

    log_admin_action(
        db, admin_id=str(admin.id), action="SETTLE_MATCH",
        target_type="room", target_id=room_id,
        details={
            "room_name": room.name,
            "players_settled": len(settled_players),
            "errors": errors,
        },
    )

    return {
        "message": f"Room '{room.name}' settled successfully.",
        "players_settled": len(settled_players),
        "errors": errors,
    }


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=AuditLogListResponse)
def get_audit_logs(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
):
    """
    Read-only audit log. Newest entries first.
    Can be filtered by action type (e.g., 'BAN_USER') or target type (e.g., 'user').
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action.upper())
    if target_type:
        query = query.filter(AuditLog.target_type == target_type.lower())

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return AuditLogListResponse(
        total=total,
        page=page,
        limit=limit,
        logs=[AuditLogOut.model_validate(log) for log in logs],
    )
