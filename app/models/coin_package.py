import uuid
from sqlalchemy import Column, Integer, Boolean, TIMESTAMP, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.expression import text
from app.database import Base


class CoinPackage(Base):
    """
    Coin purchase packages — single source of truth for pricing.
    Admin manages these via /admin/coin-packages.
    Frontend fetches via GET /coin-packages (public, active only).

    Prices stored as integers (rupees). No floats — avoids floating-point bugs.
    Example: price_inr=80 means ₹80.
    """
    __tablename__ = "coin_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    coins = Column(Integer, nullable=False, comment="Coins user receives on purchase")
    price_inr = Column(Integer, nullable=False, comment="Price in Indian Rupees (integer)")
    is_active = Column(Boolean, nullable=False, default=True, server_default="True",
                       comment="Only active packages are shown to users")
    is_popular = Column(Boolean, nullable=False, default=False, server_default="False",
                        comment="Shows a 'Popular' badge on the package in UI")
    sort_order = Column(Integer, nullable=False, default=0,
                        comment="Lower number = shown first. Controls display order.")
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
