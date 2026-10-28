"""Pages fixes du site : une page par candidat 2027, personnalité, parti et famille de sujets.

    python -m pipeline.build_pages        (lancé aussi par pipeline.build_beta)

L'app (site/index.html) reste l'explorateur à filtres ; ces pages donnent à chaque fiche une
adresse propre, lisible sans JavaScript (moteurs de recherche, aperçus de liens) :
    /candidats/<id Votona>/   /personnalites/<nom>/   /partis/<sigle>/   /sujets/<famille>/
    /candidats/  /personnalites/  /partis/  /sujets/  /methode/  et sitemap.xml
Même balisage et mêmes classes CSS que les vues de web/beta/template.html (feuille de style
extraite du gabarit dans site/assets/observatoire.css) : si une vue change, changer l'autre.
"""

import csv
import json
import re
import shutil
from collections import defaultdict
from datetime import date
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from unidecode import unidecode

from pipeline.connectors.base import SEEDS_DIR

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "web" / "beta" / "template.html"
SITE_URL = "https://observatoire.votona.fr"
VOTONA = "https://votona.fr"
CONTACT = "contact@votona.fr"
# Indexation ouverte le 28/10/2026 à la demande du porteur (conformité complète différée, docs/conformite.md).
INDEXABLE = True
SCOPE = "Sur les déclarations vérifiées, pas sur l'ensemble des propos tenus."

LEVELS = [("true", "Vrai", 0), ("mostly_true", "Plutôt vrai", 1), ("half_true", "À moitié vrai", 2),
          ("mostly_false", "Plutôt faux", 3), ("false", "Faux", 4), ("unrated", "Non classable", -1)]
LEVEL = {k: (label, idx) for k, label, idx in LEVELS}
FAMILIES = [("economie", "Économie & travail"), ("social", "Protection sociale"),
            ("securite", "Sécurité & immigration"), ("ecologie", "Écologie"),
            ("europe", "Europe & institutions"), ("societe", "Société"), ("defense", "Défense & numérique")]
FAMILY_ID = {label: fid for fid, label in FAMILIES}
FAMILY_LABEL = dict(FAMILIES)
# Couleur et accessoire de chaque famille : mêmes que Votona (CATEGORY_META.pop, assets/props).
THEME = {"economie": ("#FFB703", "economie"), "social": ("#3A86FF", "protection-sociale"),
         "securite": ("#FF6B6B", "securite"), "ecologie": ("#06D6A0", "ecologie"),
         "europe": ("#6C5CE7", "europe"), "societe": ("#FF5DA2", "societe"), "defense": ("#00B4D8", "defense")}
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]
MONTHS_SHORT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", unidecode(text).lower()).strip("-")[:60].strip("-") or "x"


def fr_date(iso: str | None, long: bool = False) -> str:
    """Même rendu que frDate() du gabarit (toLocaleDateString fr-FR)."""
    if not iso:
        return "date inconnue"
    parts = iso[:10].split("-")
    if len(parts) == 1:
        return parts[0]
    month = int(parts[1])
    if len(parts) == 2:
        return f"{MONTHS[month - 1]} {parts[0]}"
    return f"{int(parts[2])} {(MONTHS if long else MONTHS_SHORT)[month - 1]} {parts[0]}"


def initials_of(name: str) -> str:
    return "".join(w[0] for w in re.split(r"[\s-]+", name) if w)[:2].upper()


def plural(n: int, one: str, many: str) -> str:
    return f"{n} {many if n > 1 else one}"


@dataclass
class Site:
    """Données du site, préparées comme dans le gabarit (facts enrichis, personnes, partis, adresses)."""
    facts: list[dict[str, Any]]
    candidates: list[dict[str, str]]
    topics: list[dict[str, str]]
    sources: dict[str, str]
    generated_at: str
    persons: dict[str, str] = field(default_factory=dict)
    parties: dict[str, str] = field(default_factory=dict)
    candidate_by_pid: dict[str, dict[str, str]] = field(default_factory=dict)
    person_url: dict[str, str] = field(default_factory=dict)
    party_url: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, facts: list[dict[str, Any]], candidates: list[dict[str, str]], topics: list[dict[str, str]],
             sources: dict[str, str], generated_at: str) -> "Site":
        enriched = []
        for f in facts:
            rated = {r["rating_normalized"] for r in f["reviews"]} - {"unrated"}
            enriched.append({**f, "review_date": max((r["review_date"] or "" for r in f["reviews"]), default="") or None,
                             "family": FAMILY_ID.get(f.get("theme") or ""), "topics": f.get("votona_topics") or [],
                             "n_sources": len({r["source_id"] for r in f["reviews"]}), "diverge": len(rated) > 1})
        enriched.sort(key=lambda f: ((f["claim_date"] or "") + f["id"]), reverse=True)
        site = cls(enriched, [{**c, "pid": c["person_id"] or "votona:" + c["votona_id"]} for c in candidates],
                   topics, sources, generated_at)
        for f in enriched:  # du plus récent au plus ancien : un parti garde son nom le plus récent (RN, pas FN)
            site.persons[f["person"]["id"]] = f["person"]["name"]
            if f["party"]["id"]:
                site.parties.setdefault(f["party"]["id"], party_label(f["party"]))
        site.candidate_by_pid = {c["pid"]: c for c in site.candidates}
        for c in site.candidates:
            site.persons.setdefault(c["pid"], c["name"])
            site.person_url[c["pid"]] = f"/candidats/{c['votona_id']}/"
        used: set[str] = set()
        # Ordre fixe (nom, puis identifiant) : un homonyme reçoit toujours la même adresse d'un jour à l'autre.
        for pid in sorted(site.persons, key=lambda p: (site.persons[p], p)):
            if pid in site.person_url:
                continue
            slug = slugify(site.persons[pid])
            if slug in used:
                slug = f"{slug}-{slugify(pid)}"
            used.add(slug)
            site.person_url[pid] = f"/personnalites/{slug}/"
        used = set()
        short: dict[str, str] = {}  # sigle le plus récent : /partis/rn/, pas /partis/fn/
        for f in enriched:
            if f["party"]["id"]:
                short.setdefault(f["party"]["id"], f["party"]["short_name"] or f["party"]["name"])
        for pid in sorted(site.parties):
            slug = slugify(short[pid])
            if slug in used:
                slug = f"{slug}-{slugify(pid)}"
            used.add(slug)
            site.party_url[pid] = f"/partis/{slug}/"
        return site

    @property
    def candidate_parties(self) -> set[str]:
        return {c["party_id"] for c in self.candidates if c["party_id"]}

    def in_scope_2027(self, f: dict[str, Any]) -> bool:
        return f["person"]["id"] in self.candidate_by_pid or bool(f["party"]["id"] and f["party"]["id"] in self.candidate_parties)

    def of_person(self, pid: str) -> list[dict[str, Any]]:
        return [f for f in self.facts if f["person"]["id"] == pid]


