"""Construit le référentiel fermé des personnalités depuis Wikidata.

Écrit data/seeds/persons.csv, parties.csv et affiliations.csv. Périmètre : toute personne
ayant exercé depuis 2017 une fonction publique nationale ou locale (député, sénateur,
eurodéputé français, membre du gouvernement, dirigeant de parti, maire).

Les affiliations partisanes viennent de la propriété P102 (« membre du parti politique »)
avec ses dates ; une affiliation sans date reste sans date (jamais inventée).

    python -m pipeline.referential              # tout reconstruire
    python -m pipeline.referential --roles depute senateur
"""

import argparse
import csv
import json
import os
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from pipeline.connectors.base import SEEDS_DIR

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = os.environ.get(
    "OBSERVATOIRE_USER_AGENT",
    "g.nevert/0.1 (Observatoire de la parole politique; +mailto:guillaume.nevert@outlook.com)",
)
PAUSE_SECONDS = 2.0
BATCH_SIZE = 400
SINCE = '"2017-01-01"^^xsd:dateTime'

# Mandat dans la fenêtre : terminé après 2017, ou commencé récemment sans date de fin.
_WINDOW = f"""
  OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }}
  FILTER((BOUND(?end) && ?end >= {SINCE}) || (!BOUND(?end) && BOUND(?start) && ?start >= "{{since_start}}"^^xsd:dateTime))
"""
# Mandat sans aucune date, chez une personne vivante née après 1935 (données Wikidata lacunaires).
_UNDATED_LIVING = """
  FILTER NOT EXISTS { ?st pq:P580 ?s0 } FILTER NOT EXISTS { ?st pq:P582 ?e0 }
  ?p wdt:P569 ?birth. FILTER(?birth >= "1935-01-01"^^xsd:dateTime) FILTER NOT EXISTS { ?p wdt:P570 ?death }
"""

ROLES: dict[str, tuple[str, str]] = {
    "depute": ("député", f"""
  {{ ?p p:P39 ?st. ?st ps:P39 wd:Q3044918; pq:P2937 ?leg.
     VALUES ?leg {{ wd:Q24939798 wd:Q112567597 wd:Q126471296 }} }}
  UNION {{ ?p p:P39 ?st. ?st ps:P39 wd:Q3044918. {_WINDOW.replace("{since_start}", "2017-01-01T00:00:00Z")} }}
"""),
    "senateur": ("sénateur", f"""
  {{ ?p p:P39 ?st. ?st ps:P39 wd:Q14828018. {_WINDOW.replace("{since_start}", "2008-01-01T00:00:00Z")} }}
  UNION {{ ?p p:P39 ?st. ?st ps:P39 wd:Q14828018. {_UNDATED_LIVING} }}
"""),
    "eurodepute": ("eurodéputé", f"""
  ?p wdt:P27 wd:Q142; p:P39 ?st. ?st ps:P39 wd:Q27169.
  {_WINDOW.replace("{since_start}", "2014-01-01T00:00:00Z")}
"""),
    "gouvernement": ("membre du gouvernement", f"""
  ?cab wdt:P31 wd:Q1450662.
  OPTIONAL {{ ?cab wdt:P571 ?cabStart }} OPTIONAL {{ ?cab wdt:P576 ?cabEnd }}
  FILTER((BOUND(?cabEnd) && ?cabEnd >= {SINCE}) || (!BOUND(?cabEnd) && BOUND(?cabStart) && ?cabStart >= {SINCE}))
  ?p p:P39 ?st. ?st pq:P5054 ?cab.
"""),
    "chef_parti": ("dirigeant de parti", f"""
  ?org wdt:P31/wdt:P279* wd:Q7278; wdt:P17 wd:Q142; p:P488 ?st. ?st ps:P488 ?p.
  OPTIONAL {{ ?st pq:P582 ?end }} FILTER(!BOUND(?end) || ?end >= {SINCE})
"""),
    "maire": ("maire", f"""
  ?pos wdt:P279 wd:Q382617. ?p p:P39 ?st. ?st ps:P39 ?pos.
  {_WINDOW.replace("{since_start}", "2014-01-01T00:00:00Z")}
"""),
}


@dataclass
class Person:
    id: str
    full_name: str = ""
    aliases: set[str] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def day(value: str | None) -> str:
    """'2017-06-21T00:00:00Z' -> '2017-06-21' ; valeur absente -> ''."""
    return value[:10] if value and value[:1].isdigit() else ""


class Wikidata:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
            timeout=180,
        )
        self._last = 0.0

    def query(self, sparql: str) -> list[dict[str, str]]:
        for attempt in range(4):
            wait = PAUSE_SECONDS - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            response = self.client.post(SPARQL_URL, data={"query": sparql})
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(float(response.headers.get("Retry-After", 10 * (attempt + 1))))
                continue
            response.raise_for_status()
            return [{k: v["value"] for k, v in b.items()} for b in response.json()["results"]["bindings"]]
        raise RuntimeError("Wikidata : échec après plusieurs tentatives")


