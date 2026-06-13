from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.models import LeaderboardEntry
from app.services import points_service

router = APIRouter(prefix="/api/points", tags=["points"])


@router.get("/leaderboard")
def get_leaderboard(
    month: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    limit: int = Query(20),
):
    """Get the points leaderboard."""
    return points_service.get_leaderboard(month=month, domain=domain, limit=limit)


@router.get("/{user_id}")
def get_user_points(user_id: str):
    """Get total points for a user."""
    pts = points_service.get_user_points(user_id)
    return {"points": pts}
