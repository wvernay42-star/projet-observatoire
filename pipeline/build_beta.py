"""Génère web/beta/index.html : le gabarit de la beta avec l'export embarqué.

    python -m pipeline.build_beta

Embarque data/export/facts.json, la liste des sources, les sujets de Votona et l'adresse de
contact. La page est publiée telle quelle (artefact) ; elle ne charge aucune donnée à distance.
La version site (site/, Vercel) ajoute les données ouvertes : donnees/facts.json, donnees/facts.csv
et flux.xml (RSS des dernières vérifications).
"""

import base64
import csv
import hashlib
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
# Logo sobre (loupe cochée, le pictogramme du lien « Observatoire » de votona.fr) : pas de
# mascotte sur l'Observatoire, dont le sujet (vérification des faits) demande un ton sérieux.
LOGO = Path(__file__).resolve().parents[1] / "web" / "beta" / "logo-mark.svg"
# Pas de personnages costumés en en-tête (voir LOGO) : réglage commun avec build_pages.
SHOW_CHARACTERS = build_pages.SHOW_CHARACTERS
# Accessoires des 7 familles de sujets, copiés de Votona (assets/props) : même identité visuelle.
PROPS_PLACEHOLDER = "/*__PROPS__*/{}"
PROPS_DIR = LOGO.with_name("props")
CHARS_DIR = LOGO.with_name("characters")
CHARS_PLACEHOLDER = "/*__CHARS__*/{}"
PORTRAITS_PLACEHOLDER = "/*__PORTRAITS__*/{}"
PORTRAITS_DIR = LOGO.with_name("portraits")
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
            chars = {f.stem: f"/assets/characters/{f.name}" for f in sorted(CHARS_DIR.glob("*.webp"))} if SHOW_CHARACTERS else {}
            portraits = {k: f"/assets/portraits/{k}.webp" for k in sorted(pages.portraits)}
        else:
            props = {f.stem: "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode()
                     for f in sorted(PROPS_DIR.glob("*.webp"))}
            chars = {}  # artefact : pas de personnages (poids), l'en-tête s'affiche sans
            portraits = {}  # ni de portraits : les initiales
        return (html.replace(PLACEHOLDER, payload).replace(LOGO_PLACEHOLDER, logo)
                .replace(PROPS_PLACEHOLDER, json.dumps(props)).replace(CHARS_PLACEHOLDER, json.dumps(chars))
                .replace(PORTRAITS_PLACEHOLDER, json.dumps(portraits)))

    # Artefact : logo embarqué (aucune ressource externe) ; site : fichier servi à côté de la page.
    output.write_text(page(False, "data:image/svg+xml;base64," + base64.b64encode(LOGO.read_bytes()).decode()), encoding="utf-8")
    build_site(page(True, "/assets/logo-mark.svg"), pages)
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
<script defer src="/_vercel/insights/script.js"></script>
<style>:root{color-scheme:light}body{margin:0;padding:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
"""


# Données structurées de l'accueil : le site et son éditeur (pas de ClaimReview : l'Observatoire ne produit aucun verdict).
HOME_LD = ('<script type="application/ld+json">' + json.dumps([
    {"@context": "https://schema.org", "@type": "WebSite", "name": "Votona Observatoire", "url": "__URL__/", "inLanguage": "fr-FR",
     "description": "Les vérifications des fact-checkers français sur les candidats à la présidentielle 2027 et la vie politique, avec le verdict d'origine."},
    {"@context": "https://schema.org", "@type": "Organization", "name": "Votona", "url": "https://votona.fr/",
     "sameAs": ["__URL__/"]},
    {"@context": "https://schema.org", "@type": "Dataset", "name": "Déclarations politiques vérifiées par les rédactions françaises",
     "description": "Base ouverte des vérifications de fact-checking rattachées aux personnalités politiques, avec le verdict d'origine, la date et le lien vers chaque article.",
     "url": "__URL__/methode/", "inLanguage": "fr-FR", "isAccessibleForFree": True,
     "creator": {"@type": "Organization", "name": "Votona", "url": "https://votona.fr/"},
     "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": "__URL__/donnees/facts.json"},
                      {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": "__URL__/donnees/facts.csv"}]}],
    ensure_ascii=False) + "</script>\n")


def externalize_app(body: str, site_dir: Path) -> str:
    """Sort le gros script de l'app (données embarquées) du HTML : fichier à nom empreinte, chargé en différé et mis en cache."""
    m = re.search(r"<script>([\s\S]*)</script>", body)
    if not m:
        return body
    code = m.group(1)
    name = f"app.{hashlib.sha256(code.encode()).hexdigest()[:10]}.js"
    for old in (site_dir / "assets").glob("app.*.js"):
        old.unlink()
    (site_dir / "assets" / name).write_text(code, encoding="utf-8")
    return body[:m.start()] + f'<script defer src="/assets/{name}"></script>' + body[m.end():]


def build_site(page: str, pages: "build_pages.Site | None" = None, site_dir: Path = SITE_DIR) -> None:
    """Version site (Vercel) : même page, document complet ; indexable seulement si build_pages.INDEXABLE."""
    (site_dir / "assets").mkdir(parents=True, exist_ok=True)
    # Le titre et les liens de polices du gabarit vont dans le <head> du document complet.
    head_tags = re.findall(r"^(?:<title>.*?</title>|<link [^>]*>)\s*$", page, flags=re.M)
    body = re.sub(r"^(?:<title>.*?</title>|<link [^>]*>|<meta name=\"claude:[^>]*>)\s*\n", "", page, flags=re.M)
    robots = "" if build_pages.INDEXABLE else '<meta name="robots" content="noindex, nofollow">\n'
    head = SITE_HEAD.replace("__ROBOTS__", robots).replace("</head>", "\n".join(head_tags) + "\n</head>")
    if pages is not None:
        body = externalize_app(body, site_dir)
        body = body.replace('<div class="wrap" id="nav"></div>', f'<div class="wrap" id="nav">{build_pages.home_nav()}</div>', 1)
        body = body.replace('<main class="wrap" id="app"></main>', f'<main class="wrap" id="app">{build_pages.home_prerender(pages)}</main>', 1)
        head = head.replace("</head>", HOME_LD.replace("__URL__", SITE_URL) + "</head>", 1)
    (site_dir / "index.html").write_text(head + body + "\n</body>\n</html>\n", encoding="utf-8")
    shutil.copyfile(LOGO, site_dir / "assets" / "logo-mark.svg")
    shutil.copyfile(LOGO.with_name("og.jpg"), site_dir / "assets" / "og.jpg")
    if (site_dir / "assets" / "og").exists():  # images de partage par page (scripts/og-images.js)
        shutil.rmtree(site_dir / "assets" / "og")
    if build_pages.OG_DIR.exists():
        shutil.copytree(build_pages.OG_DIR, site_dir / "assets" / "og")
    (site_dir / "assets" / "props").mkdir(exist_ok=True)
    for f in PROPS_DIR.glob("*.webp"):
        shutil.copyfile(f, site_dir / "assets" / "props" / f.name)
    if (site_dir / "assets" / "portraits").exists():
        shutil.rmtree(site_dir / "assets" / "portraits")
    (site_dir / "assets" / "portraits").mkdir(parents=True)  # portraits libres, seulement ceux qui sont affichés
    for key in sorted(build_pages.displayed_portraits()):
        shutil.copyfile(PORTRAITS_DIR / f"{key}.webp", site_dir / "assets" / "portraits" / f"{key}.webp")
    (site_dir / "assets" / "characters").mkdir(exist_ok=True)  # personnages de Votona (en-têtes)
    for f in CHARS_DIR.glob("*.webp"):
        shutil.copyfile(f, site_dir / "assets" / "characters" / f.name)
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
