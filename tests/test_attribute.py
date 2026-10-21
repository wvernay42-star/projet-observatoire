import pytest

from pipeline.attribute import Attribution, Referential

PERSONS = [
    {"id": "Q1", "full_name": "Nicolas Dupont-Aignan", "aliases": '["NDA"]'},
    {"id": "Q2", "full_name": "Marine Le Pen", "aliases": "[]"},
    {"id": "Q3", "full_name": "Jean Martin", "aliases": "[]"},
    {"id": "Q4", "full_name": "Jean Martin", "aliases": "[]"},  # homonyme
    {"id": "Q5", "full_name": "Éric Ciotti", "aliases": '["Eric Ciotti"]'},
]
AFFILIATIONS = [
    {"person_id": "Q1", "party_id": "DLF", "start_date": "2008-11-23", "end_date": "", "source_url": ""},
    {"person_id": "Q5", "party_id": "LR", "start_date": "2015-05-30", "end_date": "2024-07-01", "source_url": ""},
    {"person_id": "Q5", "party_id": "UDR", "start_date": "2024-07-02", "end_date": "", "source_url": ""},
    {"person_id": "Q2", "party_id": "FN", "start_date": "", "end_date": "", "source_url": ""},
    {"person_id": "Q2", "party_id": "RN", "start_date": "", "end_date": "", "source_url": ""},
]


@pytest.fixture
def ref():
    return Referential(PERSONS, AFFILIATIONS)


@pytest.mark.parametrize("claimant", ["Nicolas Dupont-Aignan", "nicolas dupont aignan", "NDA", "Eric Ciotti"])
def test_exact_unique_match_is_auto_sure(ref, claimant):
    assert ref.attribute(claimant).status == "auto_sure"


def test_homonyms_go_to_review(ref):
    assert ref.attribute("Jean Martin") == Attribution("to_review", candidates=("Q3", "Q4"), reason="homonymes")


@pytest.mark.parametrize("claimant", ["Marine Le Pen sur TF1", "Marine Le Pen, présidente du RN", "la députée Marine Le Pen"])
def test_name_with_context_goes_to_review(ref, claimant):
    result = ref.attribute(claimant)
    assert (result.status, result.candidates) == ("to_review", ("Q2",))


@pytest.mark.parametrize("claimant", ["Des internautes sur les réseaux sociaux", "Une internaute sur Facebook",
                                      "Plusieurs sites dont Wikistrike", "un élu RN", "Anti-Macron / Facebook"])
def test_vague_labels_are_never_attributed(ref, claimant):
    assert ref.attribute(claimant).status == "rejected"


def test_surname_only_goes_to_review(ref):
    assert ref.attribute("Ciotti") == Attribution("to_review", candidates=("Q5",), reason="nom seul")


def test_unknown_person_is_rejected(ref):
    assert ref.attribute("Jean-Pierre Pernault") == Attribution("rejected", reason="hors référentiel")
    assert ref.attribute(None).status == "rejected"


def test_party_at_date(ref):
    assert ref.party_at("Q5", "2020-09-15").party_id == "LR"
    assert ref.party_at("Q5", "2025-01-10").party_id == "UDR"
    assert ref.party_at("Q1", "2019-03-06").party_id == "DLF"


def test_party_unknown_or_ambiguous_is_never_guessed(ref):
    assert ref.party_at("Q2", "2019-05-10").status == "ambiguous"  # deux affiliations sans dates
    assert ref.party_at("Q3", "2019-05-10").status == "none"
    assert ref.party_at("Q1", None).status == "no_date"


def test_partial_dates_compare_on_their_precision(ref):
    assert ref.party_at("Q5", "2024").status == "ambiguous"  # année du changement de parti
    assert ref.party_at("Q5", "2023").party_id == "LR"


def test_year_precision_dates_do_not_invent_a_day():
    ref = Referential(PERSONS, [
        {"person_id": "Q3", "party_id": "A", "start_date": "2010", "end_date": "2015", "source_url": ""},
        {"person_id": "Q3", "party_id": "B", "start_date": "2015", "end_date": "", "source_url": ""},
    ])
    assert ref.party_at("Q3", "2012-03-01").party_id == "A"
    assert ref.party_at("Q3", "2015-06-01").status == "ambiguous"  # changement dans l'année
    assert ref.party_at("Q3", "2016-01-01").party_id == "B"


def test_wikidata_date_precision():
    from pipeline.referential import day
    assert day("2015-01-01T00:00:00Z", "9") == "2015"
    assert day("2015-06-01T00:00:00Z", "10") == "2015-06"
    assert day("2015-06-21T00:00:00Z", "11") == "2015-06-21"
    assert day("1990-01-01T00:00:00Z", "8") == ""
    assert day(None) == ""
