"""Regroupement des vérifications (reviews) en affirmations (claims).

Niveau 1 — même URL : une seule review (clé unique, upsert en base).
Niveau 2 — même affirmation vérifiée par plusieurs médias : un seul claim si même personne,
dates de déclaration à ±3 jours et textes très proches (rapidfuzz, token_set_ratio), ou
textes assez proches citant exactement les mêmes chiffres (au moins deux).
Les reviews non attribuées à une personne ne sont jamais fusionnées entre elles.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from rapidfuzz import fuzz

from pipeline.text import label_key

MAX_DAYS_APART = 3
MIN_SIMILARITY = 80
MIN_SIMILARITY_SAME_FIGURES = 55


@dataclass
class Group:
    person_id: str | None
    claim_date: str | None
    texts: list[str] = field(default_factory=list)
    review_ids: list[str] = field(default_factory=list)


def _days_apart(a: str | None, b: str | None) -> int | None:
    if not a or not b or len(a) < 10 or len(b) < 10:
        return None
    return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days)


def _figures(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def similar(a: str, b: str) -> bool:
    score = fuzz.token_set_ratio(label_key(a), label_key(b))
    if score >= MIN_SIMILARITY:
        return True
    figures = _figures(a)
    return len(figures) >= 2 and figures == _figures(b) and score >= MIN_SIMILARITY_SAME_FIGURES


def group_reviews(items: Iterable[tuple[str, str | None, str | None, str]]) -> list[Group]:
    """items : (review_id, person_id, claim_date, texte) -> groupes, dans un ordre stable."""
    groups: list[Group] = []
    for review_id, person_id, claim_date, text in sorted(items, key=lambda i: (i[2] or "", i[0])):
        target = None
        if person_id:
            for g in groups:
                apart = _days_apart(g.claim_date, claim_date)
                if g.person_id == person_id and apart is not None and apart <= MAX_DAYS_APART \
                        and any(similar(text, t) for t in g.texts):
                    target = g
                    break
        if target is None:
            target = Group(person_id, claim_date)
            groups.append(target)
        target.texts.append(text)
        target.review_ids.append(review_id)
    return groups


def majority_verdict(verdicts: list[str]) -> str:
    """Verdict retenu pour un claim : le plus fréquent ; égalité -> 'unrated' (cadrage)."""
    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v] = counts.get(v, 0) + 1
    best = max(counts.values())
    winners = [v for v, n in counts.items() if n == best]
    return winners[0] if len(winners) == 1 else "unrated"
