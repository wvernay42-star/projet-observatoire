import csv
from pathlib import Path

import pytest

from pipeline.connectors.base import SEEDS_DIR, RawReview
from pipeline.ratings import LEVELS, Rating, convert, label_key, load_rating_map, unmapped_labels


def review(label, source="les_decodeurs", value=None, best=None, worst=None):
    return RawReview(url="https://x/1", source_id=source, connector="test", claim_text=None,
                     claimant=None, claim_date=None, review_date=None, rating_original=label,
                     rating_value=value, best_rating=best, worst_rating=worst)


@pytest.fixture(scope="module")
def mapping():
    return load_rating_map()


def test_label_key_ignores_case_accents_and_apostrophes():
    assert label_key("C’EST PLUS COMPLIQUÉ ") == label_key("c'est plus complique")
    assert label_key("FAUX.") == "faux"


@pytest.mark.parametrize("label", ["FAUX", "Faux", "faux", "C'EST FAUX"])
def test_exact_labels_map_to_false(mapping, label):
    assert convert(review(label), mapping) == Rating("false", "map")


def test_mapping_is_per_source(mapping):
    assert convert(review("Faux", source="source_inconnue"), mapping).method == "pending"


def test_unknown_label_is_unrated_and_pending(mapping):
    assert convert(review("Très exagéré"), mapping) == Rating("unrated", "pending")
    assert convert(review(None), mapping) == Rating("unrated", "pending")


def test_numeric_rule_is_off_by_default(mapping):
    # Les Décodeurs : 0/2 et 0/5 pour FAUX, mais aussi 1/2 : aucune échelle fiable.
    assert convert(review("?", value="0", best="2", worst="0"), mapping).method == "pending"


def test_unmapped_labels_counts(mapping):
    counts = unmapped_labels([review("DOUTEUX"), review("DOUTEUX"), review("Vrai")], mapping)
    assert counts == {("les_decodeurs", "DOUTEUX"): 2}


def test_seed_file_is_valid():
    with (SEEDS_DIR / "rating_map.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows and all(r["rating_normalized"] in LEVELS for r in rows)
    keys = [(r["source_id"], label_key(r["rating_original"])) for r in rows]
    assert len(keys) == len(set(keys)), "doublon dans rating_map.csv"


def test_proposals_use_known_levels():
    path = Path(__file__).parents[1] / "data" / "review_queue" / "rating_proposals.csv"
    with path.open(encoding="utf-8") as f:
        assert all(r["proposed_normalized"] in LEVELS for r in csv.DictReader(f))