# ---------- composants (mêmes classes que le gabarit) ----------

def counts(facts: list[dict[str, Any]]) -> dict[str, int]:
    return {k: sum(f["verdict"] == k for f in facts) for k, _, _ in LEVELS}


def summary(site: Site, facts: list[dict[str, Any]], note: str) -> str:
    n, c = len(facts), counts(facts)
    sources = sorted({r["source_id"] for f in facts for r in f["reviews"]}, key=lambda s: site.sources.get(s, s))
    last = max((f["review_date"] or "" for f in facts), default="")
    rows = "".join(
        f'<div class="bar-row" role="listitem"><span class="lab">{label}</span><div class="track"><div class="fill'
        f'{" unrated" if k == "unrated" else ""}" style="width:{(c[k] / n * 100) if n else 0:.1f}%'
        f'{"" if k == "unrated" else f";background:var(--v-{k})"}"></div></div><span class="num">{c[k]}'
        f'<span class="muted"> · {round(c[k] / n * 100) if n else 0} %</span></span></div>' for k, label, _ in LEVELS)
    return (f'<section class="summary"><div class="bars"><div><h2>{plural(n, "déclaration vérifiée", "déclarations vérifiées")}</h2>'
            f'<p class="scope-note">{escape(SCOPE + " " + note)}</p></div>'
            f'<div role="list" aria-label="Répartition par verdict">{rows}</div></div>'
            f'<aside class="side"><div><div class="k">Rédactions</div><div class="v">{len(sources)}</div>'
            f'<div class="small muted">{escape(" · ".join(site.sources.get(s, s) for s in sources)) or "—"}</div></div>'
            f'<div><div class="k">Vérifiées par plusieurs rédactions</div><div class="v">{sum(f["n_sources"] > 1 for f in facts)}</div></div>'
            f'<div><div class="k">Vérification la plus récente</div><div class="v" style="font-size:18px">{fr_date(last, True) if last else "—"}</div></div>'
            f'</aside></section>')


def mini_bar(facts: list[dict[str, Any]]) -> str:
    n, c = len(facts), counts(facts)
    label = ", ".join(f"{c[k]} {lab.lower()}" for k, lab, _ in LEVELS if c[k]) or "aucune vérification"
    spans = "".join(f'<span{" class=\"unrated\"" if k == "unrated" else ""} style="width:{c[k] / n * 100:.1f}%'
                    f'{"" if k == "unrated" else f";background:var(--v-{k})"}"></span>' for k, _, _ in LEVELS if c[k])
    return f'<div class="mini" role="img" aria-label="{escape(label)}">{spans}</div>'


def meter(k: str) -> str:
    i = LEVEL.get(k, ("", -1))[1]
    return '<div class="meter" aria-hidden="true">' + "".join(
        f'<span style="background:var(--v-{k})"></span>' if x == i else "<span></span>" for x in range(5)) + "</div>"


def party_label(p: dict[str, Any]) -> str:
    return f"{p['name']} ({p['short_name']})" if p["short_name"] else p["name"]


def party_text(f: dict[str, Any]) -> str:
    if f["party"]["id"]:
        return f["party"]["short_name"] or f["party"]["name"]
    return "sans étiquette" if f["party"]["status"] == "no_party" else "parti non renseigné"


def ext(url: str, text: str) -> str:
    return f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(text)}</a>'


def dates_line(f: dict[str, Any]) -> str:
    fb = (' class="fallback" title="Date de déclaration non fournie par la source : date de vérification utilisée"'
          if f["date_is_fallback"] else "")
    return f'<div class="dates">Déclaration : <span{fb}>{fr_date(f["claim_date"])}</span> · Vérification : {fr_date(f["review_date"])}</div>'


def fact_chips(f: dict[str, Any]) -> str:
    chips = []
    if f["n_sources"] > 1:
        chips.append(f'<span class="chip multi">Vérifié par {f["n_sources"]} rédactions</span>')
    if f["diverge"]:
        chips.append('<span class="chip diverge" title="Les rédactions ne placent pas cette déclaration au même niveau : '
                     'chaque verdict est affiché.">Verdicts divergents</span>')
    if f["family"]:
        chips.append(f'<a class="chip" href="/sujets/{f["family"]}/" title="Thème attribué automatiquement, à titre indicatif">'
                     f'{escape(FAMILY_LABEL[f["family"]])}</a>')
    if f["topics"]:
        t = f["topics"][0]
        chips.append(f'<a class="chip votona" href="{VOTONA}/sujets/{t["slug"]}/" title="{escape(t["label"])}">'
                     f'Positions des candidats sur Votona</a>')
    return f'<div class="tags">{"".join(chips)}</div>'


def fact_row(site: Site, f: dict[str, Any], with_person: bool = True) -> str:
    who = (f'<div class="who"><a class="linkish" href="{site.person_url[f["person"]["id"]]}">{escape(f["person"]["name"])}</a> '
           f'<span class="muted">· {escape(party_text(f))} à cette date</span></div>' if with_person
           else f'<div class="who muted">{escape(party_text(f))} à cette date</div>')
    reads = " · ".join(ext(r["url"], "Lire sur " + r["source_name"]) for r in f["reviews"])
    report = (f'<details class="report-d"><summary>Signaler une erreur</summary><div class="report">Écrivez à '
              f'<strong>{CONTACT}</strong> en indiquant la référence <code>{escape(f["id"])}</code>. '
              f'Une attribution contestée à raison est retirée sous 48 h.</div></details>')
    verdicts = "".join(
        f'<div class="verdict"><strong>{LEVEL.get(r["rating_normalized"], (r["rating_normalized"],))[0]}</strong>'
        f'<span class="muted"> — « {escape(r["rating_original"] or "sans libellé")} » selon {ext(r["url"], r["source_name"])}</span></div>'
        for r in f["reviews"])
    return (f'<article class="fact"><div style="display:flex;flex-direction:column;gap:6px;min-width:0">{who}'
            f'<p class="claim">« {escape(f["claim_text"] or "")} »</p>{dates_line(f)}{fact_chips(f)}'
            f'<div class="small">{reads} · {report}</div></div>'
            f'<div class="right">{meter(f["verdict"])}<strong>{LEVEL[f["verdict"]][0]}</strong>{verdicts}</div></article>')


