"""Routine quotidienne : collecte -> normalisation -> dédoublonnage -> attribution ->
conversion des verdicts -> file de validation -> export -> journal.

    python -m pipeline.run_daily                         # routine complète
    python -m pipeline.run_daily --days 90               # rattrapage sur 90 jours
    python -m pipeline.run_daily --connector google_factcheck --dry-run

Idempotente : relancer le même jour ne crée aucun doublon (clé url unique, claims recalculés).
Une erreur sur un connecteur n'arrête pas les autres.
"""

import argparse
import csv
import json
import sqlite3
import traceback
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pipeline.attribute import Attribution, Referential
from pipeline.connectors.base import Connector, RawReview
from pipeline.connectors.datacommons_feed import DataCommonsFeed
from pipeline.connectors.google_factcheck import GoogleFactCheck
from pipeline.dedupe import group_reviews
from pipeline.export import EXPORT_DIR, export
from pipeline.init_db import DB_PATH, init_db
from pipeline.normalize import claim_dates, normalize
from pipeline.ratings import convert, load_rating_map

ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = ROOT / "data" / "review_queue"
VALIDATIONS = ROOT / "data" / "validations" / "attributions.csv"
STORE_DIR = ROOT / "data" / "store"  # mémoire versionnée de la base (la base SQLite n'est pas commitée)
OVERLAP_DAYS = 7
ZERO_ALERT_RUNS = 3
MIN_EXPORT_RATIO = 0.5  # en dessous, on refuse d'écraser l'export (base vide, panne…)

CONNECTORS: dict[str, type[Connector]] = {
    GoogleFactCheck.name: GoogleFactCheck,
    DataCommonsFeed.name: DataCommonsFeed,
}

RUN_COLUMNS = ["id", "started_at", "connector", "fetched", "new_reviews", "errors"]
REVIEW_COLUMNS = ["id", "source_id", "url", "title", "rating_original", "rating_normalized", "rating_method",
                  "review_date", "ingested_at", "lang", "connector", "claimant", "claim_text", "claim_date_raw"]


def last_success(conn: sqlite3.Connection, connector: str) -> date | None:
    row = conn.execute("SELECT MAX(started_at) FROM runs WHERE connector = ? AND errors IS NULL",
                       (connector,)).fetchone()
    return date.fromisoformat(row[0][:10]) if row and row[0] else None


def collect(conn: sqlite3.Connection, names: list[str], days: int | None, now: datetime,
            rating_map: dict) -> dict[str, dict[str, Any]]:
    report = {}
    for name in names:
        last = last_success(conn, name)
        since = now.date() - timedelta(days=days) if days else \
            (last - timedelta(days=OVERLAP_DAYS) if last else now.date() - timedelta(days=OVERLAP_DAYS))
        fetched, new, errors = 0, 0, None
        try:
            raws: list[RawReview] = CONNECTORS[name]().fetch(since)
            fetched = len(raws)
            for raw in raws:
                row = normalize(raw, rating_map, now.isoformat(timespec="seconds"))
                exists = conn.execute("SELECT 1 FROM reviews WHERE url = ?", (row["url"],)).fetchone()
                new += not exists
                updates = ", ".join(f"{c} = excluded.{c}" for c in REVIEW_COLUMNS if c not in ("id", "ingested_at"))
                conn.execute(
                    f"INSERT INTO reviews ({', '.join(REVIEW_COLUMNS)}) VALUES ({', '.join('?' * len(REVIEW_COLUMNS))})"
                    f" ON CONFLICT(url) DO UPDATE SET {updates}", [row[c] for c in REVIEW_COLUMNS])
        except Exception as exc:  # un connecteur en panne n'arrête pas les autres
            errors = f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
        conn.execute("INSERT INTO runs (started_at, connector, fetched, new_reviews, errors) VALUES (?, ?, ?, ?, ?)",
                     (now.isoformat(timespec="seconds"), name, fetched, new, errors))
        report[name] = {"since": since.isoformat(), "fetched": fetched, "new": new, "errors": errors}
    return report


def refresh_ratings(conn: sqlite3.Connection, rating_map: dict) -> None:
    """Réapplique rating_map à toutes les reviews (une validation de libellé vaut pour le passé)."""
    for rid, source_id, original in conn.execute("SELECT id, source_id, rating_original FROM reviews").fetchall():
        raw = RawReview(url="", source_id=source_id, connector="", claim_text=None, claimant=None,
                        claim_date=None, review_date=None, rating_original=original)
        rating = convert(raw, rating_map)
        conn.execute("UPDATE reviews SET rating_normalized = ?, rating_method = ? WHERE id = ?",
                     (rating.normalized, rating.method, rid))


