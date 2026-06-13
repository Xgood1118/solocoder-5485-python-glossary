from __future__ import annotations

from app.database import db
from app.models import MeetingCreate, StatusChange, new_id, now
from app.services import term_service


def create_meeting(title: str, description: str, term_ids: list[str], user_id: str) -> dict:
    """Create a new meeting with associated terms in db.meetings."""
    meeting_id = new_id()
    votes: dict[str, dict[str, str]] = {}
    meeting = {
        "meeting_id": meeting_id,
        "title": title,
        "description": description,
        "term_ids": list(term_ids),
        "votes": votes,
        "status": "open",
        "created_by": user_id,
        "created_at": now().isoformat(),
    }
    db.meetings[meeting_id] = meeting
    return meeting


def add_terms_to_meeting(meeting_id: str, term_ids: list[str]) -> dict:
    """Add terms to an existing meeting."""
    meeting = db.meetings.get(meeting_id)
    if not meeting:
        return {}
    existing = set(meeting.get("term_ids", []))
    for tid in term_ids:
        if tid not in existing:
            meeting["term_ids"].append(tid)
            existing.add(tid)
    return meeting


def vote_on_term(meeting_id: str, term_id: str, vote: str, user_id: str) -> dict:
    """Record a vote (approve/reject) for a term in a meeting."""
    meeting = db.meetings.get(meeting_id)
    if not meeting:
        return {}
    if term_id not in meeting.get("term_ids", []):
        return {}

    if term_id not in meeting["votes"]:
        meeting["votes"][term_id] = {}
    meeting["votes"][term_id][user_id] = vote
    return meeting


def close_meeting(meeting_id: str) -> dict:
    """Close a meeting and apply majority votes to term statuses via term_service.change_status."""
    meeting = db.meetings.get(meeting_id)
    if not meeting:
        return {}

    meeting["status"] = "closed"

    for term_id in meeting.get("term_ids", []):
        term_votes = meeting.get("votes", {}).get(term_id, {})
        if not term_votes:
            continue

        approve_count = sum(1 for v in term_votes.values() if v == "approve")
        reject_count = sum(1 for v in term_votes.values() if v == "reject")

        term = db.terms.get(term_id)
        if not term:
            continue

        if approve_count > reject_count:
            change = StatusChange(to_status="approved", reason="meeting_vote_approved")
            term_service.change_status(term_id, change, meeting.get("created_by", ""))
        elif reject_count > approve_count:
            change = StatusChange(to_status="deprecated", reason="meeting_vote_rejected")
            term_service.change_status(term_id, change, meeting.get("created_by", ""))

    return meeting


def get_meeting(meeting_id: str) -> dict:
    """Get a meeting by its ID."""
    return db.meetings.get(meeting_id, {})


def list_meetings(status: str | None = None) -> list[dict]:
    """List all meetings, optionally filtered by status."""
    meetings = list(db.meetings.values())
    if status is not None:
        meetings = [m for m in meetings if m.get("status") == status]
    return meetings
