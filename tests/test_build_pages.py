import json
from pipeline import build_pages
from pipeline.build_pages import Site, build, fr_date, slugify


def fact(fid, pid, name, party=None, verdict="false", theme="Écologie", date="2026-10-01"):
    return {"id": fid, "person": {"id": pid, "name": name, "votona_id": None},
            "party": {"id": party, "name": "Parti " + (party or ""), "short_name": party or "", "status": "ok" if party else "none"},
            "claim_text": "Une <affirmation> & chiffrée", "claim_date": date, "date_is_fallback": False, "verdict": verdict,
            "theme": theme, "votona_topics": [], "reviews": [
                {"source_id": "afp", "source_name": "AFP Factuel", "url": "https://a/" + fid, "title": "T",
                 "rating_original": "Faux", "rating_normalized": verdict, "review_date": date}]}


CANDIDATES = [
    {"votona_id": "lepen", "name": "Marine Le Pen", "votona_party": "RN", "status": "déclaré ou pressenti",
     "person_id": "Q1", "person_match": "sûr", "party_id": "RN", "votona_url": "https://votona.fr/candidats/lepen/"},
    {"votona_id": "mathieu", "name": "Benoît Mathieu", "votona_party": "Sans étiquette", "status": "déclaré ou pressenti",
     "person_id": "", "person_match": "", "party_id": "", "votona_url": "https://votona.fr/candidats/mathieu/"},
]
TOPICS = [{"slug": "relancer-le-nucleaire", "label": "Construire des réacteurs", "category": "Écologie"}]


def make_site():
    facts = [fact("c1", "Q1", "Marine Le Pen", "RN"), fact("c2", "Q2", "Jean Martin", "RN", "true", date="2025-03-02"),
             fact("c3", "Q3", "Jean Martin", None, "half_true")]  # homonyme : deux adresses distinctes
    return Site.load(facts, CANDIDATES, TOPICS, {"afp": "AFP Factuel"}, "2026-10-27T05:00:00+00:00")


def test_addresses():
    site = make_site()
    assert site.person_url["Q1"] == "/candidats/lepen/"
    assert site.person_url["votona:mathieu"] == "/candidats/mathieu/"
    assert {site.person_url["Q2"], site.person_url["Q3"]} == {"/personnalites/jean-martin/", "/personnalites/jean-martin-q3/"}
    assert site.party_url["RN"] == "/partis/rn/"


def test_pages_sitemap_and_escaping(tmp_path):
    listed = build(make_site(), tmp_path)
    lepen = (tmp_path / "candidats/lepen/index.html").read_text(encoding="utf-8")
    assert "<h1>Marine Le Pen</h1>" in lepen and "Une &lt;affirmation&gt; &amp; chiffrée" in lepen
    assert "https://votona.fr/candidats/lepen/" in lepen and 'rel="canonical"' in lepen
    # candidat sans vérification : page publiée, hors du plan du site
    assert (tmp_path / "candidats/mathieu/index.html").exists() and "/candidats/mathieu/" not in listed
    for p in ("/candidats/lepen/", "/partis/rn/", "/sujets/ecologie/", "/methode/", "/personnalites/jean-martin/"):
        assert p in listed and (tmp_path / p.strip("/") / "index.html").exists()
    assert "observatoire.votona.fr/sujets/ecologie/" in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert ".topbar" in (tmp_path / "assets/observatoire.css").read_text(encoding="utf-8")
    # indexable ; une fiche sans fait reste en noindex
    assert "noindex" not in lepen
    assert 'content="noindex, nofollow"' in (tmp_path / "candidats/mathieu/index.html").read_text(encoding="utf-8")


def test_helpers():
    assert fr_date("2026-10-07") == "7 oct. 2026" and fr_date("2026-10", True) == "octobre 2026" and fr_date(None) == "date inconnue"
    assert slugify("Éric Ciotti") == "eric-ciotti"


def test_party_keeps_latest_name_and_address():
    old = fact("c9", "Q1", "Marine Le Pen", "RN", date="2017-05-01")
    old["party"].update(name="Front national", short_name="FN")
    site = Site.load([fact("c1", "Q1", "Marine Le Pen", "RN"), old], CANDIDATES, TOPICS, {}, "2026-10-27")
    assert site.party_url["RN"] == "/partis/rn/" and site.parties["RN"] == "Parti RN (RN)"


def test_votona_summary_has_counts_never_verdicts(tmp_path):
    build(make_site(), tmp_path)
    data = json.loads((tmp_path / "donnees/votona.json").read_text(encoding="utf-8"))
    lepen = data["candidats"]["lepen"]
    assert lepen["url"] == "https://observatoire.votona.fr/candidats/lepen/" and lepen["n"] >= 1
    assert lepen["sources"] == ["AFP Factuel"] and "mathieu" not in data["candidats"]
    assert "rating" not in json.dumps(data) and "verdict" not in json.dumps(data)


def test_share_image_per_candidate_when_available(tmp_path, monkeypatch):
    og = tmp_path / "og"
    (og / "candidats").mkdir(parents=True)
    (og / "candidats" / "lepen.jpg").write_bytes(b"jpg")
    monkeypatch.setattr(build_pages, "OG_DIR", og)
    build(make_site(), tmp_path / "site")
    lepen = (tmp_path / "site/candidats/lepen/index.html").read_text(encoding="utf-8")
    mathieu = (tmp_path / "site/candidats/mathieu/index.html").read_text(encoding="utf-8")
    assert 'og:image" content="https://observatoire.votona.fr/assets/og/candidats/lepen.jpg"' in lepen
    assert 'og:image" content="https://observatoire.votona.fr/assets/og.jpg"' in mathieu
