"""Flux ClaimReview quotidien de Data Commons (CC BY).

Le flux complet (~200 Mo, ~95 000 éléments, toutes langues) est téléchargé puis filtré :
seules les vérifications publiées par une source listée dans sources.csv sont gardées.
"""

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from pipeline.connectors.base import Connector, RawReview, domain_of, load_source_domains

FEED_URL = "https://storage.googleapis.com/datacommons-feeds/claimreview/latest/data.json"


def _name(obj: Any) -> str | None:
    if isinstance(obj, dict):
        return (obj.get("name") or "").strip() or None
    if isinstance(obj, str):
        return obj.strip() or None
    return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def parse_item(item: dict[str, Any], source_id: str) -> RawReview | None:
    url = _str(item.get("url"))
    if not url:
        return None
    reviewed = item.get("itemReviewed") or {}
    rating = item.get("reviewRating") or {}
    appearances = reviewed.get("appearance") or []
    if isinstance(appearances, dict):
        appearances = [appearances]
    return RawReview(
        url=url,
        source_id=source_id,
        connector=DataCommonsFeed.name,
        claim_text=_str(item.get("claimReviewed")),
        claimant=_name(reviewed.get("author")),
        claim_date=_str(reviewed.get("datePublished")),
        review_date=_str(item.get("datePublished")),
        rating_original=_str(rating.get("alternateName")),
        rating_value=_str(rating.get("ratingValue")),
        best_rating=_str(rating.get("bestRating")),
        worst_rating=_str(rating.get("worstRating")),
        title=_str(item.get("name")),
        lang=_str(item.get("inLanguage")),
        appearance_urls=tuple(u for a in appearances if (u := _str(a.get("url")))),
    )


def parse_feed(feed: dict[str, Any], source_domains: dict[str, str], since: date) -> list[RawReview]:
    reviews: list[RawReview] = []
    for element in feed.get("dataFeedElement") or []:
        for item in element.get("item") or []:
            source_id = source_domains.get(domain_of(item.get("url") or ""))
            if source_id is None:
                continue
            review = parse_item(item, source_id)
            # Sans date de vérification, on garde : la normalisation signalera la date manquante.
            if review and (review.review_date is None or review.review_date[:10] >= since.isoformat()):
                reviews.append(review)
    return reviews


class DataCommonsFeed(Connector):
    name = "datacommons_feed"

    def __init__(self, feed_path: Path | None = None, source_domains: dict[str, str] | None = None):
        self.feed_path = feed_path  # fichier local (tests, rejeu) au lieu du téléchargement
        self.source_domains = source_domains if source_domains is not None else load_source_domains()

    def _load(self) -> dict[str, Any]:
        if self.feed_path:
            return json.loads(self.feed_path.read_text(encoding="utf-8"))
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            response = client.get(FEED_URL)
            response.raise_for_status()
            return response.json()

    def fetch(self, since: date) -> list[RawReview]:
        return parse_feed(self._load(), self.source_domains, since)


def main(argv: Iterable[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Aperçu du connecteur Data Commons")
    parser.add_argument("--since", type=date.fromisoformat, default=date(2000, 1, 1))
    parser.add_argument("--feed", type=Path)
    args = parser.parse_args(argv)
    reviews = DataCommonsFeed(feed_path=args.feed).fetch(args.since)
    print(f"{len(reviews)} vérifications retenues")
    for r in sorted(reviews, key=lambda r: r.review_date or "", reverse=True)[:5]:
        print(f"- {r.review_date} · {r.source_id} · {r.claimant} · {r.rating_original!r}\n  {r.url}")


if __name__ == "__main__":
    main()
