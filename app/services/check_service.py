from __future__ import annotations

from app.database import db
from app.models import CheckRequest, CheckResponse, ConflictItem, LookupHit
from app.services.lookup_service import lookup_text


def check_text(request: CheckRequest) -> CheckResponse:
    """Run consistency check on the text and return all conflicts found."""
    lookup_req = _to_lookup_request(request)
    hits = lookup_text(lookup_req)

    conflicts: list[ConflictItem] = []
    for hit in hits:
        term = db.terms.get(hit.term_id)
        if not term:
            continue

        _check_forbidden(request.text, hit, conflicts)
        _check_missing_translation(request.text, hit, conflicts)
        _check_inconsistent(request.text, hit, conflicts)

    return CheckResponse(
        conflicts=conflicts,
        total_terms_checked=len(hits),
    )


def _to_lookup_request(request: CheckRequest):
    """Convert a CheckRequest into a LookupRequest for reuse."""
    from app.models import LookupRequest

    domains = [request.domain] if request.domain else None
    return LookupRequest(
        text=request.text,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        domains=domains,
    )


def _find_in_text(text: str, needle: str, case_sensitive: bool) -> bool:
    """Check if needle appears in text, respecting case sensitivity."""
    if case_sensitive:
        return needle in text
    return needle.lower() in text.lower()


def _check_forbidden(text: str, hit: LookupHit, conflicts: list[ConflictItem]) -> None:
    """Detect forbidden terms appearing in the text."""
    for forbidden in hit.forbidden_terms:
        if _find_in_text(text, forbidden, False):
            conflicts.append(
                ConflictItem(
                    term_id=hit.term_id,
                    source_term=hit.source_term,
                    expected_target=hit.target_term,
                    actual_in_text=forbidden,
                    conflict_type="forbidden_translation",
                    details=f"Forbidden term '{forbidden}' found for '{hit.source_term}'; use '{hit.target_term}' instead",
                )
            )


def _check_missing_translation(text: str, hit: LookupHit, conflicts: list[ConflictItem]) -> None:
    """Detect forced terms where the source appears but the target translation is missing."""
    if not hit.is_forced:
        return

    term = db.terms.get(hit.term_id)
    if not term:
        return

    source_present = _find_in_text(text, hit.source_term, term.get("case_sensitive", False))
    target_present = _find_in_text(text, hit.target_term, False)

    if source_present and not target_present:
        conflicts.append(
            ConflictItem(
                term_id=hit.term_id,
                source_term=hit.source_term,
                expected_target=hit.target_term,
                conflict_type="missing_translation",
                details=f"Forced term '{hit.source_term}' found but required translation '{hit.target_term}' is missing",
            )
        )


def _check_inconsistent(text: str, hit: LookupHit, conflicts: list[ConflictItem]) -> None:
    """Detect source terms whose in-text translation differs from the expected target and is not a known synonym."""
    term = db.terms.get(hit.term_id)
    if not term:
        return

    source = hit.source_term
    target = hit.target_term
    synonyms = hit.synonyms
    case_sensitive = term.get("case_sensitive", False)

    if not _find_in_text(text, source, case_sensitive):
        return

    if _find_in_text(text, target, False):
        return

    found_synonym = None
    for syn in synonyms:
        if _find_in_text(text, syn, False):
            found_synonym = syn
            break

    if found_synonym:
        return

    actual = _extract_actual_translation(text, hit, case_sensitive)
    if actual:
        conflicts.append(
            ConflictItem(
                term_id=hit.term_id,
                source_term=source,
                expected_target=target,
                actual_in_text=actual,
                conflict_type="inconsistent_translation",
                details=f"Term '{source}' should translate to '{target}' but '{actual}' was found instead",
            )
        )


def _extract_actual_translation(text: str, hit: LookupHit, case_sensitive: bool) -> str | None:
    """Try to find a candidate translation near the source term occurrence in the text."""
    source = hit.source_term
    search_text = text if case_sensitive else text.lower()
    search_source = source if case_sensitive else source.lower()

    pos = search_text.find(search_source)
    if pos == -1:
        return None

    window = 30
    after_start = pos + len(source)
    after_end = min(after_start + window, len(text))
    before_start = max(pos - window, 0)

    snippet_after = text[after_start:after_end]
    snippet_before = text[before_start:pos]

    for candidate in _collect_candidates(snippet_after, snippet_before, hit):
        return candidate

    return None


def _collect_candidates(snippet_after: str, snippet_before: str, hit: LookupHit) -> list[str]:
    """Collect candidate translations from surrounding context that are neither the target nor synonyms."""
    target = hit.target_term
    synonyms = set(hit.synonyms)
    all_known = {target} | synonyms

    candidates: list[str] = []
    for known in all_known:
        if known in snippet_after or known in snippet_before:
            candidates.append(known)

    non_target = [c for c in candidates if c != target and c not in synonyms]
    if non_target:
        return non_target

    return []