def load_validations(path: Path = VALIDATIONS) -> dict[str, str]:
    """URL de vérification -> QID de la personne validée, ou 'reject'."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {row["review_url"]: row["decision"] for row in csv.DictReader(f) if row["decision"]}


def rebuild_claims(conn: sqlite3.Connection, ref: Referential, validations: dict[str, str]) -> None:
    """Recalcule tous les claims depuis les reviews : déterministe, donc idempotent."""
    conn.row_factory = sqlite3.Row
    reviews = conn.execute("SELECT * FROM reviews").fetchall()
    attributions: dict[str, Attribution] = {}
    items = []
    for r in reviews:
        decision = validations.get(r["url"])
        if decision == "reject":
            attribution = Attribution("rejected", reason="rejeté à la validation")
        elif decision:
            attribution = Attribution("validated", decision, reason="validé à la main")
        else:
            attribution = ref.attribute(r["claimant"])
        attributions[r["id"]] = attribution
        claim_date, _, fallback = claim_dates(dict(r))
        items.append((r["id"], attribution.person_id, claim_date, r["claim_text"] or r["title"] or "", fallback))

    by_id = {r["id"]: r for r in reviews}
    conn.execute("DELETE FROM claims")
    for group in group_reviews(items):
        dated = [by_id[rid] for rid in group.review_ids if not claim_dates(dict(by_id[rid]))[2]]
        first = dated[0] if dated else by_id[group.review_ids[0]]
        attribution = attributions[first["id"]]
        claim_date, precision, fallback = claim_dates(dict(first))
        claim_id = "c_" + min(group.review_ids)
        conn.execute(
            "INSERT INTO claims (id, text, person_id, claim_date, date_precision, date_is_fallback, country,"
            " channel, attribution_status, attribution_reason, candidates) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (claim_id, first["claim_text"], attribution.person_id, claim_date, precision, fallback, "FR", None,
             attribution.status, attribution.reason, json.dumps(list(attribution.candidates))))
        conn.executemany("UPDATE reviews SET claim_id = ? WHERE id = ?", [(claim_id, rid) for rid in group.review_ids])
    conn.row_factory = None


def write_queues(conn: sqlite3.Connection, ref: Referential, out_dir: Path = QUEUE_DIR) -> dict[str, int]:
    """Files de validation (jamais publiées) : attributions, partis, libellés de verdict."""
    conn.row_factory = sqlite3.Row
    claims = conn.execute("SELECT * FROM claims WHERE attribution_status IN ('to_review', 'auto_sure', 'validated')"
                          " ORDER BY claim_date DESC").fetchall()

    def reviews_of(claim_id: str) -> list[dict[str, Any]]:
        return [{k: r[k] for k in ("url", "source_id", "claimant", "rating_original", "rating_normalized", "review_date")}
                for r in conn.execute("SELECT * FROM reviews WHERE claim_id = ?", (claim_id,))]

    attributions, parties = [], []
    for c in claims:
        base = {"claim_id": c["id"], "claim_text": c["text"], "claim_date": c["claim_date"], "reviews": reviews_of(c["id"])}
        if c["attribution_status"] == "to_review":
            candidates = json.loads(c["candidates"] or "[]")
            attributions.append({**base, "reason": c["attribution_reason"],
                                 "candidates": [{"id": q, "name": ref.full_names.get(q, q)} for q in candidates]})
        else:
            party = ref.party_at(c["person_id"], c["claim_date"])
            if party.status not in ("ok", "no_party"):
                parties.append({**base, "person": {"id": c["person_id"], "name": ref.full_names.get(c["person_id"])},
                                "status": party.status, "candidates": list(party.candidates)})
    # Libellés à valider : seulement ceux qui touchent une déclaration attribuée (ou à attribuer).
    # Ceux des rumeurs non attribuées ne changent rien à ce qui est publié : inutile de les montrer.
    ratings = [{"source_id": s, "rating_original": o, "occurrences": n} for s, o, n in conn.execute(
        "SELECT r.source_id, r.rating_original, COUNT(*) FROM reviews r JOIN claims c ON c.id = r.claim_id"
        " WHERE r.rating_method = 'pending' AND c.attribution_status IN ('to_review', 'auto_sure', 'validated')"
        " GROUP BY r.source_id, r.rating_original ORDER BY COUNT(*) DESC")]
    # Les candidats 2027 d'abord (cœur du site) ; tri stable : chaque groupe reste du plus récent au plus ancien.
    attributions.sort(key=lambda q: not any(c["id"] in ref.candidates for c in q["candidates"]))
    parties.sort(key=lambda q: q["person"]["id"] not in ref.candidates)
    conn.row_factory = None

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("attributions", attributions), ("parties", parties), ("ratings", ratings)):
        (out_dir / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"attributions": len(attributions), "parties": len(parties), "ratings": len(ratings)}


def silent_connectors(conn: sqlite3.Connection) -> list[str]:
    """Connecteurs sans nouvelle vérification sur les 3 derniers jours d'exécution (format changé ?)."""
    silent = []
    for (name,) in conn.execute("SELECT DISTINCT connector FROM runs").fetchall():
        days = conn.execute(
            "SELECT substr(started_at, 1, 10) AS day, SUM(new_reviews) FROM runs WHERE connector = ?"
            " GROUP BY day ORDER BY day DESC LIMIT ?", (name, ZERO_ALERT_RUNS)).fetchall()
        if len(days) == ZERO_ALERT_RUNS and all(n == 0 for _, n in days):
            silent.append(name)
    return silent


