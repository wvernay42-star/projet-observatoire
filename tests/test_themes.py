from pipeline.themes import classify, load_themes

THEMES = load_themes()


def test_topic_and_family():
    cat, topics = classify("La France n'a pas eu de budget à l'équilibre, la dette explose", THEMES)
    assert cat == "Économie & travail"
    assert [t["slug"] for t in topics] == ["reduire-la-dette-publique-en-priorite-par-la-baisse-des"]


def test_family_without_topic():
    assert classify("Le Hamas et Israël : ce que dit l'accord de cessez-le-feu à Gaza", THEMES) == ("Défense & numérique", [])


def test_unclassified():
    assert classify("Manger bio réduit les risques", THEMES)[0] in ("Écologie", None)
    assert classify("Une phrase sans rapport", THEMES) == (None, [])


def test_keywords_match_word_starts_only():
    # « isf » ne doit pas être reconnu au milieu d'un autre mot
    assert classify("Les visfulgures", THEMES)[1] == []
