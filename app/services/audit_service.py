from __future__ import annotations

from typing import Optional

from app.database import db
from app.models import new_id, now


def add_audit_log(
    term_id: str,
    action: str,
    changed_by: str,
    reason: str = "",
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    from_version: Optional[int] = None,
    to_version: Optional[int] = None,
    diff: Optional[dict] = None,
) -> dict:
    """Create an audit log entry and append it to db.audit_logs."""
    entry = {
        "log_id": new_id(),
        "term_id": term_id,
        "action": action,
        "changed_by": changed_by,
        "reason": reason,
        "from_status": from_status,
        "to_status": to_status,
        "from_version": from_version,
        "to_version": to_version,
        "timestamp": now().isoformat(),
        "diff": diff,
    }
    db.audit_logs.append(entry)
    return entry


def get_audit_logs(
    term_id: Optional[str] = None,
    changed_by: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[dict]:
    """Get audit logs with optional filters for term_id and changed_by."""
    logs = db.audit_logs
    if term_id is not None:
        logs = [l for l in logs if l.get("term_id") == term_id]
    if changed_by is not None:
        logs = [l for l in logs if l.get("changed_by") == changed_by]
    return logs[skip : skip + limit]


def get_term_history(term_id: str) -> list[dict]:
    """Get all audit logs for a specific term, sorted by timestamp."""
    return [l for l in db.audit_logs if l.get("term_id") == term_id]


def add_points(user_id: str, points: int, reason: str) -> None:
    """Add points to a user in db.users and append an entry to db.points_log."""
    entry = {
        "log_id": new_id(),
        "user_id": user_id,
        "points": points,
        "reason": reason,
        "timestamp": now().isoformat(),
    }
    db.points_log.append(entry)
    user = db.users.get(user_id)
    if user:
        user["points"] = user.get("points", 0) + points


def get_leaderboard(
    month: Optional[str] = None,
    domain: Optional[str] = None,
) -> list[dict]:
    """Get points leaderboard aggregated from db.points_log, optionally filtered by month and domain."""
    aggregated: dict[str, int] = {}
    for entry in db.points_log:
        ts = entry.get("timestamp", "")
        if month is not None and not ts.startswith(month):
            continue
        if domain is not None:
            uid = entry.get("user_id", "")
            user = db.users.get(uid)
            if not user or domain not in user.get("domains", []):
                continue
        uid = entry.get("user_id", "")
        aggregated[uid] = aggregated.get(uid, 0) + entry.get("points", 0)
    leaderboard = []
    for uid, total_points in aggregated.items():
        user = db.users.get(uid, {})
        leaderboard.append({
            "user_id": uid,
            "username": user.get("username", ""),
            "points": total_points,
        })
    leaderboard.sort(key=lambda x: x["points"], reverse=True)
    return leaderboard
