from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, Query

from app.models import LookupHit, LookupRequest
from app.services import learning_service, lookup_service

router = APIRouter(prefix="/api/terms", tags=["lookup"])


@router.post("/lookup", response_model=list[LookupHit])
def lookup_text(body: LookupRequest, x_user_id: Optional[str] = Header(None)):
    """Batch lookup approved terms in text."""
    hits = lookup_service.lookup_text(body)
    if x_user_id:
        for hit in hits:
            learning_service.record_query(x_user_id, hit.term_id)
    return hits


@router.get("/search", response_model=list[dict])
def search_terms(
    query: str = Query(...),
    source_lang: Optional[str] = Query(None),
    target_lang: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
):
    """Search terms with fuzzy matching."""
    return lookup_service.search_terms(
        query=query,
        source_lang=source_lang,
        target_lang=target_lang,
        domain=domain,
        status=status,
        skip=skip,
        limit=limit,
    )
