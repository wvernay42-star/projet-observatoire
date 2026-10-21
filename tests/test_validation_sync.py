import csv

from pipeline import validation_sync as vs


def write(path, header, rows=()):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def test_apply_writes_each_kind_once_and_ignores_unknown(tmp_path):
    write(tmp_path / "rating_map.csv", ["source_id", "rating_original", "rating_normalized", "decided_by"],
          [["tf1", "Faux", "false", "rule"]])
    write(tmp_path / "affiliations_manual.csv", ["person_id", "party_id", "start_date", "end_date", "source_url", "decided_at"])
    att = tmp_path / "attributions.csv"
    queues = {
        "ratings": {"items": [{"id": "r-1", "source_id": "tf1", "label": "En partie vrai"}]},
        "attributions": {"items": [{"id": "a-c1", "candidates": [{"id": "Q1"}],
                                    "reviews": [{"url": "https://x/1"}, {"url": "https://y/1"}]}]},
        "parties": {"items": [{"id": "p-c2", "claim_date": "2026-09-13", "person": {"id": "Q2"},
                               "candidates": [{"id": "RN"}], "known_affiliations": []}]},
    }
    decisions = [
        {"kind": "ratings", "item_id": "r-1", "value": "half_true", "decided_at": "t"},
        {"kind": "attributions", "item_id": "a-c1", "value": "Q1", "decided_at": "t"},
        {"kind": "parties", "item_id": "p-c2", "value": "RN", "decided_at": "t"},
        {"kind": "parties", "item_id": "p-c2", "value": "PS", "decided_at": "t"},   # hors candidats
        {"kind": "ratings", "item_id": "r-404", "value": "true", "decided_at": "t"},  # élément inconnu
    ]
    first = vs.apply(decisions, queues, seeds_dir=tmp_path, attributions_csv=att)
    second = vs.apply(decisions, queues, seeds_dir=tmp_path, attributions_csv=att)
    assert first == {"ratings": 1, "attributions": 2, "parties": 1, "skipped": 2}
    assert second["ratings"] == second["attributions"] == second["parties"] == 0
    rows = list(csv.DictReader((tmp_path / "rating_map.csv").open(encoding="utf-8")))
    assert rows[-1] == {"source_id": "tf1", "rating_original": "En partie vrai",
                        "rating_normalized": "half_true", "decided_by": "human"}
