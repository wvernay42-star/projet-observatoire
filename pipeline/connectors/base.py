"""Interface commune des connecteurs : fetch() -> list[RawReview]."""

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

SEEDS_DIR = Path(__file__).resolve().parents[2] / "data" / "seeds"


@dataclass(frozen=True)
class RawReview:
    """Un ClaimReview tel que publié par la source, avant normalisation.

    Métadonnées uniquement : jamais le corps de l'article.
    """

    url: str
    source_id: str
    connector: str
    claim_text: str | None
    claimant: str | None
    claim_date: str | None  # brut, tel que fourni (itemReviewed.datePublished)
    review_date: str | None  # brut (ClaimReview.datePublished)
    rating_original: str | None  # reviewRating.alternateName, libellé exact
    rating_value: str | None = None
    best_rating: str | None = None
    worst_rating: str | None = None
    title: str | None = None
    lang: str | None = None
    appearance_urls: tuple[str, ...] = field(default_factory=tuple)


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def load_source_domains(path: Path = SEEDS_DIR / "sources.csv") -> dict[str, str]:
    """Domaine -> source_id, d'après sources.csv (référentiel fermé des sources)."""
    with path.open(encoding="utf-8") as f:
        return {domain_of(row["url"]): row["id"] for row in csv.DictReader(f) if row["url"]}


class Connector(ABC):
    name: str

    @abstractmethod
    def fetch(self, since: date) -> list[RawReview]:
        """Vérifications publiées depuis `since` (recouvrement inclus par l'appelant)."""
