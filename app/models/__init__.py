# models/__init__.py
# Import all models here so that:
# 1. Alembic's env.py can import this single module and detect all tables.
# 2. SQLAlchemy relationship() calls resolve correctly (all classes in same metadata).
# Order matters: models with no foreign keys first, then dependents.

from app.models.user import User
from app.models.league import League, Division
from app.models.room import Room, RoomPlayer
from app.models.wallet import Wallet, Transaction
from app.models.match import Match
from app.models.otp import OTPRecord
from app.models.audit_log import AuditLog
from app.models.coin_package import CoinPackage

__all__ = [
    "User",
    "League",
    "Division",
    "Room",
    "RoomPlayer",
    "Wallet",
    "Transaction",
    "Match",
    "OTPRecord",
    "AuditLog",
    "CoinPackage",
]
