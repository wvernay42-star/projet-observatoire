"""Back-office de l'Observatoire : onglet « Observatoire » de l'admin Votona (base Supabase de Votona).

    python -m pipeline.supabase_sync apply   # applique les décisions de l'admin, puis les retire
    python -m pipeline.supabase_sync push    # dépose les files préparées par « validation_sync seed »

Tables obs_queues (files) et obs_decisions (décisions), lisibles et modifiables par le seul compte
admin de Votona (RLS) ; la routine passe par une clé secrète, qui contourne la RLS. La clé est
l'identifiant API « Supabase » de l'environnement cloud (en-têtes ajoutés automatiquement vers
le domaine Supabase), ou à défaut la variable SUPABASE_SECRET_KEY ; jamais écrite dans le dépôt.
Les décisions sont appliquées sur les files telles que l'admin les a vues (celles de Supabase).
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from pipeline.validation_sync import OUT_DIR, apply

SUPABASE_URL = "https://vvvlhxniiykbdssmadbs.supabase.co"
KINDS = ("ratings", "attributions", "parties", "sources")
DELETE_BATCH = 50


def client() -> httpx.Client:
    headers = {"User-Agent": "curl/8.0"}  # Supabase refuse une clé secrète présentée par un navigateur
    if key := os.environ.get("SUPABASE_SECRET_KEY"):
        headers |= {"apikey": key, "Authorization": f"Bearer {key}"}
    return httpx.Client(base_url=SUPABASE_URL + "/rest/v1", headers=headers, timeout=60)


def push(c: httpx.Client, out_dir: Path = OUT_DIR) -> dict[str, int]:
    """Remplace les files du back-office par celles du jour."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for kind in KINDS:
        queue = json.loads((out_dir / f"{kind}.json").read_text(encoding="utf-8"))
        rows.append({"kind": kind, "generated_at": queue["generated_at"], "items": queue["items"], "updated_at": now})
    c.post("/obs_queues", json=rows,
           headers={"Prefer": "resolution=merge-duplicates,return=minimal"}).raise_for_status()
    return {row["kind"]: len(row["items"]) for row in rows}


def _in_list(ids: list[str]) -> str:
    return "in.(" + ",".join('"' + i.replace("\\", "\\\\").replace('"', '\\"') + '"' for i in ids) + ")"


def apply_decisions(c: httpx.Client) -> dict[str, Any]:
    """Applique les décisions en attente puis les retire (une décision incohérente est ignorée et retirée)."""
    response = c.get("/obs_decisions", params={"select": "*"})
    response.raise_for_status()
    decisions = response.json()
    if not decisions:
        return {"decisions": 0}
    response = c.get("/obs_queues", params={"select": "kind,items", "kind": "in.(ratings,attributions,parties)"})
    response.raise_for_status()
    queues = {row["kind"]: {"items": row["items"]} for row in response.json()}
    result = apply(decisions, queues)
    ids = [d["item_id"] for d in decisions]
    for start in range(0, len(ids), DELETE_BATCH):
        c.delete("/obs_decisions", params={"item_id": _in_list(ids[start:start + DELETE_BATCH])}).raise_for_status()
    return {"decisions": len(decisions), **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["apply", "push"])
    args = parser.parse_args()
    with client() as c:
        try:
            print(apply_decisions(c) if args.command == "apply" else push(c))
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise SystemExit("Supabase refuse l'accès : ajoutez l'identifiant API « Supabase » à l'environnement "
                                 "cloud « Observatoire » (même clé secrète que l'environnement « Votona »).") from e
            raise


if __name__ == "__main__":
    main()
