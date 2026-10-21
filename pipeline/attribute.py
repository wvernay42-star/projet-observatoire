"""Attribution d'une vérification à une personne, puis à un parti à la date du fait.

Règles (docs/cadrage.md, « Attribution et dédoublonnage ») :
1. référentiel fermé : seules les personnes de persons.csv peuvent être attribuées ;
2. claimant identique (casse, accents, tirets près) à un nom ou alias d'une seule personne -> auto_sure ;
3. libellé vague (« des internautes », « un post Facebook »…) -> jamais attribué (rejected) ;
4. correspondance partielle ou ambiguë (homonymes, nom seul, nom + média) -> to_review ;
5. le parti vient de affiliations.csv à la date du fait, jamais de l'article.
"""

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pipeline.connectors.base import SEEDS_DIR
from pipeline.text import name_key

_VAGUE = re.compile(
    r"\b(internautes?|utilisateurs?|comptes?|pages?|posts?|publications?|sites?|blogs?|"
    r"rumeurs?|petitions?|videos?|images?|photos?|captures?|messages?|chaines?|"
    r"plusieurs|certains|anonymes?|facebook|twitter|tiktok|youtube|instagram|telegram|whatsapp|"
    r"reseaux sociaux|viral|virale)\b"
)
_VAGUE_START = re.compile(r"^(des|un|une|les|le|la|l|d)\s")
_VAGUE_WHOLE = re.compile(r"^(x|multiples?|sources? multiples?|plusieurs personnes|divers|inconnu|anonyme|\W*)$")
# « X sur TF1 », « X, député RN », « X (LFI) », « le ministre X » : on retire le contexte.
_CONTEXT = [
    re.compile(r"\s*\(.*?\)\s*"),
    re.compile(r",.*$"),
    re.compile(r"\s+(sur|dans|a|au|lors)\s+.*$"),
    re.compile(r"^(le|la|l)\s+(depute|deputee|senateur|senatrice|ministre|maire|president|presidente|"
               r"secretaire d etat|porte parole|candidat|candidate|eurodepute|eurodeputee)\s+"),
]


@dataclass(frozen=True)
class Attribution:
    status: str  # 'auto_sure', 'to_review' ou 'rejected'
    person_id: str | None = None
    candidates: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class PartyAtDate:
    party_id: str | None
    # 'ok', 'none' (aucune affiliation connue), 'ambiguous' (plusieurs en vigueur),
    # 'undated' (seules des affiliations sans aucune date correspondent : à valider), 'no_date',
    # 'no_party' (validé à la main : sans étiquette à cette date)
    status: str
    candidates: tuple[str, ...] = ()


