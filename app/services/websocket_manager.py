"""
WebSocket connection manager.

Manages active WebSocket connections grouped by room_id.
When a room's player count changes (join/leave), broadcasts the update to all
clients currently watching that room (via the /ws/rooms/{room_id} endpoint).

Limitation: This in-memory manager works perfectly for a single-server deployment.
If you ever scale to multiple server instances, replace this with Redis Pub/Sub.
"""
from fastapi import WebSocket
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Maps room_id (str) → list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        """Accept a new WebSocket connection and register it for a room."""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info(f"WS connected: room={room_id}, total={len(self.active_connections[room_id])}")

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        """Remove a disconnected WebSocket from the registry."""
        if room_id in self.active_connections:
            try:
                self.active_connections[room_id].remove(websocket)
            except ValueError:
                pass  # already removed
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        logger.info(f"WS disconnected: room={room_id}")

    async def broadcast_room_update(self, room) -> None:
        """
        Broadcast a room status update to all clients watching this room.
        Dead connections (client closed tab, network drop) are automatically cleaned up.
        """
        room_id = str(room.id)
        connections = self.active_connections.get(room_id, [])
        if not connections:
            return

        data = {
            "type": "ROOM_UPDATE",
            "roomId": room_id,
            "currentPlayers": room.current_players,
            "maxPlayers": room.max_players,
            "status": room.status,
        }

        dead: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(data)
            except Exception:
                # Connection is broken — mark for cleanup
                dead.append(connection)

        for conn in dead:
            self.disconnect(conn, room_id)


# Module-level singleton — imported by both the router and room_service
manager = ConnectionManager()
