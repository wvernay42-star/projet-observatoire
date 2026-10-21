"""Aller-retour avec le tableau de validation (page web privée adossée à une base partagée).

    python -m pipeline.validation_sync seed            # prépare les files pour la page
    python -m pipeline.validation_sync apply <dossier>  # applique les décisions téléchargées

`seed` écrit data/review_queue/validation/{ratings,attributions,parties,sources}.json : un document
par file, chacun avec ses éléments (ids stables) ; `sources` est le suivi des sources (module A). Claude les dépose dans la base de la page
(collection `queues`). La page enregistre chaque décision dans la collection `decisions`
(un document par élément). `apply` lit ces décisions (fichiers JSON téléchargés) et les écrit
dans le repo :
- verdict    -> data/seeds/rating_map.csv (decided_by = human)
- attribution -> data/validations/attributions.csv (une ligne par URL de vérification)
- parti      -> data/seeds/affiliations_manual.csv (affiliation à la date de la déclaration)
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.connectors.base import SEEDS_DIR
from pipeline.ratings import LEVELS
from pipeline.text import label_key

ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = ROOT / "data" / "review_queue"
OUT_DIR = QUEUE_DIR / "validation"
ATTRIBUTIONS_CSV = ROOT / "data" / "validations" / "attributions.csv"
NO_PARTY = "none"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _short(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def rating_item_id(source_id: str, label: str) -> str:
    return "r-" + _short(f"{source_id}|{label_key(label)}")


def build_queues(queue_dir: Path = QUEUE_DIR, seeds_dir: Path = SEEDS_DIR) -> dict[str, dict[str, Any]]:
    sources = {s["id"]: s["name"] for s in _read_csv(seeds_dir / "sources.csv")}
    persons = {p["id"]: p for p in _read_csv(seeds_dir / "persons.csv")}
    parties = {p["id"]: p for p in _read_csv(seeds_dir / "parties.csv")}
    affiliations: dict[str, list[dict[str, str]]] = {}
    for a in _read_csv(seeds_dir / "affiliations.csv"):
        affiliations.setdefault(a["person_id"], []).append(a)
    proposals = {(p["source_id"], label_key(p["rating_original"])): p
                 for p in _read_csv(queue_dir / "rating_proposals.csv")}

    def load(name: str) -> list[dict[str, Any]]:
        return json.loads((queue_dir / f"{name}.json").read_text(encoding="utf-8"))

    def reviews(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"source": sources.get(r["source_id"], r["source_id"]), "url": r["url"],
                 "claimant": r["claimant"], "rating_original": r["rating_original"],
                 "review_date": r["review_date"]} for r in rows]

    def party(pid: str) -> dict[str, str]:
        p = parties.get(pid, {})
        return {"id": pid, "name": p.get("name") or pid, "short_name": p.get("short_name", "")}

    ratings = []
    for r in load("ratings"):
        proposal = proposals.get((r["source_id"], label_key(r["rating_original"] or "")))
        ratings.append({
            "id": rating_item_id(r["source_id"], r["rating_original"] or ""),
            "source_id": r["source_id"], "source": sources.get(r["source_id"], r["source_id"]),
            "label": r["rating_original"], "occurrences": r["occurrences"],
            "proposed": proposal["proposed_normalized"] if proposal else None,
            "rationale": proposal["rationale"] if proposal else None,
        })

    attributions = [{
        "id": "a-" + q["claim_id"], "claim_id": q["claim_id"], "claim_text": q["claim_text"],
        "claim_date": q["claim_date"], "reason": q["reason"], "reviews": reviews(q["reviews"]),
        "candidates": [{"id": c["id"], "name": c["name"],
                        "role": persons.get(c["id"], {}).get("public_role", "")} for c in q["candidates"]],
    } for q in load("attributions")]

    from pipeline.attribute import Referential
    ref = Referential([], [], [], list(parties.values()))
    party_items = []
    for q in load("parties"):
        pid = q["person"]["id"]
        on = q["claim_date"] or ""
        # Seuls les partis qui existaient à la date de la déclaration sont proposés.
        known = [{**party(a["party_id"]), "start_date": a["start_date"], "end_date": a["end_date"]}
                 for a in affiliations.get(pid, []) if not on or ref.party_existed(a["party_id"], on)]
        q["candidates"] = [c for c in q["candidates"] if not on or ref.party_existed(c, on)]
        party_items.append({
            "id": "p-" + q["claim_id"], "claim_id": q["claim_id"], "claim_text": q["claim_text"],
            "claim_date": q["claim_date"], "person": q["person"], "status": q["status"],
            "candidates": [party(c) for c in q["candidates"]], "known_affiliations": known,
            "reviews": reviews(q["reviews"]),
        })

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    queues = {kind: {"generated_at": now, "items": items}
              for kind, items in (("ratings", ratings), ("attributions", attributions), ("parties", party_items))}
    queues["sources"] = {"generated_at": now, "items": source_stats(seeds_dir)}
    return queues


def source_stats(seeds_dir: Path = SEEDS_DIR, db_path: Path = ROOT / "data" / "observatoire.db") -> list[dict[str, Any]]:
    """Module A, suivi interne : répartition des verdicts par source, part de verdicts positifs.

    Deux périmètres : toutes les vérifications collectées, et celles rattachées à une
    personnalité (celles qui comptent dans l'export)."""
    import sqlite3

    if not db_path.exists():
        return []
    sources = {s["id"]: s for s in _read_csv(seeds_dir / "sources.csv")}
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT r.source_id, r.rating_normalized, c.attribution_status IN ('auto_sure', 'validated') AS attributed,
               COUNT(*), MAX(r.review_date)
        FROM reviews r LEFT JOIN claims c ON c.id = r.claim_id
        GROUP BY r.source_id, r.rating_normalized, attributed""").fetchall()
    recent = dict(conn.execute("""
        SELECT source_id, COUNT(*) FROM reviews WHERE review_date >= date('now', '-30 day') GROUP BY source_id""").fetchall())
    conn.close()
    stats: dict[str, dict[str, Any]] = {}
    for source_id, level, attributed, n, last in rows:
        s = stats.setdefault(source_id, {
            "source_id": source_id, "source": sources.get(source_id, {}).get("name", source_id),
            "full_scale": sources.get(source_id, {}).get("full_scale") == "1",
            "all": {lv: 0 for lv in LEVELS}, "attributed": {lv: 0 for lv in LEVELS},
            "last_review_date": "", "last_30_days": recent.get(source_id, 0)})
        s["all"][level] += n
        if attributed:
            s["attributed"][level] += n
        s["last_review_date"] = max(s["last_review_date"], last or "")
    for s in stats.values():
        for scope in ("all", "attributed"):
            total = sum(s[scope].values())
            positive = s[scope]["true"] + s[scope]["mostly_true"]
            s[scope + "_total"] = total
            s[scope + "_positive_share"] = round(positive / total, 3) if total else None
    return sorted(stats.values(), key=lambda s: -s["attributed_total"])


def seed(out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for kind, doc in build_queues().items():
        path = out_dir / f"{kind}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        print(f"{kind}: {len(doc['items'])} éléments -> {path.relative_to(ROOT)} ({path.stat().st_size // 1024} Ko)")


def _append_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def apply(decisions: list[dict[str, Any]], queues: dict[str, dict[str, Any]], seeds_dir: Path = SEEDS_DIR,
          attributions_csv: Path = ATTRIBUTIONS_CSV) -> dict[str, int]:
    """Écrit les décisions dans le repo ; ignore celles déjà appliquées ou incohérentes."""
    items = {i["id"]: (kind, i) for kind, q in queues.items() for i in q["items"]}
    rating_rows, attribution_rows, affiliation_rows = [], [], []
    known_ratings = {(r["source_id"], label_key(r["rating_original"])) for r in _read_csv(seeds_dir / "rating_map.csv")}
    known_urls = {r["review_url"] for r in _read_csv(attributions_csv)} if attributions_csv.exists() else set()
    known_parties = {(a["person_id"], a["start_date"]) for a in _read_csv(seeds_dir / "affiliations_manual.csv")}
    from pipeline.attribute import Referential
    parties_path = seeds_dir / "parties.csv"
    periods = Referential([], [], [], _read_csv(parties_path) if parties_path.exists() else [])
    skipped = 0
    for d in decisions:
        kind, item = items.get(d.get("item_id"), (None, None))
        value, at = d.get("value"), d.get("decided_at", "")
        if item is None or kind != d.get("kind"):
            skipped += 1
            continue
        if kind == "ratings" and value in LEVELS:
            key = (item["source_id"], label_key(item["label"] or ""))
            if key not in known_ratings:
                known_ratings.add(key)
                rating_rows.append({"source_id": item["source_id"], "rating_original": item["label"],
                                    "rating_normalized": value, "decided_by": "human"})
        elif kind == "attributions" and (value == "reject" or value in {c["id"] for c in item["candidates"]}):
            for r in item["reviews"]:
                if r["url"] not in known_urls:
                    known_urls.add(r["url"])
                    attribution_rows.append({"review_url": r["url"], "decision": value, "decided_at": at,
                                             "note": d.get("note", "")})
        elif kind == "parties" and item["claim_date"] and \
                (value == NO_PARTY or (value in {c["id"] for c in item["candidates"]} | {a["id"] for a in item["known_affiliations"]}
                                       and periods.party_existed(value, item["claim_date"]))):
            key = (item["person"]["id"], item["claim_date"])
            if key not in known_parties:
                known_parties.add(key)
                affiliation_rows.append({"person_id": item["person"]["id"], "party_id": value,
                                         "start_date": item["claim_date"], "end_date": item["claim_date"],
                                         "source_url": "validation manuelle", "decided_at": at})
        else:
            skipped += 1
    _append_csv(seeds_dir / "rating_map.csv", ["source_id", "rating_original", "rating_normalized", "decided_by"], rating_rows)
    _append_csv(attributions_csv, ["review_url", "decision", "decided_at", "note"], attribution_rows)
    _append_csv(seeds_dir / "affiliations_manual.csv",
                ["person_id", "party_id", "start_date", "end_date", "source_url", "decided_at"], affiliation_rows)
    return {"ratings": len(rating_rows), "attributions": len(attribution_rows),
            "parties": len(affiliation_rows), "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("decisions_dir", type=Path, help="dossier des décisions téléchargées (*.json)")
    args = parser.parse_args()
    if args.command == "seed":
        seed()
    else:
        raw = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(args.decisions_dir.rglob("*.json"))]
        decisions = [d["data"] if isinstance(d.get("data"), dict) else d for d in raw]
        queues = {kind: json.loads((OUT_DIR / f"{kind}.json").read_text(encoding="utf-8"))
                  for kind in ("ratings", "attributions", "parties")}  # « sources » : suivi, sans décision
        print(apply(decisions, queues))


if __name__ == "__main__":
    main()
