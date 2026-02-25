"""
Coin packages router — public endpoint.

GET /coin-packages
  Returns all active packages ordered by sort_order.
  No auth required — frontend needs these before the user has logged in
  (e.g., to show pricing on landing page or in buy-coins modal).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.coin_package import CoinPackage
from app.schemas.coin_package import CoinPackageOut

router = APIRouter()


@router.get("", response_model=List[CoinPackageOut])
def list_coin_packages(db: Session = Depends(get_db)):
    """
    Return all active coin packages sorted by display order.
    Used by the wallet page and the navbar buy-coins modal.
    """
    packages = (
        db.query(CoinPackage)
        .filter(CoinPackage.is_active == True)
        .order_by(CoinPackage.sort_order.asc(), CoinPackage.coins.asc())
        .all()
    )
    return packages
