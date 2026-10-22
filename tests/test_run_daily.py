import json
from datetime import date

import pytest

from pipeline import run_daily
from pipeline.connectors.base import Connector, RawReview


def raw(url, claimant, rating, claim_date="2026-09-13", review_date="2026-09-15T08:00:00Z", text="La dette a doublé"):
    return RawReview(url=url, source_id="tf1info_verificateurs", connector="fake", claim_text=text,
                     claimant=claimant, claim_date=claim_date, review_date=review_date, rating_original=rating)


class Fake(Connector):
    name = "fake"
    reviews: list[RawReview] = []

    def fetch(self, since: date) -> list[RawReview]:
        return list(self.reviews)


class Broken(Connector):
    name = "broken"

    def fetch(self, since: date) -> list[RawReview]:
        raise RuntimeError("site en panne")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(run_daily, "CONNECTORS", {"fake": Fake, "broken": Broken})
    monkeypatch.setattr(run_daily, "EXPORT_DIR", tmp_path / "export")
    monkeypatch.setattr(run_daily, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(run_daily, "STORE_DIR", tmp_path / "store")
    monkeypatch.setattr(run_daily, "load_validations", lambda: {})
    Fake.reviews = [
        raw("https://a/1", "Marine Le Pen", "Plutôt faux"),
        raw("https://b/1", "Marine Le Pen", "Faux", review_date="2026-09-16T08:00:00Z",
            text="La dette a-t-elle doublé ?"),
        raw("https://a/2", "Des publications sur les réseaux sociaux", "Faux"),
        raw("https://a/3", "Mathilde Panot, députée LFI", "Vrai"),
    ]
    return tmp_path


def test_full_run_is_idempotent_and_exports_only_sure_entries(env):
    db = env / "t.db"
    first = run_daily.run(["fake", "broken"], days=30, db_path=db)
    second = run_daily.run(["fake", "broken"], days=30, db_path=db)
    assert first["connectors"]["broken"]["errors"].startswith("RuntimeError")  # n'arrête pas « fake »
    assert first["connectors"]["fake"]["new"] == 4 and second["connectors"]["fake"]["new"] == 0
    assert first["reviews"] == second["reviews"] == 4
    assert second["claims"] == {"auto_sure": 1, "rejected": 1, "to_review": 1}

    facts = json.loads((env / "export" / "facts.json").read_text())
    assert len(facts) == 1
    (fact,) = facts
    assert fact["person"]["name"] == "Marine Le Pen" and len(fact["reviews"]) == 2
    assert fact["verdict"] == "unrated"  # « Plutôt faux » contre « Faux » : égalité -> unrated
    assert all(r["url"] and r["rating_original"] and r["rating_normalized"] and r["source_id"] for r in fact["reviews"])

    queue = json.loads((env / "queue" / "attributions.json").read_text())
    assert [q["candidates"][0]["name"] for q in queue] == ["Mathilde Panot"]
    stats = json.loads((env / "export" / "stats.json").read_text())
    assert stats["person"][fact["person"]["id"]]["n_claims"] == 1


def test_dry_run_writes_nothing(env):
    db = env / "dry.db"
    run_daily.run(["fake"], days=30, dry_run=True, db_path=db)
    assert not db.exists() and not (env / "export" / "facts.json").exists()


def test_store_survives_a_fresh_database(env):
    run_daily.run(["fake"], days=30, db_path=env / "a.db")
    Fake.reviews = []  # nouvelle session : la source ne renvoie plus rien, la base locale est neuve
    report = run_daily.run(["fake"], days=30, db_path=env / "b.db")
    assert report["restored"] == 4 and report["reviews"] == 4
    assert len(json.loads((env / "export" / "facts.json").read_text())) == 1


def test_export_is_never_overwritten_by_a_collapsed_base(env):
    (env / "export").mkdir()
    (env / "export" / "facts.json").write_text(json.dumps([{"id": i} for i in range(100)]))
    report = run_daily.run(["fake"], days=30, db_path=env / "c.db")
    assert report["blocked"].startswith("export refusé")
    assert len(json.loads((env / "export" / "facts.json").read_text())) == 100
