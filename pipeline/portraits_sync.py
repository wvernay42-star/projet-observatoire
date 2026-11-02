"""Portraits libres des personnalités hors candidats 2027 (Wikimedia Commons), collectés par petits lots.

    python -m pipeline.portraits_sync [--max 20]   # traite au plus 20 photos, puis s'arrête
    python -m pipeline.portraits_sync --status     # où en est la collecte

Pour chaque personne ayant au moins une déclaration vérifiée : image principale de sa fiche Wikidata
(P18) ; retenue seulement si sa licence est libre (CC, domaine public, Parlement européen...) et si un
seul visage net et centré y figure (détection OpenCV). L'image est recadrée sur le visage (192×192 WebP)
dans web/beta/portraits/<identifiant Wikidata>.webp ; son crédit (auteur, licence, lien) va dans
data/seeds/portraits.json, avec celui des candidats ; la décision de chaque personne dans
data/seeds/portraits_state.json. Wikimedia limite fortement les adresses partagées des environnements
cloud : un lot s'arrête proprement au premier refus (429) et reprend au passage suivant.

L'affichage de ces portraits est coupé tant que build_pages.OTHERS_PORTRAITS est False : on ne le passe à
True qu'une fois toutes les personnes traitées (--status), pour traiter tout le monde de la même façon.
"""

import argparse
import csv
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import httpx

from pipeline.connectors.base import SEEDS_DIR

ROOT = Path(__file__).resolve().parents[1]
EXPORT_FACTS = ROOT / "data" / "export" / "facts.json"
IMAGES_DIR = ROOT / "web" / "beta" / "portraits"
CREDITS_PATH = SEEDS_DIR / "portraits.json"
STATE_PATH = SEEDS_DIR / "portraits_state.json"
USER_AGENT = "VotonaObservatoire/1.0 (+https://observatoire.votona.fr; contact@votona.fr)"
PAUSE_SECONDS = 2.5
SPARQL_URL = "https://query.wikidata.org/sparql"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
SIZE = 192
FREE = re.compile(
    r"^(CC0|CC BY(-SA)? [1-4]\.0( [a-z]{2,3})?|Public domain|PD.*|FAL|Attribution|European Parliament|"
    r"Licence Ouverte.*|Etalab.*)", re.I)
# Décisions enregistrées (une par personne, définitives) : une personne absente de l'état est « à traiter ».
OK, NO_PHOTO, NOT_FREE, NO_FACE = "ok", "no_photo", "not_free", "no_face"


class RateLimited(Exception):
    """Wikimedia refuse (429) sur tous les chemins : on s'arrête, la suite au prochain passage."""


def is_free(license_name: str) -> bool:
    return bool(FREE.match(license_name or ""))


