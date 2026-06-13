from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models import MeetingCreate, MeetingSessionOut, MeetingVote
from app.services import meeting_service

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.post("/", response_model=MeetingSessionOut, status_code=status.HTTP_201_CREATED)
def create_meeting(body: MeetingCreate, x_user_id: Optional[str] = Header(None)):
    """Create a new meeting session."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    return meeting_service.create_meeting(body, x_user_id)


@router.get("/", response_model=list[MeetingSessionOut])
def list_meetings(status_param: Optional[str] = Query(None, alias="status")):
    """List meeting sessions with optional status filter."""
    return meeting_service.list_meetings(status=status_param)


@router.get("/{meeting_id}", response_model=MeetingSessionOut)
def get_meeting(meeting_id: str):
    """Get a meeting session by ID."""
    result = meeting_service.get_meeting(meeting_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return result


@router.post("/{meeting_id}/terms", response_model=MeetingSessionOut)
def add_terms_to_meeting(meeting_id: str, body: dict):
    """Add terms to a meeting session."""
    result = meeting_service.add_terms_to_meeting(meeting_id, body.get("term_ids", []))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return result


@router.post("/{meeting_id}/vote")
def vote_on_term(meeting_id: str, body: MeetingVote, x_user_id: Optional[str] = Header(None)):
    """Vote on a term in a meeting session."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    meeting_service.vote_on_term(meeting_id, body, x_user_id)
    return {"status": "voted"}


@router.post("/{meeting_id}/close", response_model=MeetingSessionOut)
def close_meeting(meeting_id: str, x_user_id: Optional[str] = Header(None)):
    """Close a meeting session."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    result = meeting_service.close_meeting(meeting_id, x_user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return result
