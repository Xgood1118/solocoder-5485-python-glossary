from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models import (
    BatchStatusChange,
    RollbackRequest,
    StatusChange,
    TermCreate,
    TermOut,
    TermUpdate,
    VersionDiff,
)
from app.services import term_service
from app.services.user_service import check_acl, get_user_by_token

router = APIRouter(prefix="/api/terms", tags=["terms"])


def _resolve_user(x_user_id: Optional[str]) -> dict:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    user = get_user_by_token(x_user_id)
    if not user:
        from app.services.user_service import get_user
        user = get_user(x_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token or ID")
    return user


@router.post("/", response_model=TermOut, status_code=status.HTTP_201_CREATED)
def create_term(body: TermCreate, x_user_id: Optional[str] = Header(None)):
    """Create a new term."""
    user = _resolve_user(x_user_id)
    try:
        term = term_service.create_term(body, user["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return term


@router.get("/", response_model=list[TermOut])
def list_terms(
    domain: Optional[str] = Query(None),
    status_param: Optional[str] = Query(None, alias="status"),
    source_lang: Optional[str] = Query(None),
    target_lang: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    x_user_id: Optional[str] = Header(None),
):
    """List terms with optional filters."""
    resolved = None
    if x_user_id:
        try:
            resolved = _resolve_user(x_user_id)
        except HTTPException:
            resolved = None
    return term_service.list_terms(
        domain=domain,
        status=status_param,
        source_lang=source_lang,
        target_lang=target_lang,
        user_id=resolved["user_id"] if resolved else None,
        skip=skip,
        limit=limit,
    )


@router.get("/{term_id}", response_model=TermOut)
def get_term(term_id: str, x_user_id: Optional[str] = Header(None)):
    """Get a single term by ID."""
    user = _resolve_user(x_user_id) if x_user_id else None
    term = term_service.get_term(term_id, user["user_id"] if user else "")
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")
    return term


@router.put("/{term_id}", response_model=TermOut)
def update_term(term_id: str, body: TermUpdate, x_user_id: Optional[str] = Header(None)):
    """Update an existing term."""
    user = _resolve_user(x_user_id)
    term = term_service.update_term(term_id, body, user["user_id"])
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found or access denied")
    return term


@router.patch("/{term_id}/status", response_model=TermOut)
def change_status(term_id: str, body: StatusChange, x_user_id: Optional[str] = Header(None)):
    """Change the status of a term following the state machine."""
    user = _resolve_user(x_user_id)
    try:
        term = term_service.change_status(term_id, body, user["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found or access denied")
    return term


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_term(term_id: str, x_user_id: Optional[str] = Header(None)):
    """Delete a term (admin only)."""
    user = _resolve_user(x_user_id)
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    deleted = term_service.delete_term(term_id, user["user_id"])
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")


@router.get("/{term_id}/versions/{version}")
def get_version(term_id: str, version: int):
    """Get a specific version snapshot of a term."""
    result = term_service.get_version(term_id, version)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return result


@router.get("/{term_id}/diff", response_model=list[VersionDiff])
def get_version_diff(term_id: str, v1: int = Query(...), v2: int = Query(...)):
    """Compare two versions of a term."""
    diffs = term_service.get_version_diff(term_id, v1, v2)
    if not diffs and not term_service.get_version(term_id, v1):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return diffs


@router.post("/{term_id}/rollback", response_model=TermOut)
def rollback_term(term_id: str, body: RollbackRequest, x_user_id: Optional[str] = Header(None)):
    """Rollback a term to a previous version."""
    user = _resolve_user(x_user_id)
    try:
        term = term_service.rollback_term(term_id, body.target_version, body.reason, user["user_id"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term or version not found")
    return term


@router.post("/batch/status")
def batch_status_change(body: BatchStatusChange, x_user_id: Optional[str] = Header(None)):
    """Batch change status for multiple terms."""
    user = _resolve_user(x_user_id)
    updated = 0
    errors = 0
    for tid in body.term_ids:
        try:
            result = term_service.change_status(tid, StatusChange(
                to_status=body.to_status,
                reviewer=body.reviewer,
                reason=body.reason,
            ), user["user_id"])
            if result:
                updated += 1
            else:
                errors += 1
        except (ValueError, Exception):
            errors += 1
    return {"updated": updated, "errors": errors}
