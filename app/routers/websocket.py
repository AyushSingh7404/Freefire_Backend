"""
WebSocket router: real-time room updates.

Frontend connects to ws://host/ws/rooms/{room_id} and receives JSON events
whenever a player joins or leaves the room.

Event shape:
  {
    "type": "ROOM_UPDATE",
    "roomId": "uuid",
    "currentPlayers": 12,
    "maxPlayers": 30,
    "status": "open"
  }

Note on auth: WebSocket connections cannot easily use Bearer tokens in headers
from browser JS. Two patterns are used in practice:
  1. Pass token as a query param: /ws/rooms/{id}?token=xxx (simple, less secure)
  2. Send token as first WebSocket message after connect (more secure)

We use option 1 here (query param) for simplicity. The token is validated on
connect. If invalid, the connection is immediately closed.
For production hardening, option 2 is recommended.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError

from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.services.websocket_manager import manager

router = APIRouter()


@router.websocket("/ws/rooms/{room_id}")
async def room_websocket(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(..., description="JWT access token for authentication"),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for live room player-count updates.

    Connection lifecycle:
      1. Client sends: ws://host/ws/rooms/{room_id}?token=<access_token>
      2. Server validates token
      3. If invalid → close with code 1008 (Policy Violation)
      4. If valid → accept and register connection
      5. Server pushes ROOM_UPDATE events whenever the room changes
      6. Client disconnects → connection cleaned up from manager

    The endpoint keeps the connection alive by waiting for client messages.
    The client can send a ping ("ping") to keep the connection warm through
    proxies that close idle WebSockets.
    """
    # ── Authenticate before accepting ────────────────────────────────────────
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return

        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.is_banned:
            await websocket.close(code=1008, reason="Unauthorized")
            return

    except InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # ── Accept and register connection ────────────────────────────────────────
    await manager.connect(websocket, room_id)

    try:
        # Send an immediate connection confirmation
        await websocket.send_json({
            "type": "CONNECTED",
            "roomId": room_id,
            "message": "Connected to room updates",
        })

        # Keep connection alive — wait for client messages (or disconnect)
        while True:
            data = await websocket.receive_text()
            # Handle client ping to prevent proxy timeouts
            if data == "ping":
                await websocket.send_text("pong")
            # Other client messages can be handled here in future

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
