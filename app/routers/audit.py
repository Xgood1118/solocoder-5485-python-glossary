from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.models import AuditLogOut
from app.services import audit_service

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogOut])
def get_audit_logs(
    term_id: Optional[str] = Query(None),
    changed_by: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
):
    """Get audit logs with optional filters."""
    return audit_service.get_audit_logs(
        term_id=term_id,
        changed_by=changed_by,
        skip=skip,
        limit=limit,
    )


@router.get("/logs/{term_id}/history", response_model=list[AuditLogOut])
def get_term_history(term_id: str):
    """Get the full audit history for a specific term."""
    return audit_service.get_term_history(term_id)
