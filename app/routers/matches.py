"""
Matches router: current user's match history.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.match import Match
from app.schemas.match import MatchHistoryResponse, MatchOut

router = APIRouter()


@router.get("/history", response_model=MatchHistoryResponse)
def get_match_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Paginated match history for the current user.
    Ordered newest-first (most recent match at top).
    """
    query = db.query(Match).filter(Match.user_id == current_user.id)
    total = query.count()
    matches = (
        query.order_by(Match.played_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return MatchHistoryResponse(
        total=total,
        page=page,
        limit=limit,
        matches=[MatchOut.model_validate(m) for m in matches],
    )
