from __future__ import annotations

import httpx

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from app.database import db
from app.models import new_id, now


def suggest_terms(
    text: str,
    source_lang: str,
    target_lang: str,
    domain: str | None = None,
) -> list[dict]:
    """Call an OpenAI-compatible API to identify potential terms from the given text."""
    if not OPENAI_API_KEY:
        return []

    prompt = (
        f"Identify potential terminology terms from the following text written in {source_lang}. "
        f"For each term, suggest a {target_lang} translation, a reason, and a confidence score (0-1)."
    )
    if domain:
        prompt += f" Focus on the '{domain}' domain."

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    db.recommendation_stats["suggested"] += 1

    recommendations = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            recommendations.append({
                "suggested_term": parts[0],
                "reason": parts[1],
                "confidence": float(parts[2]),
            })
    return recommendations


def adopt_recommendation(term_id: str) -> None:
    """Mark a recommendation as adopted and increment the adopted counter in recommendation stats."""
    db.recommendation_stats["adopted"] += 1


def get_recommendation_stats() -> dict:
    """Return recommendation statistics including suggested, adopted counts and adoption rate."""
    suggested = db.recommendation_stats.get("suggested", 0)
    adopted = db.recommendation_stats.get("adopted", 0)
    adoption_rate = adopted / suggested if suggested > 0 else 0.0
    return {
        "suggested": suggested,
        "adopted": adopted,
        "adoption_rate": adoption_rate,
    }
