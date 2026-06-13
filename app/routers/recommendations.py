from __future__ import annotations

from fastapi import APIRouter

from app.models import RecommendationOut, RecommendationRequest
from app.services import recommendation_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("/suggest", response_model=list[RecommendationOut])
def suggest_terms(body: RecommendationRequest):
    """Suggest terms from input text."""
    return recommendation_service.suggest_terms(body)


@router.post("/{term_id}/adopt")
def adopt_recommendation(term_id: str):
    """Adopt a term recommendation."""
    recommendation_service.adopt_recommendation(term_id)
    return {"status": "adopted"}


@router.get("/stats")
def get_recommendation_stats():
    """Get recommendation statistics."""
    return recommendation_service.get_recommendation_stats()
