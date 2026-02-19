import uuid
from sqlalchemy import Boolean, Column, String, Integer, Text, TIMESTAMP, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from app.database import Base


class League(Base):
    __tablename__ = "leagues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String(100), nullable=False)
    tier = Column(
        SAEnum("silver", "gold", "diamond", "br", name="league_tier"),
        nullable=False,
    )
    entry_fee = Column(Integer, nullable=False, default=0)  # base entry fee in coins
    description = Column(Text, nullable=True)
    max_players = Column(Integer, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, server_default="True", nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    rooms = relationship("Room", back_populates="league")
    divisions = relationship("Division", back_populates="league", cascade="all, delete-orphan")


class Division(Base):
    """
    Stores the per-division entry fees and reward descriptions for each league.
    e.g. Gold League / 1v1: entry_fee=40, rewards_description='Winner gets 60 coins'
    """
    __tablename__ = "divisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    league_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    division_type = Column(
        SAEnum("1v1", "2v2", "3v3", "4v4", "br", name="division_type"),
        nullable=False,
    )
    entry_fee = Column(Integer, nullable=False)
    rewards_description = Column(String(300), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    league = relationship("League", back_populates="divisions")
