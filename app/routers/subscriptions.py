from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from app.models import SubscriptionCreate
from app.services import subscription_service

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.post("/")
def subscribe(body: SubscriptionCreate, x_user_id: Optional[str] = Header(None)):
    """Subscribe to a domain."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    subscription_service.subscribe(x_user_id, body.domain)
    return {"subscribed": body.domain}


@router.delete("/{domain}")
def unsubscribe(domain: str, x_user_id: Optional[str] = Header(None)):
    """Unsubscribe from a domain."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    subscription_service.unsubscribe(x_user_id, domain)
    return {"unsubscribed": domain}


@router.get("/", response_model=list[str])
def get_subscriptions(x_user_id: Optional[str] = Header(None)):
    """Get the current user's domain subscriptions."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    return subscription_service.get_subscriptions(x_user_id)


@router.get("/digest/{domain}", response_model=list[dict])
def get_weekly_digest(domain: str):
    """Get the weekly digest for a domain."""
    return subscription_service.get_weekly_digest(domain)
