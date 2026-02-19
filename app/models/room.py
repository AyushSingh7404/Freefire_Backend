import uuid
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from app.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    league_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    entry_fee = Column(Integer, nullable=False)
    division = Column(
        SAEnum("1v1", "2v2", "3v3", "4v4", "br", name="room_division_type"),
        nullable=False,
    )
    max_players = Column(Integer, nullable=False)
    current_players = Column(Integer, nullable=False, default=0)
    status = Column(
        SAEnum("open", "closed", "in_progress", "completed", name="room_status"),
        nullable=False,
        server_default="open",
    )
    # The in-game Room ID that admin gets from Free Fire and shares with joined players.
    # Only revealed to users who have successfully joined the room.
    admin_room_id = Column(String(50), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    starts_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    league = relationship("League", back_populates="rooms")
    creator = relationship("User", back_populates="created_rooms", foreign_keys=[created_by])
    players = relationship("RoomPlayer", back_populates="room", cascade="all, delete-orphan")
    match = relationship("Match", back_populates="room", uselist=False)


class RoomPlayer(Base):
    """
    Join table between users and rooms.
    Captures the free_fire_id at the moment of joining (user may update it later,
    but what matters is what they registered with when they joined).
    """
    __tablename__ = "room_players"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    room_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    free_fire_id = Column(String(50), nullable=False)  # snapshot at join time
    joined_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    # Filled by admin after match ends
    position = Column(Integer, nullable=True)
    kills = Column(Integer, nullable=True)
    points = Column(Integer, nullable=True)

    __table_args__ = (
        # A user can only join a specific room once
        UniqueConstraint("room_id", "user_id", name="uq_room_player"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    room = relationship("Room", back_populates="players")
    user = relationship("User", back_populates="room_players")
