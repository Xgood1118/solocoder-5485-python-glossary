from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.config import (
    POINTS_APPROVED,
    POINTS_CREATE,
    POINTS_REJECTED,
    ROLLBACK_WINDOW_DAYS,
    VALID_DOMAINS,
    VALID_PARTS_OF_SPEECH,
    VALID_STATUSES,
)
from app.database import db
from app.models import TermCreate, TermUpdate, StatusChange, new_id, now
from app.services import audit_service


VALID_TRANSITIONS = {
    ("draft", "approved"),
    ("draft", "deprecated"),
    ("approved", "deprecated"),
}

_VERSION_FIELDS = [
    "source_term", "source_lang", "target_term", "target_lang",
    "domain", "definition", "example_source", "example_target",
    "forbidden_terms", "synonyms", "case_sensitive", "part_of_speech",
    "is_forced", "acl",
]


def _get_user(user_id: str) -> Optional[dict]:
    """Look up a user dict by user_id."""
    return db.users.get(user_id)


def _can_read(term: dict, user: dict) -> bool:
    """Check whether a user is allowed to read the given term."""
    role = user.get("role", "")
    if role == "admin":
        return True
    if role == "readonly":
        return term.get("status") == "approved"
    if role == "domain_lead":
        if term.get("domain") not in user.get("domains", []):
            return False
    acl = term.get("acl", {})
    if not acl:
        return True
    actions = acl.get(role, [])
    return "read" in actions


def _can_write(term: dict, user: dict) -> bool:
    """Check whether a user is allowed to modify the given term."""
    role = user.get("role", "")
    if role == "admin":
        return True
    if role == "readonly":
        return False
    if role == "domain_lead":
        if term.get("domain") not in user.get("domains", []):
            return False
    acl = term.get("acl", {})
    if not acl:
        return True
    actions = acl.get(role, [])
    return "write" in actions


def _save_version(term: dict, user_id: str) -> None:
    """Persist a version snapshot for a term."""
    snapshot = {f: term.get(f) for f in _VERSION_FIELDS}
    version_entry = {
        "term_id": term["term_id"],
        "version": term["version"],
        "data": snapshot,
        "created_at": term["updated_at"],
        "created_by": user_id,
    }
    versions = db.term_versions.setdefault(term["term_id"], [])
    versions.append(version_entry)


def _compute_diff(old_data: dict, new_data: dict) -> dict:
    """Return a dict mapping changed field names to {old, new} value pairs."""
    diff = {}
    all_keys = set(old_data.keys()) | set(new_data.keys())
    for key in all_keys:
        old_val = old_data.get(key)
        new_val = new_data.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    return diff


def check_uniqueness(
    source_term: str,
    source_lang: str,
    target_lang: str,
    domain: str,
    exclude_term_id: Optional[str] = None,
) -> bool:
    """Return True when no approved term shares the same source_term, source_lang, target_lang and domain."""
    for t in db.terms.values():
        if t.get("status") != "approved":
            continue
        if exclude_term_id and t["term_id"] == exclude_term_id:
            continue
        if (
            t["source_term"] == source_term
            and t["source_lang"] == source_lang
            and t["target_lang"] == target_lang
            and t["domain"] == domain
        ):
            return False
    return True


