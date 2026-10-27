"""Synchronise data/seeds/candidates_2027.csv avec la liste des candidats de Votona.

    python -m pipeline.sync_candidates /chemin/vers/votona/index.html
    python -m pipeline.sync_candidates https://votona.fr/      # site public (domaine à autoriser)

Votona (dépôt wvernay42-star/votona) est la source de la liste : nom, parti affiché, retrait, et
couleur du candidat (même couleur sur les deux sites).
Un candidat existant garde son identifiant Wikidata ; un nouveau candidat est relié au référentiel
seulement si son nom y correspond exactement et sans homonyme, sinon il est marqué « à confirmer ».
Un candidat disparu de Votona est gardé et marqué « retiré de la liste Votona » (jamais supprimé).
"""

import argparse
import csv
import re
from pathlib import Path

from pipeline.attribute import Referential
from pipeline.connectors.base import SEEDS_DIR
from pipeline.text import name_key

FIELDS = ["votona_id", "name", "votona_party", "status", "person_id", "person_match", "party_id", "votona_url", "color"]
CANDIDATE = re.compile(r'\{\s*id:"([a-z0-9-]+)", name:"([^"]+)", party:"([^"]+)"([^\n]*)')


def parse_votona(html: str) -> list[dict[str, str]]:
    return [{"votona_id": vid, "name": name, "votona_party": party,
             "status": "retiré" if re.search(r"withdrawn\s*:\s*true", rest) else "déclaré ou pressenti",
             "color": (m.group(1) if (m := re.search(r'color\s*:\s*"(#[0-9A-Fa-f]{3,8})"', rest)) else "")}
            for vid, name, party, rest in CANDIDATE.findall(html)]


def sync(html: str, seeds_dir: Path = SEEDS_DIR, ref: Referential | None = None) -> dict[str, list[str]]:
    path = seeds_dir / "candidates_2027.csv"
    with path.open(encoding="utf-8") as f:
        rows = {r["votona_id"]: r for r in csv.DictReader(f)}
    ref = ref or Referential.load(seeds_dir)
    with (seeds_dir / "parties.csv").open(encoding="utf-8") as f:
        parties = {name_key(n): p["id"] for p in csv.DictReader(f) for n in (p["name"], p["short_name"]) if n}
    report: dict[str, list[str]] = {"ajoutés": [], "modifiés": [], "absents de Votona": [], "à confirmer": []}
    seen = set()
    for c in parse_votona(html):
        seen.add(c["votona_id"])
        row = rows.get(c["votona_id"])
        if row is None:
            found = ref.attribute(c["name"])
            sure = found.status == "auto_sure" and found.person_id and not found.person_id.startswith("votona:")
            row = {**c, "person_id": found.person_id if sure else "", "person_match": "sûr" if sure else "à confirmer",
                   "party_id": parties.get(name_key(c["votona_party"]), ""),
                   "votona_url": f"https://votona.fr/candidats/{c['votona_id']}/"}
            rows[c["votona_id"]] = row
            report["ajoutés"].append(c["name"])
        elif any(row[k] != c[k] for k in ("name", "votona_party", "status")):
            report["modifiés"].append(f"{c['name']} ({row['votona_party']} / {row['status']} -> {c['votona_party']} / {c['status']})")
            row.update(c)
        row["color"] = c["color"]  # suit Votona sans être signalé comme un changement de candidature
    for vid, row in rows.items():
        if vid not in seen and row["status"] != "retiré de la liste Votona":
            row["status"] = "retiré de la liste Votona"
            report["absents de Votona"].append(row["name"])
    report["à confirmer"] = [r["name"] for r in rows.values() if r["person_match"] == "à confirmer"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows.values())
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("votona_index", help="index.html du dépôt Votona, ou l'adresse https://votona.fr/")
    args = parser.parse_args()
    if args.votona_index.startswith("https://"):
        import httpx

        response = httpx.get(args.votona_index, timeout=60, follow_redirects=True)
        response.raise_for_status()
        html = response.text
    else:
        html = Path(args.votona_index).read_text(encoding="utf-8")
    if not parse_votona(html):
        raise SystemExit("Aucun candidat trouvé dans la page Votona : liste inchangée.")
    for key, names in sync(html).items():
        print(f"{key} : {len(names)}" + (f" — {', '.join(names)}" if names else ""))


if __name__ == "__main__":
    main()
