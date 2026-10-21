"""Génère web/beta/index.html : le gabarit de la beta avec l'export embarqué.

    python -m pipeline.build_beta

Embarque data/export/facts.json, la liste des sources et l'adresse de contact. La page est
ensuite publiée telle quelle (artefact) ; elle ne charge aucune donnée à distance.
"""

import base64
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pipeline.connectors.base import SEEDS_DIR
from pipeline.export import EXPORT_DIR

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "web" / "beta" / "template.html"
OUTPUT = ROOT / "web" / "beta" / "index.html"
PLACEHOLDER = '/*__DATA__*/{"generated_at":null,"facts":[],"sources":[],"contact":"","candidates":[]}'
LOGO_PLACEHOLDER = "/*__LOGO__*/"
LOGO = Path(__file__).resolve().parents[1] / "web" / "beta" / "logo-head.webp"
CONTACT = "contact@votona.fr"


def build(export_dir: Path = EXPORT_DIR, template: Path = TEMPLATE, output: Path = OUTPUT) -> int:
    facts = json.loads((export_dir / "facts.json").read_text(encoding="utf-8"))
    with (SEEDS_DIR / "sources.csv").open(encoding="utf-8") as f:
        sources = [{"id": s["id"], "name": s["name"], "url": s["url"]} for s in csv.DictReader(f)]
    generated = datetime.fromtimestamp((export_dir / "facts.json").stat().st_mtime, timezone.utc)
    with (SEEDS_DIR / "candidates_2027.csv").open(encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))
    data = {"generated_at": generated.isoformat(timespec="seconds"), "facts": facts,
            "sources": sources, "contact": CONTACT, "candidates": candidates}
    # « </ » échappé : le JSON ne peut pas fermer la balise <script> qui l'embarque.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = template.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise ValueError("Emplacement des données introuvable dans le gabarit")
    html = html.replace(PLACEHOLDER, payload)
    # Artefact : logo embarqué (aucune ressource externe) ; site : fichier servi à côté de la page.
    logo = "data:image/webp;base64," + base64.b64encode(LOGO.read_bytes()).decode()
    output.write_text(html.replace(LOGO_PLACEHOLDER, logo), encoding="utf-8")
    build_site(html.replace(LOGO_PLACEHOLDER, "/assets/logo-head.webp"))
    return len(facts)


SITE_DIR = ROOT / "site"
SITE_HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="Votona Observatoire : les vérifications des fact-checkers français sur les candidats à la présidentielle 2027 et la vie politique, avec le verdict d'origine et un lien vers chaque article.">
<link rel="icon" href="/assets/favicon-48.png">
<style>:root{color-scheme:light}body{margin:0;padding:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
"""


def build_site(page: str, site_dir: Path = SITE_DIR) -> None:
    """Version site (Vercel) : même page, document complet, en noindex tant que c'est la préproduction."""
    (site_dir / "assets").mkdir(parents=True, exist_ok=True)
    # Le titre et les liens de polices du gabarit vont dans le <head> du document complet.
    head_tags = re.findall(r"^(?:<title>.*?</title>|<link [^>]*>)\s*$", page, flags=re.M)
    body = re.sub(r"^(?:<title>.*?</title>|<link [^>]*>|<meta name=\"claude:[^>]*>)\s*\n", "", page, flags=re.M)
    head = SITE_HEAD.replace("</head>", "\n".join(head_tags) + "\n</head>")
    (site_dir / "index.html").write_text(head + body + "\n</body>\n</html>\n", encoding="utf-8")
    shutil.copyfile(LOGO, site_dir / "assets" / "logo-head.webp")
    favicon = LOGO.with_name("favicon-48.png")
    if favicon.exists():
        shutil.copyfile(favicon, site_dir / "assets" / "favicon-48.png")
    (site_dir / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")


if __name__ == "__main__":
    n = build()
    print(f"{OUTPUT.relative_to(ROOT)} et site/index.html : {n} déclarations embarquées")
