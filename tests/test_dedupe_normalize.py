from pipeline.dedupe import group_reviews, majority_verdict
from pipeline.normalize import claim_dates, parse_date


def test_parse_date_converts_utc_to_paris_day():
    assert parse_date("2026-10-12T22:00:00Z") == ("2026-10-13", "day")
    assert parse_date("2026-10-12T10:00:00Z") == ("2026-10-12", "day")
    assert parse_date("2019-10-20") == ("2019-10-20", "day")
    assert parse_date("2019-10") == ("2019-10", "month")
    assert parse_date(None) == (None, "unknown")
    assert parse_date("n'importe quoi") == (None, "unknown")


def test_claim_date_falls_back_on_review_date():
    assert claim_dates({"claim_date_raw": "2026-09-13", "review_date": "2026-09-15"}) == ("2026-09-13", "day", 0)
    assert claim_dates({"claim_date_raw": None, "review_date": "2026-09-15"}) == ("2026-09-15", "day", 1)


def test_same_claim_by_two_outlets_is_merged():
    groups = group_reviews([
        ("r1", "Q12927", "2026-09-13", "Marine Le Pen affirme que la dette a doublé depuis 2017"),
        ("r2", "Q12927", "2026-09-14", "La dette a-t-elle doublé depuis 2017, comme l'affirme Marine Le Pen ?"),
    ])
    assert [g.review_ids for g in groups] == [["r1", "r2"]]


def test_different_people_dates_or_texts_are_not_merged():
    groups = group_reviews([
        ("r1", "Q1", "2026-09-13", "La dette a doublé depuis 2017"),
        ("r2", "Q2", "2026-09-13", "La dette a doublé depuis 2017"),        # autre personne
        ("r3", "Q1", "2026-09-30", "La dette a doublé depuis 2017"),        # trop loin dans le temps
        ("r4", "Q1", "2026-09-14", "Les retraites baissent de 25 %"),       # autre affirmation
        ("r5", None, "2026-09-13", "La dette a doublé depuis 2017"),        # non attribuée
        ("r6", None, "2026-09-13", "La dette a doublé depuis 2017"),
    ])
    assert len(groups) == 6


def test_majority_verdict_and_tie():
    assert majority_verdict(["false", "false", "mostly_false"]) == "false"
    assert majority_verdict(["false", "mostly_false"]) == "unrated"
    assert majority_verdict(["true"]) == "true"


def test_rephrased_claim_with_same_figures_is_merged():
    groups = group_reviews([
        ("r1", "Q12927", "2026-09-13", "\"Aujourd'hui, 70% des Français sont éligibles au parc social et seulement 11% en bénéficient\""),
        ("r2", "Q12927", "2026-09-13", "Les Français seulement 11% à vivre dans un logement social, alors que 70% y sont éligibles"),
        ("r3", "Q12927", "2026-09-14", "Le chômage des jeunes atteint 18% contre 7% pour l'ensemble des actifs"),  # autre affirmation
    ])
    assert [g.review_ids for g in groups] == [["r1", "r2"], ["r3"]]
