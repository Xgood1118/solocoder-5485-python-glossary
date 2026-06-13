from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TermCreate(BaseModel):
    source_term: str
    source_lang: str = "en"
    target_term: str
    target_lang: str = "zh"
    domain: str
    definition: str = ""
    example_source: str = ""
    example_target: str = ""
    forbidden_terms: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    case_sensitive: bool = False
    part_of_speech: str = "noun"
    is_forced: bool = True
    acl: dict[str, list[str]] = Field(default_factory=dict)


class TermUpdate(BaseModel):
    source_term: Optional[str] = None
    source_lang: Optional[str] = None
    target_term: Optional[str] = None
    target_lang: Optional[str] = None
    domain: Optional[str] = None
    definition: Optional[str] = None
    example_source: Optional[str] = None
    example_target: Optional[str] = None
    forbidden_terms: Optional[list[str]] = None
    synonyms: Optional[list[str]] = None
    case_sensitive: Optional[bool] = None
    part_of_speech: Optional[str] = None
    is_forced: Optional[bool] = None
    acl: Optional[dict[str, list[str]]] = None


class TermOut(BaseModel):
    term_id: str
    source_term: str
    source_lang: str
    target_term: str
    target_lang: str
    domain: str
    definition: str
    example_source: str
    example_target: str
    forbidden_terms: list[str]
    synonyms: list[str]
    case_sensitive: bool
    part_of_speech: str
    is_forced: bool
    status: str
    created_by: str
    reviewer: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    version: int
    acl: dict[str, list[str]]
    created_at: datetime
    updated_at: datetime


class StatusChange(BaseModel):
    to_status: str
    reviewer: Optional[str] = None
    reason: str = ""


class AuditLogOut(BaseModel):
    log_id: str
    term_id: str
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    from_version: Optional[int] = None
    to_version: Optional[int] = None
    changed_by: str
    reason: str
    timestamp: datetime
    diff: Optional[dict] = None


class LookupRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "zh"
    domains: Optional[list[str]] = None


class LookupHit(BaseModel):
    term_id: str
    source_term: str
    target_term: str
    domain: str
    position: int
    length: int
    is_forced: bool
    forbidden_terms: list[str]
    synonyms: list[str]


class CheckRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "zh"
    domain: Optional[str] = None


class ConflictItem(BaseModel):
    term_id: str
    source_term: str
    expected_target: str
    actual_in_text: Optional[str] = None
    conflict_type: str
    details: str


class CheckResponse(BaseModel):
    conflicts: list[ConflictItem]
    total_terms_checked: int


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "translator"
    email: str = ""
    domains: list[str] = Field(default_factory=list)


class UserOut(BaseModel):
    user_id: str
    username: str
    role: str
    email: str
    domains: list[str]
    points: int
    created_at: datetime


class UserLogin(BaseModel):
    username: str
    password: str


class TermVersionOut(BaseModel):
    term_id: str
    version: int
    data: dict
    created_at: datetime
    created_by: str


class VersionDiff(BaseModel):
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class BatchStatusChange(BaseModel):
    term_ids: list[str]
    to_status: str
    reviewer: Optional[str] = None
    reason: str = ""


class RollbackRequest(BaseModel):
    target_version: int
    reason: str = ""


class MeetingCreate(BaseModel):
    title: str
    description: str = ""
    term_ids: list[str] = Field(default_factory=list)


class MeetingVote(BaseModel):
    term_id: str
    vote: str


class MeetingSessionOut(BaseModel):
    meeting_id: str
    title: str
    description: str
    term_ids: list[str]
    votes: dict[str, dict[str, str]]
    status: str
    created_by: str
    created_at: datetime


class SubscriptionCreate(BaseModel):
    domain: str


class RecommendationRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "zh"
    domain: Optional[str] = None


class RecommendationOut(BaseModel):
    suggested_term: str
    reason: str
    confidence: float


class GraphNode(BaseModel):
    term_id: str
    source_term: str
    target_term: str
    domain: str


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str
    weight: float


class TermGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class ExportFilter(BaseModel):
    status: Optional[str] = None
    domain: Optional[str] = None
    approved_by: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class LeaderboardEntry(BaseModel):
    user_id: str
    username: str
    points: int
    domain: str
    month: str


class NotificationOut(BaseModel):
    notification_id: str
    user_id: str
    term_id: Optional[str] = None
    type: str
    message: str
    read: bool
    created_at: datetime


class StatisticsOut(BaseModel):
    total_terms: int
    by_domain: dict[str, int]
    by_status: dict[str, int]
    by_user: dict[str, int]
    review_counts_by_period: dict[str, int]


class TermUsageStats(BaseModel):
    term_id: str
    source_term: str
    document_count: int
    hit_rate: float
    adoption_rate: float


class UserPreferenceStats(BaseModel):
    user_id: str
    username: str
    domain_preferences: dict[str, int]


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.utcnow()
