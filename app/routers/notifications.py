from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models import NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationOut])
def get_notifications(
    x_user_id: Optional[str] = Header(None),
    unread_only: bool = Query(False),
):
    """Get notifications for the current user."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    return notification_service.get_notifications(x_user_id, unread_only=unread_only)


@router.patch("/{notification_id}/read")
def mark_read(notification_id: str, x_user_id: Optional[str] = Header(None)):
    """Mark a notification as read."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    result = notification_service.mark_read(notification_id, x_user_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"status": "read"}