def fact_list(site: Site, facts: list[dict[str, Any]], with_person: bool = True) -> str:
    rows = "".join(fact_row(site, f, with_person) for f in facts)
    return f'<section class="facts">{rows or "<p class=\"muted\">Aucune déclaration vérifiée.</p>"}</section>'


def prop_img(fid: str, cls: str = "prop") -> str:
    return f'<img class="{cls}" src="/assets/props/{THEME[fid][1]}.webp" alt="" width="44" height="44" loading="lazy">'


def family_tiles(facts: list[dict[str, Any]]) -> str:
    tiles = []
    for fid, label in FAMILIES:
        sub = [f for f in facts if f["family"] == fid]
        count = plural(len(sub), "déclaration vérifiée", "déclarations vérifiées") if sub else "Aucune vérification"
        tiles.append(f'<a class="tile theme" style="--th:{THEME[fid][0]}" href="/sujets/{fid}/">{prop_img(fid)}'
                     f'<span class="t">{escape(label)}</span><span class="c">{count}</span>{mini_bar(sub)}</a>')
    return f'<div class="tiles">{"".join(tiles)}</div>'


def intro(title: str, text: str = "") -> str:
    return f'<div><h1>{escape(title)}</h1>{f"<p class=\"muted lede\">{escape(text)}</p>" if text else ""}</div>'


def crumbs(*links: tuple[str, str]) -> str:
    return '<nav class="crumbs" aria-label="Fil d\'Ariane">' + "".join(
        f'<a href="{href}">{escape(label)}</a>' for href, label in links) + "</nav>"


# ---------- pages ----------

ICON_TEST = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="2"/>'
             '<path d="M9 8h6M9 12h6M9 16h3"/></svg>')
ICON_FAQ = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
            '<path d="M9.3 9.2a2.7 2.7 0 1 1 3.9 2.4c-1 .5-1.7 1.1-1.7 2.4"/><line x1="12" y1="17.2" x2="12" y2="17.21"/></svg>')
ICON_USER = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg>')
# Le compte est celui de Votona (même base Supabase) : l'icône mène à « Mon compte » sur votona.fr.
TABS = [("accueil", "/", "Accueil"), ("faits", "/#faits", "Faits"), ("personnalites", "/candidats/", "Personnalités"),
        ("partis", "/partis/", "Partis"), ("sujets", "/sujets/", "Sujets")]


def social_html() -> str:
    """Réseaux de Votona : même bloc que le pied de page du gabarit."""
    m = re.search(r"const SOCIAL_HTML = '(.*?)';\n", TEMPLATE.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def page(site: Site, path: str, title: str, description: str, tab: str, body: str,
         indexable: bool = True, ld: list[dict[str, Any]] | None = None) -> str:
    robots = "" if INDEXABLE and indexable else '<meta name="robots" content="noindex, nofollow">\n'
    nav = "".join(f'<a href="{href}"{" aria-current=\"page\"" if key == tab else ""}>'
                  f'{label}{"<span class=\"lg\"> vérifiés</span>" if key == "faits" else ""}</a>' for key, href, label in TABS)
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in ld or [])
    url = SITE_URL + path
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
{robots}<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Votona Observatoire">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}/assets/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/favicon-48.png">
<link rel="alternate" type="application/rss+xml" title="Votona Observatoire - dernières vérifications" href="/flux.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Work+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/observatoire.css">
<script defer src="/_vercel/insights/script.js"></script>
{ld_html}</head>
<body>
<div class="masthead">
<header class="topbar">
  <a class="brand" href="/" title="Accueil de l'Observatoire"><span class="mark"><img src="/assets/logo-head.webp" alt="" width="40" height="32"></span><span class="name">Votona</span><span class="year">OBSERVATOIRE</span><span class="beta-tag" title="Version bêta : mise à jour chaque jour, rattachements partisans encore incomplets">BÊTA</span></a>
  <div class="topbar-actions">
    <a class="sister-link" href="{VOTONA}/" title="Votona : le test présidentielle 2027, quel candidat te correspond ?">{ICON_TEST}<span>Le test 2027</span></a>
    <a class="icon-btn" href="{VOTONA}/?screen=account" title="Mon compte (Votona)" aria-label="Mon compte (Votona)">{ICON_USER}</a>
    <a class="icon-btn" href="/methode/" title="Méthode et FAQ" aria-label="Méthode et FAQ"{' aria-current="page"' if tab == "methode" else ""}>{ICON_FAQ}</a>
  </div>
