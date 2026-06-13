from __future__ import annotations

from fastapi import APIRouter

from app.models import StatisticsOut, TermUsageStats, UserPreferenceStats
from app.services import statistics_service

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


@router.get("/overview", response_model=StatisticsOut)
def get_overview_statistics():
    """Get overall glossary statistics."""
    return statistics_service.get_overall_statistics()


@router.get("/term/{term_id}/usage", response_model=TermUsageStats)
def get_term_usage(term_id: str):
    """Get usage statistics for a specific term."""
    return statistics_service.get_term_usage(term_id)


@router.get("/user/{user_id}/preferences", response_model=UserPreferenceStats)
def get_user_preferences(user_id: str):
    """Get preference statistics for a specific user."""
    return statistics_service.get_user_preferences(user_id)
