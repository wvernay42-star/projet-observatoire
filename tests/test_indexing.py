import json
from pathlib import Path

from pipeline import build_pages

ROOT = Path(__file__).resolve().parents[1]


def test_preprod_never_indexed_and_prod_follows_switch():
    rules = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["headers"]
    noindex = [r for r in rules if any(h["key"] == "X-Robots-Tag" for h in r["headers"])]
    # L'en-tête noindex s'applique à tout domaine autre que la production (préproduction, *.vercel.app).
    assert noindex and all(r.get("missing") == [{"type": "host", "value": "observatoire.votona.fr"}] for r in noindex)


def test_production_open_with_sitemap(tmp_path):
    # Indexation ouverte le 28/10/2026 (docs/decisions.md) ; la préproduction reste en noindex (en-tête).
    assert build_pages.INDEXABLE is True
