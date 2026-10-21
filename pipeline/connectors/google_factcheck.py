"""API Google Fact Check Tools (claims:search), interrogée éditeur par éditeur.

Les rédactions déclarent leurs vérifications à Google (outil Fact Check Markup) : l'API les
remonte même quand la page de l'article ne porte pas de balisage ClaimReview.

La clé API est ajoutée par l'environnement cloud (en-tête X-goog-api-key) ; à défaut, elle est
lue dans GOOGLE_FACTCHECK_API_KEY et passée en paramètre.
"""

import os
import time
from collections.abc import Iterator
from datetime import date
from typing import Any

import httpx

from pipeline.connectors.base import Connector, RawReview, domain_of, load_source_domains

API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
PAGE_SIZE = 100
PAUSE_SECONDS = 1.0


def parse_claim(claim: dict[str, Any], source_domains: dict[str, str]) -> list[RawReview]:
    """Une affirmation -> ses vérifications publiées par une source du référentiel."""
    reviews = []
    for review in claim.get("claimReview") or []:
        url = (review.get("url") or "").strip()
        site = (review.get("publisher") or {}).get("site") or url
        source_id = source_domains.get(domain_of(site if "//" in site else f"https://{site}"))
        if not url or source_id is None:
            continue
        reviews.append(RawReview(
            url=url,
            source_id=source_id,
            connector=GoogleFactCheck.name,
            claim_text=(claim.get("text") or "").strip() or None,
            claimant=(claim.get("claimant") or "").strip() or None,
            claim_date=claim.get("claimDate"),
            review_date=review.get("reviewDate"),
            rating_original=(review.get("textualRating") or "").strip() or None,
            title=(review.get("title") or "").strip() or None,
            lang=review.get("languageCode"),
        ))
    return reviews


class GoogleFactCheck(Connector):
    name = "google_factcheck"

    def __init__(self, client: httpx.Client | None = None, source_domains: dict[str, str] | None = None,
                 today: date | None = None):
        self.client = client or httpx.Client(timeout=60)
        self.source_domains = source_domains if source_domains is not None else load_source_domains()
        self.today = today or date.today()
        self.api_key = os.environ.get("GOOGLE_FACTCHECK_API_KEY") or None

    def _pages(self, site: str, max_age_days: int) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"reviewPublisherSiteFilter": site, "maxAgeDays": max_age_days,
                                  "pageSize": PAGE_SIZE}
        if self.api_key:
            params["key"] = self.api_key
        while True:
            response = self.client.get(API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            yield data
            token = data.get("nextPageToken")
            if not token:
                return
            params["pageToken"] = token
            time.sleep(PAUSE_SECONDS)

    def fetch(self, since: date) -> list[RawReview]:
        max_age_days = max(1, (self.today - since).days + 1)
        seen: dict[str, RawReview] = {}
        for site in sorted(self.source_domains):
            for page in self._pages(site, max_age_days):
                for claim in page.get("claims") or []:
                    for review in parse_claim(claim, self.source_domains):
                        if (review.review_date or "")[:10] >= since.isoformat():
                            seen.setdefault(review.url, review)
        return list(seen.values())


def main() -> None:
    import argparse
    from collections import Counter
    from datetime import timedelta

    parser = argparse.ArgumentParser(description="Aperçu du connecteur Google Fact Check")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    reviews = GoogleFactCheck().fetch(date.today() - timedelta(days=args.days))
    print(f"{len(reviews)} vérifications sur {args.days} jours : {dict(Counter(r.source_id for r in reviews))}")
    for r in sorted(reviews, key=lambda r: r.review_date or "", reverse=True)[:5]:
        print(f"- {r.review_date} · {r.source_id} · {r.claimant} · {r.rating_original!r}\n  {r.url}")


if __name__ == "__main__":
    main()