def batches(items: Iterable[str], size: int = BATCH_SIZE) -> Iterator[list[str]]:
    items = sorted(items)
    for i in range(0, len(items), size):
        yield items[i : i + size]


def values(ids: list[str]) -> str:
    return " ".join(f"wd:{i}" for i in ids)


def fetch_role_holders(wd: Wikidata, roles: Iterable[str]) -> dict[str, Person]:
    persons: dict[str, Person] = {}
    for role in roles:
        label, body = ROLES[role]
        rows = wd.query(f"SELECT DISTINCT ?p WHERE {{ {body} }}")
        for row in rows:
            pid = qid(row["p"])
            persons.setdefault(pid, Person(pid)).roles.add(label)
        print(f"  {role}: {len(rows)} personnes")
    return persons


def fetch_names(wd: Wikidata, persons: dict[str, Person]) -> None:
    for ids in batches(persons):
        rows = wd.query(f"""SELECT ?p ?label ?alias WHERE {{
  VALUES ?p {{ {values(ids)} }}
  OPTIONAL {{ ?p rdfs:label ?label FILTER(LANG(?label) IN ("fr", "mul")) }}
  OPTIONAL {{ ?p skos:altLabel ?alias FILTER(LANG(?alias) = "fr") }}
}}""")
        for row in rows:
            person = persons[qid(row["p"])]
            if row.get("label") and not person.full_name:
                person.full_name = row["label"]
            if row.get("alias"):
                person.aliases.add(row["alias"])


def fetch_affiliations(wd: Wikidata, person_ids: Iterable[str]) -> list[dict[str, str]]:
    affiliations = []
    for ids in batches(person_ids):
        rows = wd.query(f"""SELECT ?p ?party ?start ?end WHERE {{
  VALUES ?p {{ {values(ids)} }}
  ?p p:P102 ?st. ?st ps:P102 ?party.
  FILTER NOT EXISTS {{ ?st wikibase:rank wikibase:DeprecatedRank }}
  OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }}
}}""")
        for row in rows:
            pid = qid(row["p"])
            affiliations.append({
                "person_id": pid,
                "party_id": qid(row["party"]),
                "start_date": day(row.get("start")),
                "end_date": day(row.get("end")),
                "source_url": f"https://www.wikidata.org/wiki/{pid}#P102",
            })
    return affiliations


def fetch_parties(wd: Wikidata, party_ids: Iterable[str]) -> list[dict[str, str]]:
    parties: dict[str, dict[str, str]] = {}
    for ids in batches(party_ids):
        rows = wd.query(f"""SELECT ?party ?label ?short ?country WHERE {{
  VALUES ?party {{ {values(ids)} }}
  OPTIONAL {{ ?party rdfs:label ?label FILTER(LANG(?label) IN ("fr", "mul")) }}
  OPTIONAL {{ ?party wdt:P1813 ?short FILTER(LANG(?short) = "fr") }}
  OPTIONAL {{ ?party wdt:P17 ?country }}
}}""")
        for row in rows:
            party = parties.setdefault(qid(row["party"]), {
                "id": qid(row["party"]), "name": "", "short_name": "", "country": "", "parlgov_id": "",
            })
            party["name"] = party["name"] or row.get("label", "")
            party["short_name"] = party["short_name"] or row.get("short", "")
            if row.get("country") and qid(row["country"]) == "Q142":
                party["country"] = "FR"
    return sorted(parties.values(), key=lambda p: p["id"])


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build(roles: Iterable[str], seeds_dir: Path = SEEDS_DIR, wd: Wikidata | None = None) -> None:
    wd = wd or Wikidata()
    print("Titulaires de fonctions :")
    persons = fetch_role_holders(wd, roles)
    print(f"Noms et alias de {len(persons)} personnes…")
    fetch_names(wd, persons)
    persons = {pid: p for pid, p in persons.items() if p.full_name}
    print("Affiliations partisanes…")
    affiliations = fetch_affiliations(wd, persons)
    print("Partis…")
    parties = fetch_parties(wd, {a["party_id"] for a in affiliations})

    write_csv(seeds_dir / "persons.csv", ["id", "full_name", "aliases", "country", "public_role"], (
        {
            "id": p.id,
            "full_name": p.full_name,
            "aliases": json.dumps(sorted(p.aliases - {p.full_name}), ensure_ascii=False),
            "country": "FR",
            "public_role": "; ".join(sorted(p.roles)),
        }
        for p in sorted(persons.values(), key=lambda p: p.id)
    ))
    write_csv(seeds_dir / "parties.csv", ["id", "name", "short_name", "country", "parlgov_id"], parties)
    write_csv(seeds_dir / "affiliations.csv",
              ["person_id", "party_id", "start_date", "end_date", "source_url"],
              sorted(affiliations, key=lambda a: (a["person_id"], a["start_date"], a["party_id"])))
    print(f"Écrit : {len(persons)} personnes, {len(parties)} partis, {len(affiliations)} affiliations.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--roles", nargs="+", choices=list(ROLES), default=list(ROLES))
    args = parser.parse_args()
    build(args.roles)


if __name__ == "__main__":
    main()
