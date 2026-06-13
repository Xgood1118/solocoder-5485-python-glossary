from __future__ import annotations

from fastapi import APIRouter, Query

from app.models import TermGraph
from app.services import graph_service

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/{term_id}", response_model=TermGraph)
def get_term_graph(term_id: str, depth: int = Query(1)):
    """Get the relationship graph for a term."""
    return graph_service.get_term_graph(term_id, depth=depth)
