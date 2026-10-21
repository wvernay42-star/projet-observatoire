"""Normalisation de texte partagée (libellés de verdict, noms de personnes)."""

import re
import unicodedata


def label_key(label: str) -> str:
    """Clé de comparaison : minuscules, sans accents, apostrophes et espaces uniformisés."""
    text = unicodedata.normalize("NFKD", label.replace("’", "'"))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", text).strip(" .")


def name_key(name: str) -> str:
    """Clé d'un nom propre : comme label_key, tirets et apostrophes traités comme des espaces."""
    return re.sub(r"[\s'\-‐–]+", " ", label_key(name)).strip()
