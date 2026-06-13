from __future__ import annotations

from app.database import db
from app.models import GraphEdge, GraphNode, TermGraph, new_id, now


def get_term_graph(term_id: str, depth: int = 1) -> dict:
    """Build a relationship graph for a term based on co-occurrence, search co-occurrence, and synonym relationships."""
    term = db.terms.get(term_id)
    if not term:
        return {"nodes": [], "edges": []}

    nodes_dict: dict[str, dict] = {term_id: term}
    edges: list[dict] = []
    visited: set[str] = {term_id}
    frontier: set[str] = {term_id}

    for _ in range(depth):
        next_frontier: set[str] = set()
        for current_id in frontier:
            current_term = db.terms.get(current_id)
            if not current_term:
                continue

            co_occurrences = db.term_co_occurrence.get(current_id, {})
            for related_id, weight in co_occurrences.items():
                if related_id not in visited:
                    related_term = db.terms.get(related_id)
                    if related_term:
                        nodes_dict[related_id] = related_term
                        next_frontier.add(related_id)
                        visited.add(related_id)
                if related_id in nodes_dict:
                    edges.append({
                        "source_id": current_id,
                        "target_id": related_id,
                        "relation": "co_occurrence",
                        "weight": float(weight),
                    })

            search_co = db.search_co_occurrence.get(current_id, {})
            for related_id, weight in search_co.items():
                if related_id not in visited:
                    related_term = db.terms.get(related_id)
                    if related_term:
                        nodes_dict[related_id] = related_term
                        next_frontier.add(related_id)
                        visited.add(related_id)
                if related_id in nodes_dict:
                    edges.append({
                        "source_id": current_id,
                        "target_id": related_id,
                        "relation": "search_co_occurrence",
                        "weight": float(weight),
                    })

            current_synonyms = set(current_term.get("synonyms", []))
            for other_id, other_term in db.terms.items():
                if other_id == current_id or other_id in visited:
                    continue
                other_synonyms = set(other_term.get("synonyms", []))
                if current_synonyms & other_synonyms:
                    nodes_dict[other_id] = other_term
                    next_frontier.add(other_id)
                    visited.add(other_id)
                    edges.append({
                        "source_id": current_id,
                        "target_id": other_id,
                        "relation": "synonym",
                        "weight": 1.0,
                    })

        frontier = next_frontier

    nodes = []
    for tid, t in nodes_dict.items():
        nodes.append({
            "term_id": tid,
            "source_term": t.get("source_term", ""),
            "target_term": t.get("target_term", ""),
            "domain": t.get("domain", ""),
        })

    return {"nodes": nodes, "edges": edges}


def record_co_occurrence(term_ids: list[str]) -> None:
    """Record that the given terms appeared together, incrementing co-occurrence counts."""
    for i, t1 in enumerate(term_ids):
        for t2 in term_ids[i + 1:]:
            if t1 not in db.term_co_occurrence:
                db.term_co_occurrence[t1] = {}
            db.term_co_occurrence[t1][t2] = db.term_co_occurrence[t1].get(t2, 0) + 1

            if t2 not in db.term_co_occurrence:
                db.term_co_occurrence[t2] = {}
            db.term_co_occurrence[t2][t1] = db.term_co_occurrence[t2].get(t1, 0) + 1


def record_search_co_occurrence(term_ids: list[str]) -> None:
    """Record that a user searched for the given terms together, incrementing search co-occurrence counts."""
    for i, t1 in enumerate(term_ids):
        for t2 in term_ids[i + 1:]:
            if t1 not in db.search_co_occurrence:
                db.search_co_occurrence[t1] = {}
            db.search_co_occurrence[t1][t2] = db.search_co_occurrence[t1].get(t2, 0) + 1

            if t2 not in db.search_co_occurrence:
                db.search_co_occurrence[t2] = {}
            db.search_co_occurrence[t2][t1] = db.search_co_occurrence[t2].get(t1, 0) + 1
