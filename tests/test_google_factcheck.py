import json
from datetime import date
from pathlib import Path

import httpx

from pipeline.connectors.base import load_source_domains
from pipeline.connectors.google_factcheck import GoogleFactCheck, parse_claim

FIXTURES = Path(__file__).parent / "fixtures" / "google_factcheck"
DOMAINS = load_source_domains()


def fake_api(pages_by_site):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        pages = pages_by_site.get(request.url.params["reviewPublisherSiteFilter"], [{}])
        index = int(request.url.params.get("pageToken", 0))
        return httpx.Response(200, json=pages[index])

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_keeps_only_reviews_from_referential_sources():
    afp = load("afp")
    reviews = [r for c in afp["claims"] for r in parse_claim(c, DOMAINS)]
    assert reviews and {r.source_id for r in reviews} == {"afp_factuel", "poligraph_fr"}  # DE FACTO écarté
    assert all(r.rating_original and r.url.startswith("https://") for r in reviews)


def test_fetch_queries_each_publisher_and_follows_pages():
    franceinfo = load("franceinfo")
    page2 = {"claims": franceinfo["claims"][3:]}
    page1 = {"claims": franceinfo["claims"][:3], "nextPageToken": "1"}
    client, calls = fake_api({"franceinfo.fr": [page1, page2]})
    connector = GoogleFactCheck(client=client, source_domains=DOMAINS, today=date(2026, 10, 21))
    connector.api_key = None
    reviews = connector.fetch(date(2000, 1, 1))
    assert {c["reviewPublisherSiteFilter"] for c in calls} == set(DOMAINS)
    assert len(reviews) == len(franceinfo["claims"])
    assert all(r.source_id == "franceinfo_vraioufake" and r.connector == "google_factcheck" for r in reviews)


def test_fetch_filters_on_review_date_and_dedupes_urls():
    claims = load("franceinfo")["claims"]
    client, _ = fake_api({"franceinfo.fr": [{"claims": claims + claims}]})
    reviews = GoogleFactCheck(client=client, source_domains=DOMAINS, today=date(2026, 10, 21)).fetch(date(2000, 1, 1))
    assert len(reviews) == len(claims)
    client, _ = fake_api({"franceinfo.fr": [{"claims": claims}]})
    assert GoogleFactCheck(client=client, source_domains=DOMAINS, today=date(2026, 10, 21)).fetch(date(2100, 1, 1)) == []


def test_claimant_and_dates_are_kept_raw():
    claim = {"text": "x", "claimant": " Marine Le Pen ", "claimDate": "2026-10-01T00:00:00Z",
             "claimReview": [{"publisher": {"site": "tf1info.fr"}, "url": "https://www.tf1info.fr/a.html",
                              "reviewDate": "2026-10-02T10:00:00Z", "textualRating": "Plutôt faux"}]}
    (review,) = parse_claim(claim, DOMAINS)
    assert (review.claimant, review.claim_date, review.source_id) == ("Marine Le Pen", "2026-10-01T00:00:00Z", "tf1info_verificateurs")
