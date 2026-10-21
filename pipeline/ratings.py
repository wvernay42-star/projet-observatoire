"""Conversion des verdicts d'origine vers l'échelle commune (rating_map).

Règles, dans l'ordre (docs/cadrage.md, « Échelle de verdicts ») :
1. correspondance exacte (source + libellé, insensible à la casse et aux accents) dans rating_map ;
2. ratingValue rapporté à bestRating / worstRating, seulement pour les sources de NUMERIC_SOURCES ;
3. sinon 'unrated', et le libellé part en file de validation (proposition à valider à la main).
"""

import csv
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pipeline.connectors.base import SEEDS_DIR, RawReview

LEVELS = ("true", "mostly_true", "half_true", "mostly_false", "false", "unrated")
DECIDED_BY = ("rule", "llm_validated", "human")

# Sources dont la note numérique est cohérente d'un article à l'autre. Vide : sur le flux
# Data Commons, Les Décodeurs notent « FAUX » 0/2, 0/5, 1/2 ou 0/10 selon les articles.
NUMERIC_SOURCES: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Rating:
    normalized: str
    method: str  # 'map', 'numeric' ou 'pending' (à valider, compté comme unrated)


def label_key(label: str) -> str:
    """Clé de comparaison : minuscules, sans accents, apostrophes et espaces uniformisés."""
    text = unicodedata.normalize("NFKD", label.replace("’", "'"))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", text).strip(" .")


def load_rating_map(path: Path = SEEDS_DIR / "rating_map.csv") -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["rating_normalized"] not in LEVELS:
                raise ValueError(f"Niveau inconnu dans rating_map : {row}")
            if row["decided_by"] not in DECIDED_BY:
                raise ValueError(f"decided_by inconnu dans rating_map : {row}")
            mapping[(row["source_id"], label_key(row["rating_original"]))] = row["rating_normalized"]
    return mapping


def _numeric(value: str | None, best: str | None, worst: str | None) -> str | None:
    try:
        v, b, w = float(value), float(best), float(worst)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if b == w or not min(b, w) <= v <= max(b, w):
        return None
    share = (v - w) / (b - w)  # 0 = faux, 1 = vrai
    return LEVELS[4 - min(4, int(share * 5))]


def convert(review: RawReview, mapping: dict[tuple[str, str], str]) -> Rating:
    if review.rating_original:
        found = mapping.get((review.source_id, label_key(review.rating_original)))
        if found:
            return Rating(found, "map")
    if review.source_id in NUMERIC_SOURCES:
        found = _numeric(review.rating_value, review.best_rating, review.worst_rating)
        if found:
            return Rating(found, "numeric")
    return Rating("unrated", "pending")


def unmapped_labels(reviews: Iterable[RawReview], mapping: dict[tuple[str, str], str]) -> Counter:
    """(source_id, libellé d'origine) non convertis, avec leur nombre d'occurrences."""
    return Counter(
        (r.source_id, r.rating_original or "")
        for r in reviews
        if convert(r, mapping).method == "pending"
    )


def main() -> None:
    import argparse
    from datetime import date

    from pipeline.connectors.datacommons_feed import DataCommonsFeed

    parser = argparse.ArgumentParser(description="Bilan de conversion des verdicts sur le flux Data Commons")
    parser.add_argument("--feed", type=Path, help="flux déjà téléchargé (sinon téléchargement)")
    args = parser.parse_args()
    reviews = DataCommonsFeed(feed_path=args.feed).fetch(date(2000, 1, 1))
    mapping = load_rating_map()
    methods = Counter(convert(r, mapping).method for r in reviews)
    print(f"{len(reviews)} vérifications : {dict(methods)}")
    print("Libellés non convertis (-> unrated en attendant validation) :")
    for (source, label), n in unmapped_labels(reviews, mapping).most_common():
        print(f"  {n:>3} × {source} : {label[:90]!r}")


if __name__ == "__main__":
    main()
