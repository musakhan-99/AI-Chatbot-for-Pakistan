from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "official_sources.json"

with _DATA_PATH.open("r", encoding="utf-8") as f:
    OFFICIAL_SOURCES: list[dict[str, Any]] = json.load(f)


def official_sources_for_query(query: str, limit: int = 4) -> list[dict[str, str]]:
    text = query.casefold()
    scored: list[tuple[int, dict[str, Any]]] = []

    for item in OFFICIAL_SOURCES:
        score = sum(2 if " " in kw else 1 for kw in item["keywords"] if kw.casefold() in text)
        if score:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "title": item["name"],
            "url": item["url"],
            "source_type": "official",
            "authority": item["authority"],
            "language": "en",
        }
        for _, item in scored[:limit]
    ]


def topic_warnings(query: str) -> list[str]:
    text = query.casefold()
    warnings: list[str] = []

    live_terms = [
        "today", "latest", "current", "right now", "price", "rate", "weather",
        "flight", "road closed", "admission open", "deadline", "news", "result",
        "aaj", "abhi", "latest", "rate", "qeemat", "mausam",
    ]
    legal_tax_terms = [
        "law", "legal", "court", "tax", "fbr", "ntn", "visa", "passport",
        "cnic", "nicop", "company registration", "secp", "license", "licence",
        "قانون", "ٹیکس", "ویزا", "پاسپورٹ", "شناختی کارڈ",
    ]
    medical_terms = [
        "medicine", "medical", "doctor", "dose", "symptom", "treatment", "hospital",
        "دوا", "علاج", "بیماری",
    ]

    if any(term in text for term in live_terms):
        warnings.append(
            "This question may depend on live or rapidly changing information. Verify time-sensitive details with the linked official source."
        )
    if any(term in text for term in legal_tax_terms):
        warnings.append(
            "Government, legal, tax, identity, and visa procedures can change. Treat the official authority as the final source."
        )
    if any(term in text for term in medical_terms):
        warnings.append(
            "Health information is general guidance only and is not a diagnosis or substitute for a qualified clinician."
        )

    return warnings