def parse_imageinfo(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Réponse de l'API Commons (prop=imageinfo) -> titre -> licence, auteur, date, tailles, liens."""
    renamed = {n["to"]: n["from"] for n in data.get("query", {}).get("normalized", [])}
    out: dict[str, dict[str, Any]] = {}
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        raw_date = re.sub(r"<[^>]+>", "", meta.get("DateTimeOriginal", {}).get("value", "")
                          or meta.get("DateTime", {}).get("value", ""))
        year = re.search(r"(19|20)\d\d(-\d\d(-\d\d)?)?", raw_date)
        author = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip()
        author = re.sub(r"^(Own work|Travail personnel)\s*[-–,]?\s*", "", author, flags=re.I).strip()
        out[renamed.get(page.get("title", ""), page.get("title", ""))] = {
            "license": lic, "free": is_free(lic), "license_url": meta.get("LicenseUrl", {}).get("value", ""),
            "author": author, "date": year.group(0) if year else "", "w": info.get("width", 0),
            "thumb": info.get("thumburl", ""), "url": info.get("url", ""), "page": info.get("descriptionurl", "")}
    return out


def usable_face(face: dict[str, Any] | None) -> bool:
    """Un seul visage, assez grand (≥ 15 % de la largeur) et centré : un vrai portrait."""
    if not face or face["n"] != 1:
        return False
    x, _, w, _ = face["box"]
    return w / face["w"] >= 0.15 and 0.15 <= (x + w / 2) / face["w"] <= 0.85


def detect_face(data: bytes) -> dict[str, Any] | None:
    import cv2
    import numpy as np
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
    gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    boxes = [tuple(int(v) for v in b) for b in cascade.detectMultiScale(gray, 1.1, 6, minSize=(int(w * 0.10),) * 2)]
    return {"n": len(boxes), "w": w, "h": h, "box": max(boxes, key=lambda b: b[2]) if boxes else None}


def crop_webp(data: bytes, box: tuple[int, int, int, int]) -> bytes:
    """Carré centré sur le visage (un peu plus bas : front, cheveux, épaules), 192×192 WebP."""
    import cv2
    import numpy as np
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    x, y, bw, _ = box
    cx, cy = x + bw / 2, y + bw / 2 + bw * 0.08
    side = min(bw * 1.95, w, h)
    x0 = int(max(0, min(w - side, cx - side / 2)))
    y0 = int(max(0, min(h - side, cy - side / 2)))
    out = cv2.resize(img[y0:y0 + int(side), x0:x0 + int(side)], (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".webp", out, [cv2.IMWRITE_WEBP_QUALITY, 82])
    if not ok:
        raise ValueError("encodage WebP impossible")
    return bytes(buf)


def persons_to_process() -> dict[str, str]:
    """Personnes avec au moins une vérification, hors candidats 2027 (qui ont leur photo choisie à part)."""
    with (SEEDS_DIR / "candidates_2027.csv").open(encoding="utf-8") as f:
        candidates = {r["person_id"] for r in csv.DictReader(f) if r["person_id"]}
    names: dict[str, str] = {}
    for fact in json.loads(EXPORT_FACTS.read_text(encoding="utf-8")):
        p = fact["person"]
        if p["id"].startswith("Q") and p["id"] not in candidates:
            names[p["id"]] = p["name"]
    return names


def limited(r: httpx.Response) -> bool:
    """Refus temporaire de Wikimedia : 429, ou 403 « robot policy » (même limite de débit, autre habillage), ou panne."""
    return r.status_code in (429, 500, 502, 503, 504) or (r.status_code == 403 and "robot policy" in r.text)


def _get(client: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
    time.sleep(PAUSE_SECONDS)
    return client.get(url, **kwargs)


def wikidata_images(client: httpx.Client, ids: list[str]) -> dict[str, str]:
    """Identifiant Wikidata -> titre Commons de l'image principale (P18), pour ceux qui en ont une."""
    found: dict[str, str] = {}
    for i in range(0, len(ids), 150):
        query = "SELECT ?p ?img WHERE { VALUES ?p { %s } ?p wdt:P18 ?img }" % " ".join("wd:" + q for q in ids[i:i + 150])
        r = _get(client, SPARQL_URL, params={"format": "json", "query": query})
        if limited(r):
            raise RateLimited(SPARQL_URL)
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            title = "File:" + httpx.URL(b["img"]["value"]).path.rsplit("/", 1)[-1]
            found.setdefault(b["p"]["value"].rsplit("/", 1)[1], unquote(title).replace("_", " "))
    return found


def commons_info(client: httpx.Client, titles: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(titles), 50):
        r = _get(client, COMMONS_API, params={
            "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size|extmetadata",
            "iiurlwidth": 500, "titles": "|".join(titles[i:i + 50])})
        if limited(r):
            raise RateLimited(COMMONS_API)
        r.raise_for_status()
        out |= parse_imageinfo(r.json())
    return out


def download(client: httpx.Client, title: str, meta: dict[str, Any]) -> bytes:
    """Image en 500 px par plusieurs chemins officiels, dans l'ordre ; RateLimited si tous refusent."""
    name = quote(title[5:].replace(" ", "_"))
    routes = [meta["thumb"], f"https://commons.wikimedia.org/w/thumb.php?f={name}&w=500",
              f"https://fr.wikipedia.org/wiki/Special:FilePath/{name}?width=500"] if meta["w"] >= 500 else [meta["url"]]
    for route in routes:
        r = _get(client, route, follow_redirects=True)
        if r.status_code == 200:
            return r.content
        if not limited(r):
            r.raise_for_status()
    raise RateLimited(title)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def status(names: dict[str, str], state: dict[str, Any]) -> dict[str, int]:
    done = [p for p in names if p in state]
    counts = {s: sum(state[p]["status"] == s for p in done) for s in (OK, NO_PHOTO, NOT_FREE, NO_FACE)}
    return {"personnes": len(names), "traitées": len(done), "restantes": len(names) - len(done), **counts}


def run(max_images: int = 20, client: httpx.Client | None = None, today: date | None = None,
        names: dict[str, str] | None = None) -> dict[str, Any]:
    """Un lot : décide pour toutes les personnes sans photo ni image (instantané), puis télécharge au plus
    `max_images` images. Écrit l'état au fur et à mesure (un refus de Wikimedia ne perd rien)."""
    names = names if names is not None else persons_to_process()
    state, credits = load_json(STATE_PATH), load_json(CREDITS_PATH)
    stamp = (today or date.today()).isoformat()
    owns = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=90)
    stopped = False
    try:
        pending = sorted(p for p in names if p not in state)
        if pending:
            try:
                titles = wikidata_images(client, pending)
                for pid in pending:
                    if pid not in titles:
                        state[pid] = {"status": NO_PHOTO, "on": stamp}
                with_photo = [p for p in pending if p in titles]
                info = commons_info(client, sorted({titles[p] for p in with_photo}))
                for pid in with_photo:
                    meta = info.get(titles[pid])
                    if meta is None or not meta["free"]:
                        state[pid] = {"status": NOT_FREE, "on": stamp}
                save_json(STATE_PATH, state)
                todo = [p for p in with_photo if p not in state][:max_images]
                for pid in todo:
                    meta = info[titles[pid]]
                    data = download(client, titles[pid], meta)
                    face = detect_face(data)
                    if usable_face(face):
                        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                        (IMAGES_DIR / f"{pid}.webp").write_bytes(crop_webp(data, face["box"]))
                        credits[pid] = {k: meta[k] for k in ("author", "license", "license_url", "date", "page")}
                        credits[pid]["title"] = titles[pid]
                        state[pid] = {"status": OK, "on": stamp}
                    else:
                        state[pid] = {"status": NO_FACE, "on": stamp}
                    save_json(STATE_PATH, state)
                    save_json(CREDITS_PATH, credits)
            except (RateLimited, httpx.TransportError):
                stopped = True
    finally:
        save_json(STATE_PATH, state)
        save_json(CREDITS_PATH, credits)
        if owns:
            client.close()
    return {**status(names, state), "limité": stopped}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max", type=int, default=20, help="images à télécharger au plus par passage")
    parser.add_argument("--status", action="store_true", help="affiche l'avancement sans rien télécharger")
    args = parser.parse_args()
    names = persons_to_process()
    if args.status:
        print(status(names, load_json(STATE_PATH)))
        return
    result = run(args.max, names=names)
    print(result)
    if result["limité"]:
        print("Wikimedia limite l'accès : lot interrompu, reprise au prochain passage.")


if __name__ == "__main__":
    main()
