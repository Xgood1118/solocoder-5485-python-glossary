from __future__ import annotations

from pypinyin import lazy_pinyin

from app.database import db
from app.models import LookupHit, LookupRequest


def lookup_text(request: LookupRequest) -> list[LookupHit]:
    """Find all approved terms whose source_term appears in the request text using N-gram matching."""
    terms = []
    for t in db.terms.values():
        if t.get("status") != "approved":
            continue
        if t["source_lang"] != request.source_lang:
            continue
        if t["target_lang"] != request.target_lang:
            continue
        if request.domains and t["domain"] not in request.domains:
            continue
        terms.append(t)

    hits = _ngram_match(request.text, terms, request.source_lang, request.target_lang)
    hits.sort(key=lambda h: h.position)
    return hits


def search_terms(
    query: str,
    source_lang: str = None,
    target_lang: str = None,
    domain: str = None,
    status: str = None,
    skip: int = 0,
    limit: int = 50,
) -> list[dict]:
    """Fuzzy search using FTS5, substring matching, pinyin, and Levenshtein edit distance."""
    seen_ids: set[str] = set()
    results: list[dict] = []

    fts_ids = _fts_query(query)
    for tid in fts_ids:
        if tid not in seen_ids:
            seen_ids.add(tid)
            term = db.terms.get(tid)
            if term and _matches_filters(term, source_lang, target_lang, domain, status):
                results.append(term)

    query_lower = query.lower()
    for t in db.terms.values():
        if t["term_id"] in seen_ids:
            continue
        if not _matches_filters(t, source_lang, target_lang, domain, status):
            continue

        if query_lower in t["source_term"].lower() or query_lower in t["target_term"].lower():
            seen_ids.add(t["term_id"])
            results.append(t)
            continue

        if _pinyin_match(query_lower, t["source_term"]) or _pinyin_match(query_lower, t["target_term"]):
            seen_ids.add(t["term_id"])
            results.append(t)
            continue

        max_dist = 2 if len(query) <= 5 else 3
        if _levenshtein(query_lower, t["source_term"].lower()) <= max_dist:
            seen_ids.add(t["term_id"])
            results.append(t)
            continue
        if _levenshtein(query_lower, t["target_term"].lower()) <= max_dist:
            seen_ids.add(t["term_id"])
            results.append(t)

    return results[skip : skip + limit]


def _ngram_match(
    text: str,
    terms: list[dict],
    source_lang: str,
    target_lang: str,
) -> list[LookupHit]:
    """N-gram match each term's source_term against the text, preferring longer matches first."""
    sorted_terms = sorted(terms, key=lambda t: len(t["source_term"]), reverse=True)
    hits: list[LookupHit] = []
    covered: list[tuple[int, int]] = []

    for t in sorted_terms:
        source = t["source_term"]
        if not source:
            continue

        start = 0
        while True:
            if t.get("case_sensitive"):
                pos = text.find(source, start)
            else:
                pos = text.lower().find(source.lower(), start)

            if pos == -1:
                break

            end = pos + len(source)
            if not _is_subsumed(pos, end, covered):
                covered.append((pos, end))
                hits.append(
                    LookupHit(
                        term_id=t["term_id"],
                        source_term=t["source_term"],
                        target_term=t["target_term"],
                        domain=t["domain"],
                        position=pos,
                        length=len(source),
                        is_forced=t.get("is_forced", False),
                        forbidden_terms=list(t.get("forbidden_terms", [])),
                        synonyms=list(t.get("synonyms", [])),
                    )
                )

            start = pos + 1

    return hits


def _levenshtein(s1: str, s2: str) -> int:
    """Compute the standard Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def _fts_query(query: str) -> list[str]:
    """Run an FTS5 MATCH query and return matching term_ids."""
    if not db.fts_conn:
        return []
    tokens = query.strip().split()
    if not tokens:
        return []
    fts_expr = " OR ".join(f'"{tok}"' for tok in tokens)
    try:
        return db.fts_search(fts_expr)
    except Exception:
        return []


def _matches_filters(
    term: dict,
    source_lang: str | None,
    target_lang: str | None,
    domain: str | None,
    status: str | None,
) -> bool:
    """Check whether a term matches all provided filter criteria."""
    if source_lang and term.get("source_lang") != source_lang:
        return False
    if target_lang and term.get("target_lang") != target_lang:
        return False
    if domain and term.get("domain") != domain:
        return False
    if status and term.get("status") != status:
        return False
    return True


def _pinyin_match(query_lower: str, text: str) -> bool:
    """Check if the lowercased query matches the pinyin representation of the text."""
    pinyin_list = lazy_pinyin(text)
    full_pinyin = "".join(pinyin_list).lower()
    if query_lower in full_pinyin:
        return True
    joined = "".join(pinyin_list).lower()
    return query_lower in joined


def _is_subsumed(start: int, end: int, covered: list[tuple[int, int]]) -> bool:
    """Check if a span [start, end) is fully covered by an existing longer span."""
    for cs, ce in covered:
        if cs <= start and ce >= end:
            return True
    return False
