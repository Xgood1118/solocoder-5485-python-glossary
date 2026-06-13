from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel

from app.models import UserCreate, UserLogin, UserOut
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["users"])


class UserUpdateBody(BaseModel):
    role: Optional[str] = None
    email: Optional[str] = None
    domains: Optional[list[str]] = None


def _resolve_user(x_user_id: Optional[str]) -> dict:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    user = user_service.get_user_by_token(x_user_id)
    if not user:
        user = user_service.get_user(x_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token or ID")
    return user


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate):
    """Create a new user."""
    return user_service.create_user(body)


@router.post("/login")
def login(body: UserLogin):
    """Authenticate a user and return a token."""
    result = user_service.login(body)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return result


@router.get("/me", response_model=UserOut)
def get_current_user(x_user_id: Optional[str] = Header(None)):
    """Get the current authenticated user."""
    return _resolve_user(x_user_id)


@router.get("/", response_model=list[UserOut])
def list_users(
    role: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
):
    """List users with optional role filter."""
    return user_service.list_users(role=role, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str):
    """Get a user by ID."""
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    body: UserUpdateBody,
    x_user_id: Optional[str] = Header(None),
):
    """Update a user (admin only)."""
    caller = _resolve_user(x_user_id)
    if caller.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    updated = user_service.update_user(user_id, role=body.role, email=body.email, domains=body.domains)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, x_user_id: Optional[str] = Header(None)):
    """Delete a user (admin only)."""
    caller = _resolve_user(x_user_id)
    if caller.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    deleted = user_service.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