def run(names: list[str], days: int | None = None, dry_run: bool = False, db_path: Path = DB_PATH) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    if dry_run:
        conn = sqlite3.connect(":memory:")
        if db_path.exists():
            sqlite3.connect(db_path).backup(conn)
    else:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
    init_db_conn(conn)
    rating_map = load_rating_map()
    ref = Referential.load()

    report: dict[str, Any] = {"restored": load_store(conn, STORE_DIR)}
    report["connectors"] = collect(conn, names, days, now, rating_map)
    refresh_ratings(conn, rating_map)
    rebuild_claims(conn, ref, load_validations())
    statuses = Counter(s for (s,) in conn.execute("SELECT attribution_status FROM claims"))
    report["reviews"] = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    report["claims"] = dict(statuses)
    if not dry_run:
        published = conn.execute("SELECT COUNT(*) FROM claims WHERE attribution_status IN ('auto_sure', 'validated')").fetchone()[0]
        before = previous_export_size(EXPORT_DIR)
        if before > 20 and published < before * MIN_EXPORT_RATIO:
            # Garde-fou : une base vide ou partielle ne doit jamais écraser l'export publié.
            report["blocked"] = f"export refusé : {published} entrées contre {before} publiées"
        else:
            report["queues"] = write_queues(conn, ref, QUEUE_DIR)
            report["exported"] = export(conn, ref, EXPORT_DIR)
        conn.commit()
        save_store(conn, STORE_DIR)
    report["silent_connectors"] = silent_connectors(conn)
    conn.close()
    return report


def load_store(conn: sqlite3.Connection, store_dir: Path = STORE_DIR) -> int:
    """Recharge la base depuis data/store/*.jsonl quand elle est vide (nouvelle session, nouveau clone)."""
    if conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] or not (store_dir / "reviews.jsonl").exists():
        return 0
    loaded = 0
    for table, columns in (("reviews", REVIEW_COLUMNS), ("runs", RUN_COLUMNS)):
        path = store_dir / f"{table}.jsonl"
        if not path.exists():
            continue
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        conn.executemany(f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
                         [[r.get(c) for c in columns] for r in rows])
        loaded += len(rows) if table == "reviews" else 0
    return loaded


def save_store(conn: sqlite3.Connection, store_dir: Path = STORE_DIR) -> None:
    """Écrit la base en JSON Lines triés (diff lisible dans git) : toutes les vérifications et le journal des exécutions."""
    store_dir.mkdir(parents=True, exist_ok=True)
    for table, columns, order in (("reviews", REVIEW_COLUMNS, "url"), ("runs", RUN_COLUMNS, "id")):
        rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order}").fetchall()
        (store_dir / f"{table}.jsonl").write_text(
            "".join(json.dumps(dict(zip(columns, r)), ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
            encoding="utf-8")


def previous_export_size(export_dir: Path) -> int:
    path = export_dir / "facts.json"
    try:
        return len(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return 0


def init_db_conn(conn: sqlite3.Connection) -> None:
    schema = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")
    conn.executescript(schema.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS "))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--connector", action="append", choices=list(CONNECTORS),
                        help="limiter à ce connecteur (répétable) ; défaut : tous")
    parser.add_argument("--days", type=int, help="fenêtre de collecte (défaut : depuis le dernier succès - 7 j)")
    parser.add_argument("--dry-run", action="store_true", help="n'écrit ni la base ni les exports")
    args = parser.parse_args()
    report = run(args.connector or list(CONNECTORS), args.days, args.dry_run)

    if report.get("restored"):
        print(f"Base rechargée depuis data/store : {report['restored']} vérifications")
    print("Collecte :")
    for name, r in report["connectors"].items():
        status = f"ERREUR {r['errors']}" if r["errors"] else "ok"
        print(f"  {name:<18} depuis {r['since']} : {r['fetched']} récupérées, {r['new']} nouvelles — {status}")
    print(f"Base : {report['reviews']} vérifications, claims : {report['claims']}")
    if "queues" in report:
        q = report["queues"]
        print(f"File de validation : {q['attributions']} attributions, {q['parties']} partis, {q['ratings']} libellés")
        print(f"Exportées (data/export/facts.json) : {report['exported']}")
    if report.get("blocked"):
        print(f"ALERTE : {report['blocked']} (base incomplète ?). Rien n'a été exporté.")
    if report["silent_connectors"]:
        print(f"ALERTE : aucun résultat nouveau depuis {ZERO_ALERT_RUNS} jours : {report['silent_connectors']}")


if __name__ == "__main__":
    main()
