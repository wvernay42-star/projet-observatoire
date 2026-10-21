"""Export public : data/export/facts.json (entrées validées) et stats.json (agrégats).

Seuls les claims dont l'attribution est 'auto_sure' ou 'validated' sont exportés.
Métadonnées uniquement : jamais le contenu des articles.
"""

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pipeline.attribute import Referential
from pipeline.connectors.base import SEEDS_DIR
from pipeline.dedupe import majority_verdict
from pipeline.ratings import LEVELS

EXPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "export"
PUBLISHED = ("auto_sure", "validated")
SCOPE_NOTE = "Sur les déclarations vérifiées, pas sur l'ensemble des propos."


def _read(name: str) -> dict[str, dict[str, str]]:
    with (SEEDS_DIR / name).open(encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def load_party_names() -> dict[str, list[dict[str, str]]]:
    """Noms datés des partis : corrections manuelles d'abord, puis Wikidata (P1448)."""
    names: dict[str, list[dict[str, str]]] = {}
    for file in ("party_names_manual.csv", "party_names.csv"):
        path = SEEDS_DIR / file
        if not path.exists():
            continue
        manual_parties = set(names)  # le fichier manuel fait foi pour les partis qu'il couvre
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["party_id"] not in manual_parties:
                    names.setdefault(row["party_id"], []).append(row)
    return names


def party_name_at(party: dict[str, str], history: list[dict[str, str]], on: str | None) -> tuple[str, str]:
    """(nom, sigle) du parti à la date de la déclaration ; à défaut, le nom actuel."""
    if on:
        for n in history:
            k_start, k_end = min(len(n["start_date"]), len(on)), min(len(n["end_date"]), len(on))
            if n["start_date"] and n["start_date"][:k_start] <= on[:k_start] and \
                    (not n["end_date"] or on[:k_end] < n["end_date"][:k_end]):
                return n["name"], n["short_name"] or (party.get("short_name", "") if not n["end_date"] else "")
    return party.get("name", ""), party.get("short_name", "")


def build_facts(conn: sqlite3.Connection, ref: Referential) -> list[dict[str, Any]]:
    sources, parties = _read("sources.csv"), _read("parties.csv")
    party_names = load_party_names()
    conn.row_factory = sqlite3.Row
    claims = conn.execute(
        f"SELECT * FROM claims WHERE attribution_status IN ({','.join('?' * len(PUBLISHED))})"
        " ORDER BY claim_date DESC, id", PUBLISHED).fetchall()
    facts = []
    for c in claims:
        reviews = conn.execute("SELECT * FROM reviews WHERE claim_id = ? ORDER BY review_date, url",
                               (c["id"],)).fetchall()
        party = ref.party_at(c["person_id"], c["claim_date"])
        p = parties.get(party.party_id or "", {})
        name, short = party_name_at(p, party_names.get(party.party_id or "", []), c["claim_date"]) if p else (None, None)
        facts.append({
            "id": c["id"],
            "person": {"id": c["person_id"], "name": ref.full_names.get(c["person_id"], ""),
                       "votona_id": ref.candidates.get(c["person_id"], {}).get("votona_id")},
            "party": {"id": party.party_id, "name": name, "short_name": short, "status": party.status},
            "claim_text": c["text"],
            "claim_date": c["claim_date"],
            "date_precision": c["date_precision"],
            "date_is_fallback": bool(c["date_is_fallback"]),
            "country": c["country"],
            "attribution_status": c["attribution_status"],
            "verdict": majority_verdict([r["rating_normalized"] for r in reviews]),
            "reviews": [{
                "source_id": r["source_id"],
                "source_name": sources.get(r["source_id"], {}).get("name", r["source_id"]),
                "url": r["url"],
                "title": r["title"],
                "rating_original": r["rating_original"],
                "rating_normalized": r["rating_normalized"],
                "review_date": r["review_date"],
            } for r in reviews],
        })
    return facts


def _bucket() -> dict[str, Any]:
    return {"n": 0, "verdicts": Counter(), "sources": set(), "last_review_date": ""}


def build_stats(facts: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, dict[str, Any]]] = {k: defaultdict(_bucket) for k in ("person", "party", "country", "month")}
    for f in facts:
        keys = {"person": f["person"]["id"], "party": f["party"]["id"], "country": f["country"],
                "month": (f["claim_date"] or "")[:7] or None}
        for kind, key in keys.items():
            if not key:
                continue
            b = groups[kind][key]
            b["n"] += 1
            b["verdicts"][f["verdict"]] += 1
            b["sources"].update(r["source_id"] for r in f["reviews"])
            b["last_review_date"] = max([b["last_review_date"]] + [r["review_date"] or "" for r in f["reviews"]])
    return {
        "scope_note": SCOPE_NOTE,
        **{kind: {key: {"n_claims": b["n"],
                        "verdicts": {level: b["verdicts"].get(level, 0) for level in LEVELS},
                        "n_sources": len(b["sources"]),
                        "last_review_date": b["last_review_date"] or None}
                  for key, b in sorted(g.items())}
           for kind, g in groups.items()},
    }


def export(conn: sqlite3.Connection, ref: Referential, out_dir: Path = EXPORT_DIR) -> int:
    facts = build_facts(conn, ref)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "stats.json").write_text(json.dumps(build_stats(facts), ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    return len(facts)
