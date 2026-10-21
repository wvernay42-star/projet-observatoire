"""Génère web/beta/index.html : le gabarit de la beta avec l'export embarqué.

    python -m pipeline.build_beta

Embarque data/export/facts.json, la liste des sources et l'adresse de contact. La page est
ensuite publiée telle quelle (artefact) ; elle ne charge aucune donnée à distance.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.connectors.base import SEEDS_DIR
from pipeline.export import EXPORT_DIR

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "web" / "beta" / "template.html"
OUTPUT = ROOT / "web" / "beta" / "index.html"
PLACEHOLDER = '/*__DATA__*/{"generated_at":null,"facts":[],"sources":[],"contact":""}'
CONTACT = "guillaume.nevert@outlook.com"


def build(export_dir: Path = EXPORT_DIR, template: Path = TEMPLATE, output: Path = OUTPUT) -> int:
    facts = json.loads((export_dir / "facts.json").read_text(encoding="utf-8"))
    with (SEEDS_DIR / "sources.csv").open(encoding="utf-8") as f:
        sources = [{"id": s["id"], "name": s["name"], "url": s["url"]} for s in csv.DictReader(f)]
    generated = datetime.fromtimestamp((export_dir / "facts.json").stat().st_mtime, timezone.utc)
    data = {"generated_at": generated.isoformat(timespec="seconds"), "facts": facts,
            "sources": sources, "contact": CONTACT}
    # « </ » échappé : le JSON ne peut pas fermer la balise <script> qui l'embarque.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = template.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise ValueError("Emplacement des données introuvable dans le gabarit")
    output.write_text(html.replace(PLACEHOLDER, payload), encoding="utf-8")
    return len(facts)


if __name__ == "__main__":
    n = build()
    print(f"{OUTPUT.relative_to(ROOT)} : {n} déclarations embarquées")
