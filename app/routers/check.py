from __future__ import annotations

from fastapi import APIRouter

from app.models import CheckRequest, CheckResponse
from app.services import check_service

router = APIRouter(prefix="/api/check", tags=["check"])


@router.post("/", response_model=CheckResponse)
def check_text(body: CheckRequest):
    """Check text for term consistency issues."""
    return check_service.check_text(body)
