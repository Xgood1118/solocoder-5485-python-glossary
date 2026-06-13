from __future__ import annotations

from collections import Counter

from app.database import db
from app.models import new_id, now


def get_overall_statistics() -> dict:
    """Return overall statistics including total terms, breakdowns by domain/status/user, and review counts by period."""
    by_domain: dict[str, int] = Counter()
    by_status: dict[str, int] = Counter()
    by_user: dict[str, int] = Counter()
    review_counts_by_period: dict[str, int] = Counter()

    for term in db.terms.values():
        by_domain[term.get("domain", "")] += 1
        by_status[term.get("status", "")] += 1
        by_user[term.get("created_by", "")] += 1

    for log in db.audit_logs:
        if log.get("action") == "status_change":
            ts = log.get("timestamp", "")
            period = ts[:7] if len(ts) >= 7 else ts
            review_counts_by_period[period] += 1

    return {
        "total_terms": len(db.terms),
        "by_domain": dict(by_domain),
        "by_status": dict(by_status),
        "by_user": dict(by_user),
        "review_counts_by_period": dict(review_counts_by_period),
    }


def get_term_usage(term_id: str) -> dict:
    """Return usage statistics for a specific term including document count, hit rate, and adoption rate."""
    usage = db.term_usage.get(term_id, {})
    return {
        "term_id": term_id,
        "document_count": usage.get("document_count", 0),
        "hit_rate": usage.get("hit_rate", 0.0),
        "adoption_rate": usage.get("adoption_rate", 0.0),
    }


def record_term_usage(term_id: str, document_id: str, was_adopted: bool) -> None:
    """Track term usage in documents, updating document count and adoption rate."""
    if term_id not in db.term_usage:
        db.term_usage[term_id] = {
            "document_count": 0,
            "adopted_count": 0,
            "hit_rate": 0.0,
            "adoption_rate": 0.0,
            "documents": set(),
        }

    usage = db.term_usage[term_id]
    if document_id not in usage.get("documents", set()):
        usage.setdefault("documents", set()).add(document_id)
        usage["document_count"] += 1
        if was_adopted:
            usage["adopted_count"] = usage.get("adopted_count", 0) + 1
        if usage["document_count"] > 0:
            usage["adoption_rate"] = usage.get("adopted_count", 0) / usage["document_count"]
        usage["hit_rate"] = usage["document_count"]


def get_user_preferences(user_id: str) -> dict:
    """Return a user's domain preferences based on their query history."""
    domain_prefs: dict[str, int] = Counter()
    history = db.query_history.get(user_id, [])
    for entry in history:
        term_id = entry.get("term_id", "")
        term = db.terms.get(term_id)
        if term:
            domain_prefs[term.get("domain", "")] += 1

    user = db.users.get(user_id, {})
    return {
        "user_id": user_id,
        "domain_preferences": dict(domain_prefs),
    }
