import json
from datetime import date
from pathlib import Path

from pipeline.connectors.base import load_source_domains
from pipeline.connectors.datacommons_feed import DataCommonsFeed, parse_feed, parse_item

FIXTURE = Path(__file__).parent / "fixtures" / "datacommons_sample.json"


def test_keeps_only_sources_from_referential():
    reviews = DataCommonsFeed(feed_path=FIXTURE).fetch(date(2000, 1, 1))
    assert {r.source_id for r in reviews} == {"les_surligneurs", "les_decodeurs", "afp_factuel"}
    assert all(r.connector == "datacommons_feed" for r in reviews)


def test_fields_are_kept_verbatim():
    for r in DataCommonsFeed(feed_path=FIXTURE).fetch(date(2000, 1, 1)):
        assert r.url.startswith("https://")
        assert r.rating_original  # libellé d'origine, jamais réécrit
        assert r.review_date and r.claimant


def test_since_filters_on_review_date():
    feed = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert parse_feed(feed, load_source_domains(), date(2100, 1, 1)) == []


def test_parse_item_handles_missing_fields():
    review = parse_item({"url": "https://lessurligneurs.eu/x/", "itemReviewed": {"author": "Jean Dupont"}}, "les_surligneurs")
    assert review is not None
    assert review.claimant == "Jean Dupont"
    assert review.rating_original is None and review.claim_date is None
    assert parse_item({"claimReviewed": "sans url"}, "les_surligneurs") is None
