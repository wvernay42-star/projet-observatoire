from pipeline.export import party_name_at

HISTORY = [
    {"name": "En marche !", "short_name": "EM", "start_date": "2016-04-06", "end_date": "2017-05-08"},
    {"name": "La République en marche !", "short_name": "LREM", "start_date": "2017-05-08", "end_date": "2022-09-22"},
    {"name": "Renaissance", "short_name": "RE", "start_date": "2022-09-22", "end_date": ""},
]
PARTY = {"name": "Renaissance", "short_name": "RE"}


def test_party_name_is_the_one_in_force_at_the_claim_date():
    assert party_name_at(PARTY, HISTORY, "2016-10-01") == ("En marche !", "EM")
    assert party_name_at(PARTY, HISTORY, "2020-10-02") == ("La République en marche !", "LREM")
    assert party_name_at(PARTY, HISTORY, "2022-09-22") == ("Renaissance", "RE")
    assert party_name_at(PARTY, HISTORY, "2025-01-01") == ("Renaissance", "RE")


def test_party_name_falls_back_on_current_name():
    assert party_name_at(PARTY, [], "2020-10-02") == ("Renaissance", "RE")
    assert party_name_at(PARTY, HISTORY, None) == ("Renaissance", "RE")
