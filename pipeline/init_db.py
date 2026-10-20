"""Crée data/observatoire.db à partir de schema.sql (idempotent)."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "observatoire.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def init_db(db_path: Path = DB_PATH) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    schema = schema.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)


if __name__ == "__main__":
    init_db()
    print(f"Base initialisée : {DB_PATH}")