</header>
<nav class="subnav" aria-label="Navigation de l'Observatoire"><div class="wrap">{nav}</div></nav>
</div>
<main class="wrap">
{body}
<footer class="gfoot">Votona Observatoire ne produit aucun verdict : il reprend celui de la rédaction, avec un lien vers l'article. Version bêta, mise à jour chaque jour ({fr_date(site.generated_at, True)}).
<div class="flinks"><a href="/methode/">Méthode</a> · <a href="/vous-etes-cite/">Vous êtes cité ?</a> · <a href="/donnees/facts.csv">Données ouvertes</a> · <a href="/flux.xml">Flux RSS</a> · <a href="{VOTONA}/a-propos/">À propos</a> · <a href="{VOTONA}/mentions-legales/">Mentions légales</a> · <a href="{VOTONA}/confidentialite/">Confidentialité</a> · <a href="{VOTONA}/contact/">Contact</a></div>
<div class="social">{social_html()}</div>
</footer>
</main>
</body>
</html>
"""


def breadcrumb_ld(*items: tuple[str, str]) -> dict[str, Any]:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": name, "item": SITE_URL + path} for i, (path, name) in enumerate(items)]}


def person_page(site: Site, pid: str) -> tuple[str, str, bool]:
    path, name, cand = site.person_url[pid], site.persons[pid], site.candidate_by_pid.get(pid)
    facts = site.of_person(pid)
    initials = initials_of(name)
    party_names = list(dict.fromkeys(party_label(f["party"]) for f in reversed(facts) if f["party"]["id"]))
    party_line = ("Partis sur la période : " + ", ".join(party_names) if party_names
                  else f'{cand["votona_party"]} (selon Votona)' if cand else "Parti non renseigné sur la période")
    wiki = f' · {ext("https://www.wikidata.org/wiki/" + pid, "fiche Wikidata")}' if pid.startswith("Q") else ""
    badge = ""
    if cand:
        status = "Candidature 2027 retirée" if cand["status"] == "retiré" else "Présidentielle 2027"
        badge = (f'<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:8px;align-items:center"><span class="badge">{status}</span>'
                 f'<a href="{escape(cand["votona_url"])}">Ses positions sur Votona</a></div>')
    parts = [crumbs(("/candidats/", "Candidats 2027") if cand else ("/personnalites/", "Personnalités")),
             (f'<div class="head cc" style="--cc:{escape(cand.get("color") or "#7C3AED")}"><div class="avatar cc" aria-hidden="true">' if cand
              else '<div class="head"><div class="avatar" aria-hidden="true">') + f'{escape(initials)}</div><div style="min-width:0">'
             f'<h1>{escape(name)}</h1>{badge}<p class="muted" style="margin:4px 0 0">{escape(party_line)}{wiki}</p></div></div>']
    if facts:
        parts.append(summary(site, facts, "Toute la période."))
        fams = [(fid, label) for fid, label in FAMILIES if any(f["family"] == fid for f in facts)]
        if fams:
            parts.append('<div class="tags"><span class="small muted">Sujets vérifiés :</span>' + "".join(
                f'<a class="chip" href="/sujets/{fid}/">{escape(label)} · {sum(f["family"] == fid for f in facts)}</a>'
                for fid, label in fams) + "</div>")
        dated = sorted(f["claim_date"] for f in facts if f["claim_date"])
        if len(dated) > 1:
            def day(d: str) -> int:
                y, m, dd = (d.split("-") + ["15", "15"])[:3]
                return date(int(y), int(m), int(dd)).toordinal()
            t0, t1 = day(dated[0]), day(dated[-1])
            dots = "".join(
                f'<span class="{"unrated" if f["verdict"] == "unrated" else ""}" title="{fr_date(f["claim_date"])} — {LEVEL[f["verdict"]][0]}" '
                f'style="left:{50 if t0 == t1 else 2 + (day(f["claim_date"]) - t0) / (t1 - t0) * 96:.1f}%'
                f'{"" if f["verdict"] == "unrated" else ";background:var(--v-" + f["verdict"] + ")"}"></span>'
                for f in facts if f["claim_date"])
            parts.append(f'<section aria-label="Frise des vérifications" class="sect"><h2>Dans le temps</h2><div class="timeline">{dots}</div>'
                         f'<div class="axis"><span>{fr_date(dated[0])}</span><span>{fr_date(dated[-1])}</span></div></section>')
        parts.append(f'<section class="sect"><h2>Les {len(facts)} faits</h2>{fact_list(site, facts, False)}</section>')
    else:
        parts.append('<p class="notice">Aucune vérification publiée à ce jour par les rédactions suivies. Cela ne dit rien de '
                     "l'exactitude de ses propos : les rédactions choisissent ce qu'elles vérifient.</p>")
    if cand:
        parts.append(f'<a class="btn btn-ghost btn-row" href="{escape(cand["votona_url"])}">Voir ses positions sur Votona, sujet par sujet</a>')
    n = len(facts)
    title = f"{name} : déclarations vérifiées par les fact-checkers - Votona Observatoire"
    desc = (f"{plural(n, 'déclaration', 'déclarations')} de {name} vérifiée{'s' if n > 1 else ''} par les rédactions françaises "
            f"de fact-checking, avec le verdict d'origine et le lien vers chaque article." if n else
            f"{name} : aucune déclaration vérifiée à ce jour par les rédactions françaises de fact-checking suivies.")
    ld = [breadcrumb_ld(("/", "Observatoire"), ("/candidats/" if cand else "/personnalites/", "Candidats 2027" if cand else "Personnalités"), (path, name))]
    return path, page(site, path, title, desc, "personnalites", "\n".join(parts), indexable=bool(facts), ld=ld), bool(facts)


def party_page(site: Site, party_id: str) -> tuple[str, str]:
    path, name = site.party_url[party_id], site.parties[party_id]
    facts = [f for f in site.facts if f["party"]["id"] == party_id]
    by_person: dict[str, list] = defaultdict(list)
    for f in facts:
        by_person[f["person"]["id"]].append(f)
    cands = [c for c in site.candidates if c["party_id"] == party_id]
    rows = "".join(
        f'<tr><td><a class="linkish" href="{site.person_url[pid]}">{escape(site.persons[pid])}</a></td><td class="num">{len(fs)}</td>'
        + "".join(f'<td class="num">{sum(f["verdict"] == k for f in fs)}</td>' for k, _, _ in LEVELS) + "</tr>"
        for pid, fs in sorted(by_person.items(), key=lambda x: site.persons[x[0]]))
    head = "".join(f"<th>{h}</th>" for h in ["Personne", "Vérifications", *(label for _, label, _ in LEVELS)])
    cand_note = ('<p class="notice">Candidat 2027 : ' + ", ".join(
        f'<a class="linkish" href="{site.person_url[c["pid"]]}">{escape(c["name"])}</a> '
        f'(<a href="{escape(c["votona_url"])}">positions sur Votona</a>)' for c in cands) + "</p>") if cands else ""
    body = "\n".join([
        crumbs(("/partis/", "Partis")),
        intro(name, "Déclarations de personnes affiliées à ce parti à la date où elles ont été faites. La couverture dépend des "
                    "rédactions et des affiliations connues : elle ne représente pas l'ensemble du parti."),
        cand_note, summary(site, facts, "Toute la période."),
        f'<section class="sect"><h2>Par personne</h2><div class="table-box"><table class="plain"><thead><tr>{head}</tr></thead>'
        f"<tbody>{rows}</tbody></table></div></section>",
        f'<section class="sect"><h2>Les {len(facts)} faits</h2>{fact_list(site, facts)}</section>'])
    title = f"{name} : déclarations vérifiées de ses membres - Votona Observatoire"
    desc = (f"{plural(len(facts), 'déclaration', 'déclarations')} de membres de {name}, vérifiée{'s' if len(facts) > 1 else ''} par "
            "les rédactions françaises de fact-checking, avec le parti à la date de chaque déclaration.")
    return path, page(site, path, title, desc, "partis", body, ld=[breadcrumb_ld(("/", "Observatoire"), ("/partis/", "Partis"), (path, name))])


def family_page(site: Site, fid: str) -> tuple[str, str]:
    path, label = f"/sujets/{fid}/", FAMILY_LABEL[fid]
    facts = [f for f in site.facts if f["family"] == fid]
    scoped = [f for f in facts if site.in_scope_2027(f)]
    topics = sorted(({**t, "n": sum(any(x["slug"] == t["slug"] for x in f["topics"]) for f in facts)}
                     for t in site.topics if FAMILY_ID.get(t["category"]) == fid), key=lambda t: (-t["n"], t["label"]))
    topic_rows = "".join(
        f'<div class="topic{"" if t["n"] else " blind"}"><div><div>{escape(t["label"])}</div><div class="small">'
        f'<a href="{VOTONA}/sujets/{t["slug"]}/">Que proposent les candidats ? (Votona)</a></div></div>'
        f'<span class="n2">{str(t["n"]) + " vérif." if t["n"] else "aucune vérification"}</span></div>' for t in topics)
    body = "\n".join([
        crumbs(("/sujets/", "Sujets")),
        f'<div class="theme-hero" style="--th:{THEME[fid][0]}">{prop_img(fid)}<div class="theme-pill">Sujet · '
        f'{plural(len(facts), "déclaration vérifiée", "déclarations vérifiées")}</div><h1>{escape(label)}</h1>'
        f'<p class="muted" style="margin:8px 0 0">Thème attribué automatiquement, à titre indicatif. {len(scoped)} de ces '
        f"déclarations viennent des candidats 2027 ou de leurs partis.</p></div>",
        summary(site, facts, "Toute la vie politique, toute la période."),
        f'<section class="sect"><h2>Les sujets du test Votona</h2><div class="topics">{topic_rows}</div></section>',
        f'<section class="sect"><h2>Les {len(facts)} faits</h2>{fact_list(site, facts)}</section>'])
    title = f"{label} : les déclarations politiques vérifiées - Votona Observatoire"
    desc = (f"{label} : {plural(len(facts), 'déclaration politique vérifiée', 'déclarations politiques vérifiées')} par les rédactions "
            "françaises de fact-checking, reliées aux sujets du test présidentielle 2027 de Votona.")
    return path, page(site, path, title, desc, "sujets", body, ld=[breadcrumb_ld(("/", "Observatoire"), ("/sujets/", "Sujets"), (path, label))])


def people_tabs(active: str) -> str:
    return ('<div class="tabs" role="tablist">'
            f'<a href="/candidats/" role="tab" aria-selected="{str(active == "candidats").lower()}">Candidats 2027</a>'
            f'<a href="/personnalites/" role="tab" aria-selected="{str(active == "toutes").lower()}">Toutes les personnalités</a></div>')


PEOPLE_INTRO = ("Aucun classement : le nombre de vérifications dépend des choix des rédactions, pas de la sincérité des personnes. "
                "L'absence de vérification ne dit rien de l'exactitude des propos.")


def index_pages(site: Site) -> dict[str, str]:
    pages = {}
    # Candidats 2027 : ordre alphabétique du nom de famille (identifiant Votona), retraits en fin de liste.
    cards = []
    for c in sorted(site.candidates, key=lambda c: (c["status"] == "retiré", c["votona_id"])):
        facts = site.of_person(c["pid"])
        initials = initials_of(c["name"])
        cards.append(f'<article class="cand cc{" withdrawn" if c["status"] == "retiré" else ""}" style="--cc:{escape(c.get("color") or "#7C3AED")}"><div class="top">'
                     f'<span class="nm"><span class="av" aria-hidden="true">{escape(initials)}</span>'
                     f'<a class="linkish" href="{site.person_url[c["pid"]]}">{escape(c["name"])}</a></span>'
                     f'<span class="cnt">{f"{len(facts)} vérif." if facts else "—"}</span></div>'
                     f'<div class="small muted">{escape(c["votona_party"])}{" · candidature retirée" if c["status"] == "retiré" else ""}</div>'
                     f'{mini_bar(facts) if facts else ""}<div class="small"><a href="{escape(c["votona_url"])}">Ses positions sur Votona</a></div></article>')
    pages["/candidats/"] = page(site, "/candidats/", "Candidats à la présidentielle 2027 : déclarations vérifiées - Votona Observatoire",
                                "Les déclarations des candidats à la présidentielle 2027 vérifiées par les rédactions françaises de fact-checking, candidat par candidat.",
                                "personnalites", "\n".join([intro("Personnalités", PEOPLE_INTRO), people_tabs("candidats"),
                                f'<div class="cands">{"".join(cards)}</div>',
                                '<p class="small muted">La même liste que sur Votona. Les vérifications ne comptent jamais dans le classement de Votona : les deux outils sont séparés.</p>']))
    by_person: dict[str, int] = defaultdict(int)
    for f in site.facts:
        by_person[f["person"]["id"]] += 1
    links = "".join(f'<a href="{site.person_url[pid]}"><span class="n1">{escape(site.persons[pid])}{" · 2027" if pid in site.candidate_by_pid else ""}</span>'
                    f'<span class="n2">{n} vérif.</span></a>' for pid, n in sorted(by_person.items(), key=lambda x: site.persons[x[0]]))
    pages["/personnalites/"] = page(site, "/personnalites/", "Personnalités politiques : déclarations vérifiées - Votona Observatoire",
                                    "Toutes les personnalités politiques françaises dont une déclaration a été vérifiée par les rédactions de fact-checking.",
                                    "personnalites", "\n".join([intro("Personnalités", PEOPLE_INTRO), people_tabs("toutes"),
                                    f'<p class="small muted" style="margin:0">{plural(len(by_person), "personnalité", "personnalités")} avec au moins une vérification, par ordre alphabétique.</p>',
                                    f'<div class="people">{links}</div>']))
    by_party: dict[str, list] = defaultdict(list)
    for f in site.facts:
        if f["party"]["id"]:
            by_party[f["party"]["id"]].append(f)
    unknown = sum(not f["party"]["id"] for f in site.facts)

    def block(title: str, ids: list[str]) -> str:
        if not ids:
            return ""
        tiles = []
        for pid in ids:
            cands = [c["name"] for c in site.candidates if c["party_id"] == pid and c["status"] != "retiré"]
            tiles.append(f'<a class="tile" href="{site.party_url[pid]}"><span class="t">{escape(site.parties[pid])}</span>'
                         f'<span class="c">{plural(len(by_party[pid]), "déclaration vérifiée", "déclarations vérifiées")}'
                         f'{" · candidat : " + escape(", ".join(cands)) if cands else ""}</span>{mini_bar(by_party[pid])}</a>')
        return f'<section class="sect"><h2>{title}</h2><div class="tiles">{"".join(tiles)}</div></section>'
    ids = sorted(by_party, key=lambda p: site.parties[p])
    cp = site.candidate_parties
    pages["/partis/"] = page(site, "/partis/", "Partis politiques : déclarations vérifiées de leurs membres - Votona Observatoire",
                             "Les déclarations des membres de chaque parti, vérifiées par les rédactions françaises de fact-checking, selon le parti à la date de la déclaration.",
                             "partis", "\n".join([intro("Partis", "Parti en vigueur à la date de chaque déclaration, d'après des affiliations publiques et datées. "
                                                        + plural(unknown, "déclaration n'a", "déclarations n'ont") + " pas encore de parti renseigné et ne "
                                                        + ("sont comptées" if unknown > 1 else "est comptée") + " dans aucun parti."),
                                                  block("Partis des candidats 2027", [p for p in ids if p in cp]),
                                                  block("Autres partis", [p for p in ids if p not in cp])]))
    scoped = [f for f in site.facts if site.in_scope_2027(f)]
    blind = [t for t in site.topics if not any(any(x["slug"] == t["slug"] for x in f["topics"]) for f in scoped)]
    pages["/sujets/"] = page(site, "/sujets/", "Sujets : les déclarations politiques vérifiées par thème - Votona Observatoire",
                             "Les déclarations politiques vérifiées, classées selon les 7 familles et les sujets du test présidentielle 2027 de Votona, avec les angles morts.",
                             "sujets", "\n".join([
                                 intro("Sujets", f"Les déclarations vérifiées classées selon les 7 familles et les {len(site.topics)} sujets du test Votona. "
                                                 "Le thème est attribué automatiquement à partir de la déclaration et du titre de l'article : il est indicatif et ne qualifie jamais le propos."),
                                 family_tiles(site.facts),
                                 '<section class="sect"><h2>Angles morts</h2>'
                                 f'<p class="muted" style="margin:0">{len(blind)} sujets du test Votona sur {len(site.topics)} n\'ont aucune déclaration vérifiée '
                                 "des candidats 2027 ou de leurs partis. Les candidats en parlent dans leurs programmes, les rédactions ne les ont pas (encore) vérifiés sur ces points.</p>"
                                 '<div class="tags">' + "".join(f'<a class="chip" href="{VOTONA}/sujets/{t["slug"]}/">{escape(t["label"])}</a>' for t in blind)
                                 + "</div></section>"]))
    return pages


def methode_page(site: Site) -> str:
    """Page Méthode : même texte que la vue « methodologie » du gabarit, extrait du rendu de l'app."""
    used = sorted({r["source_id"] for f in site.facts for r in f["reviews"]}, key=lambda s: site.sources.get(s, s))
    rows = "".join(f'<tr><td>{escape(site.sources.get(s, s))}</td><td class="num">{sum(any(r["source_id"] == s for r in f["reviews"]) for f in site.facts)}</td></tr>' for s in used)
    scale = [("true", "Vrai, Correct"), ("mostly_true", "Plutôt vrai"), ("half_true", "À moitié vrai, Imprécis, En partie vrai"),
             ("mostly_false", "Plutôt faux, Trompeur, Exagéré"), ("false", "Faux, Inventé"), ("unrated", "Manque de contexte, Montage, Invérifiable")]
    sw = lambda k: ('<span class="sw unrated" aria-hidden="true"></span>' if k == "unrated"
                    else f'<span class="sw" style="background: var(--v-{k})" aria-hidden="true"></span>')
    scale_rows = "".join(f"<tr><td>{sw(k)} {LEVEL[k][0]}</td><td>{ex}</td></tr>" for k, ex in scale)
    body = f"""<div class="prose">
<nav class="mtabs" aria-label="Méthodes de Votona"><a href="{VOTONA}/methode/">Le test Votona</a><a href="/methode/" aria-current="page">L'Observatoire</a></nav>
<section class="mhero"><img src="/assets/logo-head.webp" alt="" width="104" height="83"><div><h1>Méthode de l'Observatoire</h1><p>D'où viennent les vérifications, comment elles sont rattachées aux personnalités et aux partis, et ce que l'Observatoire ne fait jamais.</p></div></section>
<nav class="mtoc" aria-label="Sommaire"><a href="#principes">Principes</a><a href="#recoupement">Recoupement et divergences</a><a href="#sujets">Sujets</a><a href="#votona">Votona et l'Observatoire</a><a href="#redactions">Rédactions suivies</a><a href="#echelle">Échelle commune</a><a href="#donnees">Données ouvertes</a><a href="#limites">Limites de la version bêta</a><a href="#droits">Contester une entrée, vos droits</a></nav>
<p>L'Observatoire ne produit aucun verdict. Il recense des vérifications publiées par des rédactions de fact-checking, les rattache à des personnalités politiques identifiées et les rend consultables par période, parti, personne, sujet, verdict et rédaction.</p>
<h2 id="principes">Principes</h2>
<ul>
<li>Le verdict affiché est celui de la source, avec son libellé d'origine toujours visible.</li>
<li>Chaque entrée donne le lien vers l'article, la date de la déclaration, la date de la vérification et le nom de la rédaction.</li>
<li>Un verdict qui ne se place pas sur l'axe vrai/faux est classé « non classable », jamais forcé.</li>
<li>{SCOPE} Les rédactions choisissent ce qu'elles vérifient, souvent des propos qui suscitent un doute : ces chiffres ne mesurent pas la sincérité d'une personne.</li>
<li>Le parti indiqué est celui en vigueur à la date de la déclaration, d'après des affiliations publiques et datées. Faute de date fiable, le parti n'est pas indiqué. Un parti qui a changé de nom est affiché sous son nom actuel (Rassemblement national pour l'ancien Front national, Renaissance pour La République en marche) ; le nom à la date figure dans les données ouvertes.</li>
<li>Seules des métadonnées sont reprises (titre, verdict, dates, lien), jamais le contenu des articles.</li>
<li>Toute attribution incertaine est vérifiée à la main avant publication. Aucun classement des personnalités n'est proposé.</li>
</ul>
<h2 id="recoupement">Recoupement et divergences</h2>
<p>Quand plusieurs rédactions vérifient la même déclaration, toutes les vérifications sont affichées, avec la mention « Vérifié par N rédactions ». Le compteur retient le verdict le plus fréquent, et « non classable » en cas d'égalité. Si les rédactions placent la déclaration à des niveaux différents, la mention « Verdicts divergents » le signale : l'Observatoire ne tranche pas.</p>
<h2 id="sujets">Sujets</h2>
<p>Chaque déclaration est rangée, si possible, dans l'une des 7 familles et l'un des sujets du test Votona, à partir de mots-clés lus dans la déclaration et le titre de l'article. Ce classement automatique est indicatif ; il sert à relier un fait aux positions des candidats sur Votona, et à repérer les sujets que personne n'a vérifiés (angles morts).</p>
<h2 id="votona">Votona et l'Observatoire</h2>
<p>Votona compare vos positions à celles des candidats ; l'Observatoire recense ce que les rédactions de fact-checking ont vérifié. Les deux outils partagent la liste des candidats et les sujets, mais <strong>les vérifications n'entrent jamais dans le classement de Votona</strong>, et l'Observatoire n'interprète aucune position.</p>
<h2 id="redactions">Rédactions suivies</h2>
<div class="table-box"><table class="plain"><thead><tr><th>Rédaction</th><th>Déclarations dans la base</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="small muted">Collecte : API Google Fact Check Tools (vérifications déclarées par les rédactions) et flux ClaimReview de Data Commons (licence CC BY). Personnalités et affiliations : Wikidata.</p>
<h2 id="echelle">Échelle commune</h2>
<div class="table-box"><table class="plain"><thead><tr><th>Niveau</th><th>Exemples de libellés d'origine</th></tr></thead><tbody>{scale_rows}</tbody></table></div>
<h2 id="donnees">Données ouvertes</h2>
<p>Toute la base publiée est téléchargeable et réutilisable en citant l'Observatoire et chaque rédaction : <a href="/donnees/facts.json">JSON</a>, <a href="/donnees/facts.csv">CSV</a> et <a href="/flux.xml">flux RSS des dernières vérifications</a>. Métadonnées seulement : pour lire une vérification, suivez le lien vers la rédaction.</p>
<h2 id="limites">Limites de la version bêta</h2>
<ul>
<li>Périmètre : France ; personnalités ayant exercé une fonction publique depuis 2017, et tous les candidats 2027 de la liste Votona.</li>
<li>Certains libellés intermédiaires sont classés « non classable » en attendant leur validation.</li>
<li>Les affiliations partisanes de Wikidata sont souvent non datées : beaucoup de déclarations n'ont pas encore de parti indiqué.</li>
<li>Le thème est attribué par mots-clés : certaines déclarations restent sans sujet.</li>
</ul>
<h2 id="droits">Contester une entrée, vos droits</h2>
<p>Pour signaler une erreur, demander une rectification ou vous opposer au traitement de données vous concernant, écrivez à <strong>{CONTACT}</strong> en indiquant la référence de l'entrée (lien « Signaler une erreur »). Une attribution contestée à raison est retirée sous 48 heures. Personnalité citée : voir <a href="/vous-etes-cite/">Vous êtes cité ?</a></p>
<p class="small muted">Données mises à jour le {fr_date(site.generated_at, True)}.</p>
</div>"""
    return page(site, "/methode/", "Méthode de l'Observatoire - Votona Observatoire",
                "Comment Votona Observatoire recense les vérifications des fact-checkers : verdict d'origine, parti à la date, recoupement, sujets, données ouvertes.",
                "methode", body)


