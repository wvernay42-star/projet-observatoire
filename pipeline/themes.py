"""Thèmes indicatifs d'une déclaration : familles et sujets de Votona, par mots-clés.

data/seeds/themes.csv liste, pour chaque sujet de Votona (adresse votona.fr/sujets/<slug>/) et
chaque famille, des mots-clés normalisés (minuscules, sans accents). Un sujet est retenu dès qu'un
de ses mots-clés apparaît (début de mot) dans l'affirmation ou le titre de la vérification ; la
famille est celle des sujets trouvés, sinon celle dont les mots-clés reviennent le plus.
Classement automatique et indicatif : il oriente la lecture, il ne qualifie jamais le propos.
"""

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pipeline.connectors.base import SEEDS_DIR
from pipeline.text import name_key


@dataclass(frozen=True)
class Theme:
    kind: str  # 'topic' ou 'category'
    key: str
    label: str
    category: str
    patterns: tuple[re.Pattern, ...]


def load_themes(path: Path = SEEDS_DIR / "themes.csv") -> list[Theme]:
    with path.open(encoding="utf-8") as f:
        return [Theme(r["kind"], r["key"], r["label"], r["category"],
                      tuple(re.compile(r"(?<![a-z0-9])" + re.escape(name_key(k))) for k in r["keywords"].split(";") if k.strip()))
                for r in csv.DictReader(f)]


def classify(text: str, themes: list[Theme]) -> tuple[str | None, list[dict[str, str]]]:
    """(famille, sujets Votona) d'un texte."""
    key = " " + name_key(text) + " "
    topics = [t for t in themes if t.kind == "topic" and any(p.search(key) for p in t.patterns)]
    if topics:
        category = Counter(t.category for t in topics).most_common(1)[0][0]
    else:
        scores = Counter({t.category: sum(len(p.findall(key)) for p in t.patterns) for t in themes if t.kind == "category"})
        best = scores.most_common(1)
        category = best[0][0] if best and best[0][1] else None
    return category, [{"slug": t.key, "label": t.label} for t in topics]
