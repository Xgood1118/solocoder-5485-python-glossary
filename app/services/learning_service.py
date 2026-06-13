from __future__ import annotations

from app.database import db
from app.models import new_id, now


def record_query(user_id: str, term_id: str) -> None:
    """Record a query in the user's query history, keeping at most 100 entries per user."""
    if user_id not in db.query_history:
        db.query_history[user_id] = []
    db.query_history[user_id].append({
        "term_id": term_id,
        "timestamp": now().isoformat(),
    })
    if len(db.query_history[user_id]) > 100:
        db.query_history[user_id] = db.query_history[user_id][-100:]


def get_query_history(user_id: str, limit: int = 20) -> list[dict]:
    """Get the most recent queries for a user, up to the given limit."""
    history = db.query_history.get(user_id, [])
    return list(history[-limit:])
