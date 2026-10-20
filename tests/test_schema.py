import sqlite3

from pipeline.init_db import init_db

EXPECTED = {"sources", "persons", "parties", "affiliations", "claims", "reviews",
            "rating_map", "official_refs", "runs"}


def test_schema_creates_all_tables(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    init_db(db)  # idempotent
    with sqlite3.connect(db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED <= tables
