"""Génère web/beta/index.html : le gabarit de la beta avec l'export embarqué.

    python -m pipeline.build_beta

Embarque data/export/facts.json, la liste des sources, les sujets de Votona et l'adresse de
contact. La page est publiée telle quelle (artefact) ; elle ne charge aucune donnée à distance.
La version site (site/, Vercel) ajoute les données ouvertes : donnees/facts.json, donnees/facts.csv
et flux.xml (RSS des dernières vérifications).
"""

import base64
import csv
import json
import re
import shutil
from email.utils import format_datetime
from xml.sax.saxutils import escape
from datetime import datetime, timezone
from pathlib import Path

from pipeline import build_pages
from pipeline.connectors.base import SEEDS_DIR
from pipeline.export import EXPORT_DIR

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "web" / "beta" / "template.html"
OUTPUT = ROOT / "web" / "beta" / "index.html"
PLACEHOLDER = '/*__DATA__*/{"generated_at":null,"facts":[],"sources":[],"contact":"","candidates":[]}'
LOGO_PLACEHOLDER = "/*__LOGO__*/"
LOGO = Path(__file__).resolve().parents[1] / "web" / "beta" / "logo-head.webp"
# Accessoires des 7 familles de sujets, copiés de Votona (assets/props) : même identité visuelle.
PROPS_PLACEHOLDER = "/*__PROPS__*/{}"
PROPS_DIR = LOGO.with_name("props")
CONTACT = "contact@votona.fr"
SITE_URL = "https://observatoire.votona.fr"  # adresse de production (liens absolus du flux RSS)


def build(export_dir: Path = EXPORT_DIR, template: Path = TEMPLATE, output: Path = OUTPUT) -> int:
    facts = json.loads((export_dir / "facts.json").read_text(encoding="utf-8"))
    with (SEEDS_DIR / "sources.csv").open(encoding="utf-8") as f:
        sources = [{"id": s["id"], "name": s["name"], "url": s["url"]} for s in csv.DictReader(f)]
    generated = datetime.fromtimestamp((export_dir / "facts.json").stat().st_mtime, timezone.utc)
    with (SEEDS_DIR / "candidates_2027.csv").open(encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))
    with (SEEDS_DIR / "themes.csv").open(encoding="utf-8") as f:
        topics = [{"slug": t["key"], "label": t["label"], "category": t["category"]}
                  for t in csv.DictReader(f) if t["kind"] == "topic"]
    data = {"generated_at": generated.isoformat(timespec="seconds"), "facts": facts, "sources": sources,
            "contact": CONTACT, "candidates": candidates, "topics": topics}
    html = template.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        raise ValueError("Emplacement des données introuvable dans le gabarit")

    pages = build_pages.load_site(facts, data["generated_at"])
    # Sur le site, une personne, un parti ou un sujet ouvre sa page fixe (pipeline/build_pages.py).
    urls = {"persons": pages.person_url, "parties": pages.party_url}

    def page(site: bool, logo: str) -> str:
        # « </ » échappé : le JSON ne peut pas fermer la balise <script> qui l'embarque.
        payload = json.dumps({**data, "site": site, **({"urls": urls} if site else {})}, ensure_ascii=False,
                             separators=(",", ":")).replace("</", "<\\/")
        if site:
            props = {f.stem: f"/assets/props/{f.name}" for f in sorted(PROPS_DIR.glob("*.webp"))}
        else:
            props = {f.stem: "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode()
                     for f in sorted(PROPS_DIR.glob("*.webp"))}
        return (html.replace(PLACEHOLDER, payload).replace(LOGO_PLACEHOLDER, logo)
                .replace(PROPS_PLACEHOLDER, json.dumps(props)))

    # Artefact : logo embarqué (aucune ressource externe) ; site : fichier servi à côté de la page.
    output.write_text(page(False, "data:image/webp;base64," + base64.b64encode(LOGO.read_bytes()).decode()), encoding="utf-8")
    build_site(page(True, "/assets/logo-head.webp"))
    write_open_data(facts, generated)
    build_pages.build(pages, SITE_DIR)
    return len(facts)