class Referential:
    def __init__(self, persons: list[dict[str, str]], affiliations: list[dict[str, str]],
                 manual_affiliations: list[dict[str, str]] | None = None,
                 parties: list[dict[str, str]] | None = None):
        self.names: dict[str, set[str]] = defaultdict(set)
        self.surnames: dict[str, set[str]] = defaultdict(set)
        self.full_names: dict[str, str] = {}
        for p in persons:
            self.full_names[p["id"]] = p["full_name"]
            for name in [p["full_name"], *json.loads(p.get("aliases") or "[]")]:
                key = name_key(name)
                if key:
                    self.names[key].add(p["id"])
            tokens = name_key(p["full_name"]).split()
            if len(tokens) >= 2:
                self.surnames[tokens[-1]].add(p["id"])
        self.affiliations: dict[str, list[dict[str, str]]] = defaultdict(list)
        for a in affiliations:
            self.affiliations[a["person_id"]].append(a)
        # Affiliations validées à la main : prioritaires sur Wikidata aux dates qu'elles couvrent.
        # Période d'existence de chaque parti : une affiliation n'a pas de sens hors de cette période.
        self.party_periods = {p["id"]: (p.get("inception", ""), p.get("dissolved", "")) for p in parties or []}
        self.manual: dict[str, list[dict[str, str]]] = defaultdict(list)
        for a in manual_affiliations or []:
            self.manual[a["person_id"]].append(a)

    @classmethod
    def load(cls, seeds_dir: Path = SEEDS_DIR) -> "Referential":
        def read(name: str) -> list[dict[str, str]]:
            with (seeds_dir / name).open(encoding="utf-8") as f:
                return list(csv.DictReader(f))

        manual_path = seeds_dir / "affiliations_manual.csv"
        manual = read("affiliations_manual.csv") if manual_path.exists() else []
        return cls(read("persons.csv"), read("affiliations.csv"), manual, read("parties.csv"))

    def attribute(self, claimant: str | None) -> Attribution:
        if not claimant or not claimant.strip():
            return Attribution("rejected", reason="claimant absent")
        key = name_key(claimant)
        exact = self.names.get(key, set())
        if len(exact) == 1:
            return Attribution("auto_sure", next(iter(exact)), reason="correspondance exacte")
        if len(exact) > 1:
            return Attribution("to_review", candidates=tuple(sorted(exact)), reason="homonymes")

        stripped = key
        for pattern in _CONTEXT:
            stripped = pattern.sub(" ", stripped).strip()
        stripped = re.sub(r"\s+", " ", stripped)
        if stripped != key and (found := self.names.get(stripped)):
            return Attribution("to_review", candidates=tuple(sorted(found)),
                               reason="nom retrouvé après retrait du contexte")

        if _VAGUE.search(key) or _VAGUE_START.match(key) or _VAGUE_WHOLE.match(key):
            return Attribution("rejected", reason="libellé vague")

        tokens = stripped.split()
        if len(tokens) == 1 and (found := self.surnames.get(tokens[0])):
            return Attribution("to_review", candidates=tuple(sorted(found))[:20], reason="nom seul")
        return Attribution("rejected", reason="hors référentiel")

    def party_existed(self, party_id: str, on: str) -> bool:
        """Le parti existait-il à cette date ? Inconnu -> oui (on ne retire rien sans information)."""
        inception, dissolved = self.party_periods.get(party_id, ("", ""))
        n_start, n_end = min(len(inception), len(on)), min(len(dissolved), len(on))
        return (not inception or inception[:n_start] <= on[:n_start]) and \
            (not dissolved or on[:n_end] <= dissolved[:n_end])

    def party_at(self, person_id: str, on: str | None) -> PartyAtDate:
        """Parti en vigueur à la date `on` (ISO 8601, jour, mois ou année)."""
        if not on:
            return PartyAtDate(None, "no_date")
        on = on[:10]

        def started(start: str) -> bool:  # comparé à la précision la plus faible des deux dates
            n = min(len(start), len(on))
            return not start or start[:n] <= on[:n]

        def not_ended(end: str) -> bool:
            n = min(len(end), len(on))
            return not end or on[:n] <= end[:n]

        manual = {a["party_id"] for a in self.manual.get(person_id, [])
                  if started(a["start_date"]) and not_ended(a["end_date"])
                  and (a["party_id"] == "none" or self.party_existed(a["party_id"], on))}
        if len(manual) == 1:
            party_id = next(iter(manual))
            return PartyAtDate(None, "no_party") if party_id == "none" else PartyAtDate(party_id, "ok")

        matching = [
            a for a in self.affiliations.get(person_id, [])
            if started(a["start_date"]) and not_ended(a["end_date"]) and self.party_existed(a["party_id"], on)
        ]
        # Le cadrage exige des affiliations datées : une affiliation sans aucune date
        # ne sert jamais automatiquement, elle est seulement proposée à la validation.
        dated = {a["party_id"] for a in matching if a["start_date"] or a["end_date"]}
        undated = {a["party_id"] for a in matching} - dated
        if len(dated) == 1 and not undated:
            return PartyAtDate(next(iter(dated)), "ok")
        if len(dated) > 1:
            return PartyAtDate(None, "ambiguous", tuple(sorted(dated | undated)))
        if undated:
            return PartyAtDate(None, "undated", tuple(sorted(dated | undated)))
        return PartyAtDate(None, "none")


def main() -> None:
    import argparse
    from collections import Counter
    from datetime import date

    from pipeline.connectors.datacommons_feed import DataCommonsFeed

    parser = argparse.ArgumentParser(description="Bilan d'attribution sur le flux Data Commons")
    parser.add_argument("--feed", type=Path, help="flux déjà téléchargé (sinon téléchargement)")
    args = parser.parse_args()
    ref = Referential.load()
    reviews = DataCommonsFeed(feed_path=args.feed).fetch(date(2000, 1, 1))
    results = [(r, ref.attribute(r.claimant)) for r in reviews]
    print(Counter(a.status for _, a in results))
    for r, a in results:
        if a.status != "rejected" or a.reason not in ("libellé vague", "claimant absent"):
            who = a.person_id or ", ".join(ref.full_names.get(c, c) for c in a.candidates[:3])
            party = ref.party_at(a.person_id, r.claim_date or r.review_date) if a.person_id else None
            print(f"{a.status:<10} {a.reason:<40} {r.claimant!r} -> {who} {party or ''}")


if __name__ == "__main__":
    main()
