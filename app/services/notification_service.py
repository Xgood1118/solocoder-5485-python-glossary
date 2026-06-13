from __future__ import annotations

from app.database import db
from app.models import new_id, now


def create_notification(user_id: str, term_id: str, type: str, message: str) -> dict:
    """Create a notification for a user and store it in db.notifications keyed by user_id."""
    notification = {
        "notification_id": new_id(),
        "user_id": user_id,
        "term_id": term_id,
        "type": type,
        "message": message,
        "read": False,
        "created_at": now().isoformat(),
    }
    if user_id not in db.notifications:
        db.notifications[user_id] = []
    db.notifications[user_id].append(notification)
    return notification


def get_notifications(user_id: str, unread_only: bool = False) -> list[dict]:
    """Get notifications for a user, optionally filtered to unread only."""
    notifications = db.notifications.get(user_id, [])
    if unread_only:
        return [n for n in notifications if not n.get("read", False)]
    return list(notifications)


def mark_read(notification_id: str, user_id: str) -> bool:
    """Mark a specific notification as read for a given user. Returns True if found."""
    notifications = db.notifications.get(user_id, [])
    for notification in notifications:
        if notification.get("notification_id") == notification_id:
            notification["read"] = True
            return True
    return False


def notify_status_change(term_id: str, from_status: str, to_status: str) -> None:
    """Send notifications to watchers (term creator and domain subscribers) about a status change."""
    term = db.terms.get(term_id)
    if not term:
        return

    message = f"术语 {term.get('source_term', '')} 状态从 {from_status} 变更为 {to_status}"

    creator_id = term.get("created_by")
    if creator_id:
        create_notification(
            user_id=creator_id,
            term_id=term_id,
            type="status_change",
            message=message,
        )

    domain = term.get("domain", "")
    for subscriber_id, domains in db.subscriptions.items():
        if domain in domains and subscriber_id != creator_id:
            create_notification(
                user_id=subscriber_id,
                term_id=term_id,
                type="status_change",
                message=message,
            )