SITE_DIR = ROOT / "site"
SITE_HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
__ROBOTS__<meta name="description" content="Votona Observatoire : les vérifications des fact-checkers français sur les candidats à la présidentielle 2027 et la vie politique, avec le verdict d'origine et un lien vers chaque article.">
<link rel="icon" href="/assets/favicon-48.png">
<link rel="canonical" href="https://observatoire.votona.fr/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Votona Observatoire">
<meta property="og:title" content="Votona Observatoire - les déclarations vérifiées">
<meta property="og:description" content="Les vérifications des fact-checkers français sur les candidats à la présidentielle 2027 et la vie politique, avec le verdict d'origine.">
<meta property="og:image" content="https://observatoire.votona.fr/assets/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="Votona Observatoire - dernières vérifications" href="/flux.xml">
<style>:root{color-scheme:light}body{margin:0;padding:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
"""


def build_site(page: str, site_dir: Path = SITE_DIR) -> None:
    """Version site (Vercel) : même page, document complet ; indexable seulement si build_pages.INDEXABLE."""
    (site_dir / "assets").mkdir(parents=True, exist_ok=True)
    # Le titre et les liens de polices du gabarit vont dans le <head> du document complet.
    head_tags = re.findall(r"^(?:<title>.*?</title>|<link [^>]*>)\s*$", page, flags=re.M)
    body = re.sub(r"^(?:<title>.*?</title>|<link [^>]*>|<meta name=\"claude:[^>]*>)\s*\n", "", page, flags=re.M)
    robots = "" if build_pages.INDEXABLE else '<meta name="robots" content="noindex, nofollow">\n'
    head = SITE_HEAD.replace("__ROBOTS__", robots).replace("</head>", "\n".join(head_tags) + "\n</head>")
    (site_dir / "index.html").write_text(head + body + "\n</body>\n</html>\n", encoding="utf-8")
    shutil.copyfile(LOGO, site_dir / "assets" / "logo-head.webp")
    shutil.copyfile(LOGO.with_name("og.jpg"), site_dir / "assets" / "og.jpg")
    (site_dir / "assets" / "props").mkdir(exist_ok=True)
    for f in PROPS_DIR.glob("*.webp"):
        shutil.copyfile(f, site_dir / "assets" / "props" / f.name)
    favicon = LOGO.with_name("favicon-48.png")
    if favicon.exists():
        shutil.copyfile(favicon, site_dir / "assets" / "favicon-48.png")
    # Ouvert selon build_pages.INDEXABLE ; la préproduction reste
    # en noindex de toute façon (en-tête X-Robots-Tag hors du domaine de production, vercel.json).
    (site_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {build_pages.SITE_URL}/sitemap.xml\n" if build_pages.INDEXABLE
        else "User-agent: *\nDisallow: /\n", encoding="utf-8")


OPEN_DATA_COLUMNS = ["id", "person_id", "person_name", "votona_id", "party_id", "party_name", "party_name_at_date", "party_status",
                     "claim_text", "claim_date", "date_is_fallback", "verdict", "theme", "votona_topics",
                     "source_id", "source_name", "url", "title", "rating_original", "rating_normalized", "review_date"]
RSS_ITEMS = 50


def write_open_data(facts: list[dict], generated: datetime, site_dir: Path = SITE_DIR) -> None:
    """Données ouvertes du site : la base publiée en JSON et CSV (une ligne par vérification), et un flux RSS."""
    out = site_dir / "donnees"
    out.mkdir(parents=True, exist_ok=True)
    (out / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "facts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OPEN_DATA_COLUMNS)
        w.writeheader()
        for fact in facts:
            for r in fact["reviews"]:
                w.writerow({"id": fact["id"], "person_id": fact["person"]["id"], "person_name": fact["person"]["name"],
                            "votona_id": fact["person"].get("votona_id") or "", "party_id": fact["party"]["id"] or "",
                            "party_name": fact["party"]["name"] or "", "party_name_at_date": fact["party"].get("name_at_date") or "", "party_status": fact["party"]["status"],
                            "claim_text": fact["claim_text"], "claim_date": fact["claim_date"] or "",
                            "date_is_fallback": int(fact["date_is_fallback"]), "verdict": fact["verdict"],
                            "theme": fact.get("theme") or "",
                            "votona_topics": ";".join(t["slug"] for t in fact.get("votona_topics", [])),
                            **{k: r[k] or "" for k in ("source_id", "source_name", "url", "title", "rating_original",
                                                       "rating_normalized", "review_date")}})
    latest = sorted(facts, key=lambda f: max((r["review_date"] or "" for r in f["reviews"]), default=""), reverse=True)
    items = []
    for fact in latest[:RSS_ITEMS]:
        r = max(fact["reviews"], key=lambda x: x["review_date"] or "")
        when = datetime.fromisoformat((r["review_date"] or generated.date().isoformat())[:10]).replace(hour=12, tzinfo=timezone.utc)
        verdicts = " ; ".join(f"« {x['rating_original'] or 'sans libellé'} » selon {x['source_name']}" for x in fact["reviews"])
        items.append(f"""<item><title>{escape(fact["person"]["name"] + " : « " + (fact["claim_text"] or "") + " »")}</title>
<link>{escape(r["url"])}</link><guid isPermaLink="false">{escape(fact["id"])}</guid><pubDate>{format_datetime(when)}</pubDate>
<description>{escape(verdicts)}</description></item>""")
    (site_dir / "flux.xml").write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Votona Observatoire - dernières vérifications</title><link>{SITE_URL}/</link>
<description>Les dernières déclarations politiques vérifiées par les rédactions françaises de fact-checking, avec le verdict d'origine.</description>
<language>fr</language><lastBuildDate>{format_datetime(generated)}</lastBuildDate>
{chr(10).join(items)}
</channel></rss>
""", encoding="utf-8")


if __name__ == "__main__":
    n = build()
    print(f"{OUTPUT.relative_to(ROOT)} et site/index.html : {n} déclarations embarquées")