def create_term(data: TermCreate, user_id: str) -> dict:
    """Create a new term in draft status with version 1, record audit log and award points."""
    if data.domain not in VALID_DOMAINS:
        raise ValueError(f"Invalid domain: {data.domain}")
    if data.part_of_speech not in VALID_PARTS_OF_SPEECH:
        raise ValueError(f"Invalid part_of_speech: {data.part_of_speech}")

    ts = now().isoformat()
    term_id = new_id()
    term = {
        "term_id": term_id,
        "source_term": data.source_term,
        "source_lang": data.source_lang,
        "target_term": data.target_term,
        "target_lang": data.target_lang,
        "domain": data.domain,
        "definition": data.definition,
        "example_source": data.example_source,
        "example_target": data.example_target,
        "forbidden_terms": list(data.forbidden_terms),
        "synonyms": list(data.synonyms),
        "case_sensitive": data.case_sensitive,
        "part_of_speech": data.part_of_speech,
        "is_forced": data.is_forced,
        "status": "draft",
        "created_by": user_id,
        "reviewer": None,
        "approved_by": None,
        "approved_at": None,
        "version": 1,
        "acl": dict(data.acl) if data.acl else {},
        "created_at": ts,
        "updated_at": ts,
    }

    db.terms[term_id] = term
    _save_version(term, user_id)

    audit_service.add_audit_log(
        term_id=term_id,
        action="create",
        from_status=None,
        to_status="draft",
        from_version=None,
        to_version=1,
        changed_by=user_id,
        reason="",
        diff=None,
    )

    audit_service.add_points(user_id=user_id, points=POINTS_CREATE, reason="term_created")

    db.fts_insert(
        term_id,
        data.source_term,
        data.target_term,
        data.definition,
        data.domain,
        data.source_lang,
        data.target_lang,
    )

    return term


def get_term(term_id: str, user_id: str) -> Optional[dict]:
    """Retrieve a single term by ID after passing the ACL read check."""
    term = db.terms.get(term_id)
    if not term:
        return None
    user = _get_user(user_id)
    if not user or not _can_read(term, user):
        return None
    return term


def update_term(term_id: str, data: TermUpdate, user_id: str) -> Optional[dict]:
    """Update non-None fields on a term, bump version, save snapshot and log the diff."""
    term = db.terms.get(term_id)
    if not term:
        return None
    user = _get_user(user_id)
    if not user or not _can_write(term, user):
        return None

    old_data = {f: term.get(f) for f in _VERSION_FIELDS}
    update_fields = data.model_dump(exclude_none=True)

    if "domain" in update_fields and update_fields["domain"] not in VALID_DOMAINS:
        raise ValueError(f"Invalid domain: {update_fields['domain']}")
    if "part_of_speech" in update_fields and update_fields["part_of_speech"] not in VALID_PARTS_OF_SPEECH:
        raise ValueError(f"Invalid part_of_speech: {update_fields['part_of_speech']}")
    if "status" in update_fields and update_fields["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {update_fields['status']}")

    for key, value in update_fields.items():
        term[key] = value

    term["version"] += 1
    term["updated_at"] = now().isoformat()

    new_data = {f: term.get(f) for f in _VERSION_FIELDS}
    diff = _compute_diff(old_data, new_data)

    _save_version(term, user_id)

    audit_service.add_audit_log(
        term_id=term_id,
        action="update",
        from_status=term["status"],
        to_status=term["status"],
        from_version=term["version"] - 1,
        to_version=term["version"],
        changed_by=user_id,
        reason="",
        diff=diff,
    )

    db.fts_update(
        term_id,
        term["source_term"],
        term["target_term"],
        term.get("definition", ""),
        term["domain"],
        term["source_lang"],
        term["target_lang"],
    )

    return term


def change_status(term_id: str, change: StatusChange, user_id: str) -> Optional[dict]:
    """Transition a term between statuses following the state machine, with uniqueness and points logic."""
    term = db.terms.get(term_id)
    if not term:
        return None
    user = _get_user(user_id)
    if not user or not _can_write(term, user):
        return None

    from_status = term["status"]
    to_status = change.to_status

    if to_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {to_status}")

    if change.reviewer:
        reviewer_user = _get_user(change.reviewer)
        if not reviewer_user:
            raise ValueError(f"Reviewer user not found: {change.reviewer}")
        if reviewer_user.get("role") not in ("reviewer", "domain_lead", "admin"):
            raise ValueError(f"User {change.reviewer} does not have reviewer permissions")

    transition = (from_status, to_status)
    if transition not in VALID_TRANSITIONS:
        raise ValueError(f"Invalid status transition: {from_status} -> {to_status}")

    if to_status == "approved":
        if not check_uniqueness(
            term["source_term"],
            term["source_lang"],
            term["target_lang"],
            term["domain"],
            exclude_term_id=term_id,
        ):
            raise ValueError(
                "Duplicate approved term with same source_term, source_lang, target_lang, domain"
            )

    old_version = term["version"]
    term["status"] = to_status
    term["updated_at"] = now().isoformat()

    if to_status == "approved":
        term["approved_by"] = change.reviewer or user_id
        term["approved_at"] = now().isoformat()
        term["reviewer"] = change.reviewer or user_id
        audit_service.add_points(user_id=user_id, points=POINTS_APPROVED, reason="term_approved")
    elif from_status == "draft" and to_status == "deprecated":
        term["reviewer"] = change.reviewer or user_id
        audit_service.add_points(user_id=user_id, points=POINTS_REJECTED, reason="term_rejected")

    audit_service.add_audit_log(
        term_id=term_id,
        action="status_change",
        from_status=from_status,
        to_status=to_status,
        from_version=old_version,
        to_version=old_version,
        changed_by=user_id,
        reason=change.reason,
        diff=None,
    )

    return term


