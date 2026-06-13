from __future__ import annotations

from datetime import timedelta

from app.database import db
from app.models import new_id, now


def subscribe(user_id: str, domain: str) -> dict:
    """Add a domain to a user's subscriptions."""
    if user_id not in db.subscriptions:
        db.subscriptions[user_id] = []
    if domain not in db.subscriptions[user_id]:
        db.subscriptions[user_id].append(domain)
    return {"user_id": user_id, "domains": db.subscriptions[user_id]}


def unsubscribe(user_id: str, domain: str) -> bool:
    """Remove a domain from a user's subscriptions. Returns True if the domain was found and removed."""
    domains = db.subscriptions.get(user_id, [])
    if domain in domains:
        domains.remove(domain)
        return True
    return False


def get_subscriptions(user_id: str) -> list[str]:
    """Get the list of domains a user is subscribed to."""
    return list(db.subscriptions.get(user_id, []))


def get_weekly_digest(domain: str) -> list[dict]:
    """Get terms changed this week in the given domain based on audit logs within the last 7 days."""
    cutoff = (now() - timedelta(days=7)).isoformat()
    results = []
    seen_term_ids: set[str] = set()
    for log in db.audit_logs:
        if log.get("timestamp", "") < cutoff:
            continue
        term_id = log.get("term_id", "")
        if term_id in seen_term_ids:
            continue
        term = db.terms.get(term_id)
        if not term or term.get("domain") != domain:
            continue
        seen_term_ids.add(term_id)
        results.append(term)
    return results
