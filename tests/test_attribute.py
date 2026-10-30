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
                                      "Plusieurs sites dont Wikistrike", "un élu RN", "Anti-Macron / Facebook",
                                      "Sources multiples", "Multiple", "X", "-"])
def test_vague_labels_are_never_attributed(ref, claimant):
    assert ref.attribute(claimant).status == "rejected"


@pytest.mark.parametrize("claimant", ["Le député LFI Marine Le Pen", "L'eurodéputée du RN Marine Le Pen",
                                      "Le premier secrétaire du PS, Marine Le Pen", "La tête de liste RN Marine Le Pen"])
def test_title_and_party_before_the_name_go_to_review(ref, claimant):
    result = ref.attribute(claimant)
    assert (result.status, result.candidates) == ("to_review", ("Q2",))


def test_several_people_are_all_proposed(ref):
    assert ref.attribute("Marine Le Pen et Eric Ciotti") == Attribution(
        "to_review", candidates=("Q2", "Q5"), reason="plusieurs personnes")


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
    assert ref.party_at("Q2", "2019-05-10").status == "undated"  # affiliations sans dates : à valider
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


def test_undated_affiliation_is_never_used_automatically():
    ref = Referential(PERSONS, [
        {"person_id": "Q3", "party_id": "PS", "start_date": "", "end_date": "", "source_url": ""},
    ])
    result = ref.party_at("Q3", "2020-09-12")
    assert (result.party_id, result.status, result.candidates) == (None, "undated", ("PS",))


def test_manual_affiliation_wins_on_its_date_only():
    manual = [{"person_id": "Q2", "party_id": "RN", "start_date": "2026-09-13", "end_date": "2026-09-13", "source_url": ""}]
    ref = Referential(PERSONS, AFFILIATIONS, manual)
    assert ref.party_at("Q2", "2026-09-13").party_id == "RN"
    assert ref.party_at("Q2", "2019-05-10").status == "undated"  # ailleurs, Wikidata reste la règle


def test_manual_no_party_is_a_decision_not_a_gap():
    manual = [{"person_id": "Q3", "party_id": "none", "start_date": "2026-10-15", "end_date": "2026-10-15", "source_url": ""}]
    assert Referential(PERSONS, [], manual).party_at("Q3", "2026-10-15").status == "no_party"


def test_affiliation_outside_party_lifetime_is_ignored():
    parties = [{"id": "UMP", "inception": "2002-11-17", "dissolved": "2015-05-30"},
               {"id": "LR", "inception": "2015-05-30", "dissolved": ""}]
    affiliations = [{"person_id": "Q3", "party_id": "UMP", "start_date": "", "end_date": "", "source_url": ""},
                    {"person_id": "Q3", "party_id": "LR", "start_date": "2015-05-30", "end_date": "", "source_url": ""}]
    manual = [{"person_id": "Q3", "party_id": "UMP", "start_date": "2024-11-15", "end_date": "2024-11-15", "source_url": ""}]
    ref = Referential(PERSONS, affiliations, manual, parties)
    assert ref.party_at("Q3", "2024-11-15").party_id == "LR"  # UMP n'existait plus : validation ignorée
    assert ref.party_at("Q3", "2010-01-01").status == "undated"  # UMP possible, mais sans date
    assert not ref.party_existed("LR", "2012-03-01")


def test_candidates_2027_join_the_referential(tmp_path):
    import csv
    def write(name, header, rows):
        with (tmp_path / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
    write("persons.csv", ["id", "full_name", "aliases", "country", "public_role"], [["Q1", "Marine Le Pen", "[]", "FR", "député"]])
    write("affiliations.csv", ["person_id", "party_id", "start_date", "end_date", "source_url"], [])
    write("parties.csv", ["id", "name", "short_name", "country", "parlgov_id", "inception", "dissolved"], [])
    write("candidates_2027.csv", ["votona_id", "name", "votona_party", "status", "person_id", "person_match", "party_id", "votona_url"],
          [["lepen", "Marine Le Pen", "RN", "déclaré ou pressenti", "Q1", "sûr", "", ""],
           ["arthaud", "Nathalie Arthaud", "Lutte Ouvrière", "déclaré ou pressenti", "Q439490", "sûr", "", ""],
           ["mathieu", "Benoît Mathieu", "Sans étiquette", "déclaré ou pressenti", "", "aucune fiche Wikidata", "", ""]])
    ref = Referential.load(tmp_path)
    assert ref.attribute("Nathalie Arthaud").person_id == "Q439490"
    assert ref.attribute("Benoît Mathieu").person_id == "votona:mathieu"
    assert set(ref.candidates) == {"Q1", "Q439490", "votona:mathieu"}
