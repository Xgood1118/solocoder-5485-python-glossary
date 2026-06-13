from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.services import learning_service

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/history", response_model=list[dict])
def get_query_history(
    x_user_id: Optional[str] = Header(None),
    limit: int = Query(20),
):
    """Get query history for the current user."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    return learning_service.get_query_history(x_user_id, limit=limit)
