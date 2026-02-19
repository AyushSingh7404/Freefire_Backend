import uuid
from sqlalchemy import Column, Integer, TIMESTAMP, ForeignKey, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from app.database import Base


class Match(Base):
    """
    One Match record per user per room.
    When admin settles a room with 30 players, 30 Match records are created.
    """
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    room_id = Column(
        UUID(as_uuid=True),
        # SET NULL so match history is preserved even if room is deleted
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    league_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leagues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    division = Column(String(10), nullable=False)  # "1v1", "2v2", "3v3", "4v4", "br"
    room_name = Column(String(100), nullable=True)  # snapshot of room name at time of match
    result = Column(
        SAEnum("win", "loss", "draw", name="match_result"),
        nullable=False,
    )
    coins_won = Column(Integer, nullable=False, default=0)
    kills = Column(Integer, nullable=False, default=0)
    position = Column(Integer, nullable=True)
    played_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    room = relationship("Room", back_populates="match")
    user = relationship("User", back_populates="matches")
