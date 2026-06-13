from __future__ import annotations

from app.database import db
from app.models import new_id, now
from app.services import notification_service, statistics_service


def check_document_usage(text: str, source_lang: str, document_id: str) -> list[dict]:
    """Find terms whose source_term appears in the text, notify their creators, and record usage."""
    found = []
    for term in db.terms.values():
        if term.get("source_lang") != source_lang:
            continue
        source = term.get("source_term", "")
        if not source:
            continue
        case_sensitive = term.get("case_sensitive", False)
        search_text = text if case_sensitive else text.lower()
        search_source = source if case_sensitive else source.lower()
        if search_source in search_text:
            found.append(term)
            creator_id = term.get("created_by", "")
            if creator_id:
                notification_service.create_notification(
                    user_id=creator_id,
                    term_id=term["term_id"],
                    type="document_usage",
                    message=f"你的术语在 {document_id} 文档被使用",
                )
            is_forced = term.get("is_forced", False)
            statistics_service.record_term_usage(
                term_id=term["term_id"],
                document_id=document_id,
                was_adopted=is_forced,
            )
    return found


def on_term_status_change(term_id: str, from_status: str, to_status: str) -> None:
    """Trigger notifications for status changes to subscribers of the term's domain."""
    notification_service.notify_status_change(term_id, from_status, to_status)