def list_terms(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> list:
    """Return a filtered, ACL-enforced slice of terms."""
    user = _get_user(user_id) if user_id else None
    results = []
    for term in db.terms.values():
        if user and not _can_read(term, user):
            continue
        if domain and term.get("domain") != domain:
            continue
        if status and term.get("status") != status:
            continue
        if source_lang and term.get("source_lang") != source_lang:
            continue
        if target_lang and term.get("target_lang") != target_lang:
            continue
        results.append(term)
    return results[skip : skip + limit]


def delete_term(term_id: str, user_id: str) -> bool:
    """Permanently remove a term (admin only) and delete from FTS."""
    user = _get_user(user_id)
    if not user or user.get("role") != "admin":
        return False
    term = db.terms.pop(term_id, None)
    if not term:
        return False
    db.fts_delete(term_id)
    return True


def get_version(term_id: str, version: int) -> Optional[dict]:
    """Retrieve a specific version snapshot for a term."""
    versions = db.term_versions.get(term_id, [])
    for v in versions:
        if v["version"] == version:
            return v
    return None


def get_version_diff(term_id: str, v1: int, v2: int) -> list[dict]:
    """Compare two version snapshots field by field and return a list of differences."""
    ver1 = get_version(term_id, v1)
    ver2 = get_version(term_id, v2)
    if not ver1 or not ver2:
        return []
    data1 = ver1.get("data", {})
    data2 = ver2.get("data", {})
    all_keys = sorted(set(data1.keys()) | set(data2.keys()))
    diffs = []
    for key in all_keys:
        old_val = data1.get(key)
        new_val = data2.get(key)
        if old_val != new_val:
            diffs.append({"field": key, "old_value": old_val, "new_value": new_val})
    return diffs


def rollback_term(term_id: str, target_version: int, reason: str, user_id: str) -> Optional[dict]:
    """Restore a term to a previous version within the rollback window, creating a new version entry."""
    term = db.terms.get(term_id)
    if not term:
        return None
    user = _get_user(user_id)
    if not user or not _can_write(term, user):
        return None

    target = get_version(term_id, target_version)
    if not target:
        return None

    updated_at_dt = datetime.fromisoformat(term["updated_at"])
    window = timedelta(days=ROLLBACK_WINDOW_DAYS)
    if now() - updated_at_dt > window:
        raise ValueError(f"Rollback is only allowed within {ROLLBACK_WINDOW_DAYS} days of last update")

    old_data = {f: term.get(f) for f in _VERSION_FIELDS}
    old_version = term["version"]

    for key, value in target["data"].items():
        term[key] = value

    term["version"] = old_version + 1
    term["updated_at"] = now().isoformat()

    new_data = {f: term.get(f) for f in _VERSION_FIELDS}
    diff = _compute_diff(old_data, new_data)

    _save_version(term, user_id)

    audit_service.add_audit_log(
        term_id=term_id,
        action="rollback",
        from_status=term["status"],
        to_status=term["status"],
        from_version=old_version,
        to_version=term["version"],
        changed_by=user_id,
        reason=reason,
        diff=diff,
    )

    db.fts_update(
        term_id,
        term["source_term"],
        term["target_term"],
        term.get("definition", ""),
        term["domain"],
        term["source_lang"],
        term["target_lang"],
    )

    return term
