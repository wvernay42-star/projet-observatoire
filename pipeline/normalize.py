"""Conversion d'une vérification brute (RawReview) vers une ligne de la table reviews."""

import hashlib
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pipeline.connectors.base import RawReview
from pipeline.ratings import convert

PARIS = ZoneInfo("Europe/Paris")


def review_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def parse_date(value: str | None) -> tuple[str | None, str]:
    """Date brute -> (date ISO à sa précision, précision 'day' | 'month' | 'unknown').

    Un horodatage UTC est ramené à la date de Paris (« 2026-10-12T22:00:00Z » = 13 octobre).
    """
    if not value:
        return None, "unknown"
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", value):
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value[:10], "day"
        if moment.tzinfo is not None:
            moment = moment.astimezone(PARIS)
        return moment.date().isoformat(), "day"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value, "day"
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value, "month"
    return None, "unknown"


def normalize(raw: RawReview, rating_map: dict[tuple[str, str], str], ingested_at: str) -> dict[str, Any]:
    rating = convert(raw, rating_map)
    review_date, _ = parse_date(raw.review_date)
    return {
        "id": review_id(raw.url),
        "source_id": raw.source_id,
        "url": raw.url,
        "title": raw.title,
        "rating_original": raw.rating_original,
        "rating_normalized": rating.normalized,
        "rating_method": rating.method,
        "review_date": review_date,
        "ingested_at": ingested_at,
        "lang": raw.lang,
        "connector": raw.connector,
        "claimant": raw.claimant,
        "claim_text": raw.claim_text,
        "claim_date_raw": raw.claim_date,
    }


def claim_dates(review: dict[str, Any]) -> tuple[str | None, str, int]:
    """Date de la déclaration : (date, précision, date_is_fallback), repli sur la vérification."""
    claim_date, precision = parse_date(review.get("claim_date_raw"))
    if claim_date:
        return claim_date, precision, 0
    return review.get("review_date"), "day" if review.get("review_date") else "unknown", 1
