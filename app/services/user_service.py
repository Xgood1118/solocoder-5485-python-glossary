from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional
from uuid import uuid4

from app.config import (
    RATE_LIMIT_BATCH_PER_MINUTE,
    RATE_LIMIT_PER_MINUTE,
    VALID_DOMAINS,
    VALID_ROLES,
)
from app.database import db
from app.models import UserCreate, UserLogin, new_id, now


_rate_limits: dict[str, dict[str, int]] = {}


def _hash_password(password: str) -> str:
    """Return SHA-256 hex digest of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()


def _user_dict(user: dict) -> dict:
    """Return a copy of user dict without the password_hash field."""
    return {k: v for k, v in user.items() if k != "password_hash"}


def create_user(data: UserCreate) -> dict:
    """Create a new user with hashed password after validating role and domains."""
    if data.role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {data.role}")
    for domain in data.domains:
        if domain not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {domain}")

    user_id = new_id()
    ts = now().isoformat()
    user = {
        "user_id": user_id,
        "username": data.username,
        "password_hash": _hash_password(data.password),
        "role": data.role,
        "email": data.email,
        "domains": list(data.domains),
        "points": 0,
        "created_at": ts,
    }
    db.users[user_id] = user
    return _user_dict(user)


def login(data: UserLogin) -> Optional[dict]:
    """Authenticate a user by username and password, issue a token on success."""
    for user in db.users.values():
        if user.get("username") == data.username and user.get("password_hash") == _hash_password(data.password):
            token = str(uuid4())
            db.user_tokens[token] = user["user_id"]
            return {"token": token, "user": _user_dict(user)}
    return None


def get_user_by_token(token: str) -> Optional[dict]:
    """Look up the user associated with a token and return the user dict."""
    user_id = db.user_tokens.get(token)
    if not user_id:
        return None
    user = db.users.get(user_id)
    if not user:
        return None
    return _user_dict(user)


def get_user(user_id: str) -> Optional[dict]:
    """Return a user dict by user_id, excluding the password hash."""
    user = db.users.get(user_id)
    if not user:
        return None
    return _user_dict(user)


def list_users(role: str = None, skip: int = 0, limit: int = 50) -> list[dict]:
    """Return a list of users with optional role filter, without password hashes."""
    results = []
    for user in db.users.values():
        if role and user.get("role") != role:
            continue
        results.append(_user_dict(user))
    return results[skip : skip + limit]


def update_user(user_id: str, role: str = None, email: str = None, domains: list[str] = None) -> Optional[dict]:
    """Update user fields. Only admin users can change roles."""
    user = db.users.get(user_id)
    if not user:
        return None

    if role is not None:
        if user.get("role") != "admin":
            raise ValueError("Only admin can change roles")
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}")
        user["role"] = role

    if email is not None:
        user["email"] = email

    if domains is not None:
        for domain in domains:
            if domain not in VALID_DOMAINS:
                raise ValueError(f"Invalid domain: {domain}")
        user["domains"] = list(domains)

    return _user_dict(user)


def delete_user(user_id: str) -> bool:
    """Delete a user and clean up all associated tokens."""
    if user_id not in db.users:
        return False
    del db.users[user_id]
    tokens_to_remove = [t for t, uid in db.user_tokens.items() if uid == user_id]
    for token in tokens_to_remove:
        del db.user_tokens[token]
    return True


def check_acl(user: dict, term: dict, action: str) -> bool:
    """Check whether a user has permission for the given action on a term."""
    role = user.get("role", "")

    if role == "admin":
        return True

    if role == "readonly":
        if action != "read":
            return False
        return term.get("status") == "approved"

    if role == "domain_lead":
        if term.get("domain") not in user.get("domains", []):
            return False

    acl = term.get("acl", {})
    if not acl:
        return True

    actions = acl.get(role, [])
    return action in actions


def check_rate_limit(user_id: str, is_batch: bool = False) -> bool:
    """Check whether the user is within their per-minute rate limit."""
    minute_key = datetime.utcnow().strftime("%Y%m%d%H%M")
    limit = RATE_LIMIT_BATCH_PER_MINUTE if is_batch else RATE_LIMIT_PER_MINUTE

    if user_id not in _rate_limits:
        _rate_limits[user_id] = {}

    user_limits = _rate_limits[user_id]
    count = user_limits.get(minute_key, 0)

    if count >= limit:
        return False

    user_limits[minute_key] = count + 1
    return True
