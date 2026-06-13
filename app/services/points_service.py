from __future__ import annotations

from typing import Optional

from app.database import db
from app.models import new_id, now


def add_points(user_id: str, points: int, reason: str) -> None:
    """Add points to a user and append an entry to the points log."""
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
    limit: int = 20,
) -> list[dict]:
    """Aggregate points from the points log, optionally filtered by month prefix and domain, grouped by user and sorted descending."""
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
    return leaderboard[:limit]


def get_user_points(user_id: str) -> int:
    """Return the total points for a given user."""
    user = db.users.get(user_id)
    if not user:
        return 0
    return user.get("points", 0)