def cited_page(site: Site) -> str:
    """« Vous êtes cité ? » : information des personnes citées et procédure (RGPD, cadrage « Conformité »)."""
    body = f"""<div class="prose">
<h1>Vous êtes cité ?</h1>
<p class="muted lede">Votona Observatoire rassemble des vérifications publiées par des rédactions de fact-checking sur des déclarations publiques de personnalités politiques. Voici quelles données vous concernant sont traitées, d'où elles viennent, et comment demander une correction ou vous opposer.</p>
<h2>Ce que l'Observatoire publie</h2>
<ul>
<li>Votre nom et, s'il est connu, le parti auquel vous étiez affilié à la date de la déclaration, d'après des affiliations publiques et datées.</li>
<li>La déclaration telle que la rédaction l'a formulée, le verdict de la rédaction avec son libellé d'origine, les dates et le lien vers l'article.</li>
<li>Rien d'autre : aucun verdict propre à l'Observatoire, aucun classement des personnalités, jamais le contenu des articles.</li>
</ul>
<h2>D'où viennent ces données</h2>
<p>Des rédactions de fact-checking, via l'API Google Fact Check Tools et le flux ClaimReview de Data Commons ; de Wikidata pour les fonctions et les affiliations ; de la liste des candidats de <a href="{VOTONA}/">Votona</a>. Toute attribution incertaine (homonyme, nom incomplet) est vérifiée à la main avant d'être publiée.</p>
<h2>Pourquoi, et sur quelle base</h2>
<p>Pour informer le public sur la vérification des propos politiques, en réunissant ce que les rédactions ont publié. Le traitement repose sur l'intérêt légitime d'information du public sur la vie politique (article 6.1.f du RGPD), dans le cadre de la liberté d'expression et d'information. L'affiliation partisane n'est reprise que lorsqu'elle a été rendue publique par la personne elle-même (article 9.2.e du RGPD).</p>
<h2>Vos droits</h2>
<p>Vous pouvez demander l'accès à ces données, leur rectification, leur effacement ou la limitation de leur traitement, et vous opposer à leur traitement (article 21 du RGPD). Écrivez à <strong>{CONTACT}</strong> en indiquant la référence de l'entrée (lien « Signaler une erreur » sous chaque déclaration) ou l'adresse de votre fiche.</p>
<ul>
<li><strong>Attribution erronée</strong> (la déclaration n'est pas de vous, ou le parti indiqué est faux) : l'entrée est retirée ou corrigée sous 48 heures si la demande est fondée.</li>
<li><strong>Désaccord avec un verdict</strong> : l'Observatoire reprend le verdict de la rédaction sans le modifier ; adressez-vous à la rédaction concernée (lien sur chaque entrée). Si elle corrige son article, la correction est reprise à la mise à jour suivante.</li>
<li><strong>Autres demandes</strong> : réponse sous un mois.</li>
</ul>
<p>Vous pouvez aussi introduire une réclamation auprès de la CNIL (<a href="https://www.cnil.fr" target="_blank" rel="noopener">cnil.fr</a>). Le responsable du traitement est l'éditeur de Votona ; voir les <a href="{VOTONA}/mentions-legales/">mentions légales</a> et la <a href="{VOTONA}/confidentialite/#observatoire">politique de confidentialité</a>.</p>
<p class="small muted">Page mise à jour le {fr_date(site.generated_at, True)}.</p>
</div>"""
    return page(site, "/vous-etes-cite/", "Vous êtes cité ? Données personnelles et droits - Votona Observatoire",
                "Personnalité politique citée sur Votona Observatoire : données traitées, sources, base légale et procédure de rectification ou d'opposition.",
                "methode", body)


