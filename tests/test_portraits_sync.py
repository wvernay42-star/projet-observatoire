import json

import cv2
import httpx
import numpy as np
import pytest
import respx

from pipeline import portraits_sync as ps


def jpeg(w: int = 600, h: int = 800) -> bytes:
    ok, buf = cv2.imencode(".jpg", np.random.default_rng(1).integers(0, 255, (h, w, 3), dtype=np.uint8))
    assert ok
    return bytes(buf)


def imageinfo(title: str, license_name: str = "CC BY-SA 4.0") -> dict:
    return {"query": {"normalized": [{"from": title, "to": title}], "pages": {"1": {"title": title, "imageinfo": [{
        "width": 3000, "thumburl": "https://upload.wikimedia.org/thumb/x/500px-a.jpg", "url": "https://upload.wikimedia.org/x/a.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/" + title,
        "extmetadata": {"LicenseShortName": {"value": license_name}, "LicenseUrl": {"value": "https://cc/x"},
                        "Artist": {"value": '<a href="u">Jeanne <b>Photo</b></a>'}, "DateTimeOriginal": {"value": "2025-06-09 10:00"}}}]}}}}


def sparql(images: dict[str, str]) -> dict:
    return {"results": {"bindings": [{"p": {"value": "http://www.wikidata.org/entity/" + q},
                                      "img": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/" + f}} for q, f in images.items()]}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(ps, "CREDITS_PATH", tmp_path / "credits.json")
    monkeypatch.setattr(ps, "IMAGES_DIR", tmp_path / "img")
    monkeypatch.setattr(ps, "PAUSE_SECONDS", 0)
    monkeypatch.setattr(ps, "detect_face", lambda data: {"n": 1, "w": 600, "h": 800, "box": (200, 150, 200, 200)})
    return tmp_path


def test_parse_imageinfo_cleans_author_and_flags_licence():
    info = ps.parse_imageinfo(imageinfo("File:A.jpg"))["File:A.jpg"]
    assert info["author"] == "Jeanne Photo" and info["free"] and info["date"] == "2025-06-09"
    assert not ps.parse_imageinfo(imageinfo("File:A.jpg", "All rights reserved"))["File:A.jpg"]["free"]
    assert ps.is_free("CC0") and ps.is_free("European Parliament") and not ps.is_free("")


def test_usable_face_needs_one_big_centred_face():
    base = {"w": 500, "h": 600}
    assert ps.usable_face({**base, "n": 1, "box": (150, 100, 200, 200)})
    assert not ps.usable_face({**base, "n": 2, "box": (150, 100, 200, 200)})   # photo de groupe
    assert not ps.usable_face({**base, "n": 1, "box": (150, 100, 40, 40)})     # visage trop petit
    assert not ps.usable_face({**base, "n": 1, "box": (0, 100, 120, 120)})     # décentré
    assert not ps.usable_face(None)


def test_crop_is_a_192_square_webp():
    out = cv2.imdecode(np.frombuffer(ps.crop_webp(jpeg(), (200, 150, 200, 200)), np.uint8), cv2.IMREAD_COLOR)
    assert out.shape[:2] == (ps.SIZE, ps.SIZE)


@respx.mock
def test_run_decides_everyone_and_respects_the_cap(env):
    respx.get(ps.SPARQL_URL).mock(return_value=httpx.Response(200, json=sparql({"Q1": "A.jpg", "Q3": "B.jpg"})))
    respx.get(ps.COMMONS_API).mock(return_value=httpx.Response(200, json={"query": {"pages": {
        **imageinfo("File:A.jpg")["query"]["pages"], "2": {**imageinfo("File:B.jpg", "All rights reserved")["query"]["pages"]["1"]}}}}))
    respx.get(url__regex=r"https://upload\.wikimedia\.org/.*").mock(return_value=httpx.Response(200, content=jpeg()))
    names = {"Q1": "Un", "Q2": "Deux", "Q3": "Trois"}
    result = ps.run(1, names=names)
    state = json.loads((env / "state.json").read_text())
    assert {p: v["status"] for p, v in state.items()} == {"Q1": "ok", "Q2": "no_photo", "Q3": "not_free"}
    assert result["restantes"] == 0 and not result["limité"]
    credit = json.loads((env / "credits.json").read_text())["Q1"]
    assert credit["author"] == "Jeanne Photo" and credit["license"] == "CC BY-SA 4.0" and (env / "img" / "Q1.webp").exists()
    assert not (env / "img" / "Q3.webp").exists()                    # licence non libre : jamais reprise


@respx.mock
def test_run_stops_cleanly_when_wikimedia_refuses_and_resumes(env):
    respx.get(ps.SPARQL_URL).mock(return_value=httpx.Response(200, json=sparql({"Q1": "A.jpg"})))
    respx.get(ps.COMMONS_API).mock(return_value=httpx.Response(200, json=imageinfo("File:A.jpg")))
    image = respx.get(url__regex=r"https://(upload\.wikimedia\.org|commons\.wikimedia\.org/w/thumb|fr\.wikipedia\.org/wiki/Special).*")
    image.mock(return_value=httpx.Response(429))
    first = ps.run(5, names={"Q1": "Un"})
    assert first["limité"] and first["restantes"] == 1 and not (env / "img").exists()
    image.mock(return_value=httpx.Response(200, content=jpeg()))
    second = ps.run(5, names={"Q1": "Un"})
    assert not second["limité"] and second["restantes"] == 0 and (env / "img" / "Q1.webp").exists()
    again = ps.run(5, names={"Q1": "Un"})                            # rien à refaire : aucune requête de plus
    assert again["traitées"] == 1


def test_others_portraits_are_hidden_until_enabled(tmp_path, monkeypatch):
    from pipeline import build_pages
    (tmp_path / "img").mkdir()
    for key in ("lepen", "Q5"):
        (tmp_path / "img" / f"{key}.webp").write_bytes(b"x")
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    (seeds / "portraits.json").write_text(json.dumps({"lepen": {"license": "CC0"}, "Q5": {"license": "CC0"}}), encoding="utf-8")
    monkeypatch.setattr(build_pages, "SEEDS_DIR", seeds)
    monkeypatch.setattr(build_pages, "PORTRAITS_DIR", tmp_path / "img")
    monkeypatch.setattr(build_pages, "OTHERS_PORTRAITS", False)
    assert set(build_pages.load_portraits({"lepen"})) == {"lepen"}
    monkeypatch.setattr(build_pages, "OTHERS_PORTRAITS", True)
    assert set(build_pages.load_portraits({"lepen"})) == {"lepen", "Q5"}


@respx.mock
def test_robot_policy_403_is_a_temporary_refusal_not_a_crash(env):
    respx.get(ps.SPARQL_URL).mock(return_value=httpx.Response(403, text="Please respect our robot policy https://w.wiki/4wJS"))
    result = ps.run(5, names={"Q1": "Un"})
    assert result["limité"] and result["restantes"] == 1
    respx.get(ps.SPARQL_URL).mock(return_value=httpx.Response(403, text="Forbidden"))   # autre 403 : vraie erreur
    with pytest.raises(httpx.HTTPStatusError):
        ps.run(5, names={"Q1": "Un"})
