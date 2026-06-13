from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from app.services import workflow_service

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


@router.post("/check-document", response_model=list[dict])
def check_document_usage(
    body: dict,
    x_user_id: Optional[str] = Header(None),
):
    """Check a document for term usage issues."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    return workflow_service.check_document_usage(
        text=body.get("text", ""),
        source_lang=body.get("source_lang", "en"),
        document_id=body.get("document_id", ""),
        user_id=x_user_id,
    )