def stylesheet() -> str:
    """Feuille de style des pages fixes : celle du gabarit de l'app, sans copie à maintenir."""
    html = TEMPLATE.read_text(encoding="utf-8")
    return html[html.index("<style>") + len("<style>"):html.index("</style>")]


def votona_summary(site: Site) -> dict[str, Any]:
    """Résumé lu par le générateur de Votona (encart des fiches candidats) : nombres et rédactions, jamais de verdict."""
    cands = {}
    for c in site.candidates:
        facts = site.of_person(c["pid"])
        if facts:
            cands[c["votona_id"]] = {
                "n": len(facts), "url": SITE_URL + site.person_url[c["pid"]],
                "sources": sorted({site.sources.get(r["source_id"], r["source_id"]) for f in facts for r in f["reviews"]}),
                "last_review": max((f["review_date"] or "" for f in facts), default="") or None}
    families = {fid: {"n": n, "url": f"{SITE_URL}/sujets/{fid}/"} for fid, _ in FAMILIES
                if (n := sum(f["family"] == fid for f in site.facts))}
    return {"generated_at": site.generated_at, "scope": SCOPE, "candidats": cands, "sujets": families}


def build(site: Site, site_dir: Path) -> list[str]:
    """Écrit toutes les pages et le plan du site ; renvoie les adresses indexables."""
    (site_dir / "assets").mkdir(parents=True, exist_ok=True)
    (site_dir / "assets" / "observatoire.css").write_text(stylesheet(), encoding="utf-8")
    for d in ("candidats", "personnalites", "partis", "sujets", "methode", "vous-etes-cite"):  # pages recréées à chaque fois
        if (site_dir / d).exists():
            shutil.rmtree(site_dir / d)
    pages: dict[str, str] = {}
    listed = ["/", "/candidats/", "/personnalites/", "/partis/", "/sujets/", "/methode/", "/vous-etes-cite/"]
    for pid in site.person_url:
        if pid in site.candidate_by_pid or site.of_person(pid):
            path, html, indexable = person_page(site, pid)
            pages[path] = html
            if indexable:
                listed.append(path)
    for party_id in site.party_url:
        path, html = party_page(site, party_id)
        pages[path] = html
        listed.append(path)
    for fid, _ in FAMILIES:
        path, html = family_page(site, fid)
        pages[path] = html
        listed.append(path)
    pages.update(index_pages(site))
    pages["/methode/"] = methode_page(site)
    pages["/vous-etes-cite/"] = cited_page(site)
    for path, html in pages.items():
        out = site_dir / path.strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
    (site_dir / "donnees").mkdir(exist_ok=True)
    (site_dir / "donnees" / "votona.json").write_text(
        json.dumps(votona_summary(site), ensure_ascii=False, indent=1), encoding="utf-8")
    lastmod = site.generated_at[:10]
    (site_dir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{SITE_URL}{p}</loc><lastmod>{lastmod}</lastmod></url>\n" for p in listed) + "</urlset>\n",
        encoding="utf-8")
    return listed


def load_site(facts: list[dict[str, Any]], generated_at: str) -> Site:
    with (SEEDS_DIR / "sources.csv").open(encoding="utf-8") as f:
        sources = {s["id"]: s["name"] for s in csv.DictReader(f)}
    with (SEEDS_DIR / "candidates_2027.csv").open(encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))
    with (SEEDS_DIR / "themes.csv").open(encoding="utf-8") as f:
        topics = [{"slug": t["key"], "label": t["label"], "category": t["category"]} for t in csv.DictReader(f) if t["kind"] == "topic"]
    return Site.load(facts, candidates, topics, sources, generated_at)


if __name__ == "__main__":
    from datetime import datetime, timezone

    from pipeline.build_beta import SITE_DIR
    from pipeline.export import EXPORT_DIR
    facts_path = EXPORT_DIR / "facts.json"
    generated = datetime.fromtimestamp(facts_path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
    urls = build(load_site(json.loads(facts_path.read_text(encoding="utf-8")), generated), SITE_DIR)
    print(f"site/ : {len(urls)} pages au plan du site")
