import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from pipeline.build_beta import write_open_data

FACT = {"id": "c_1", "person": {"id": "Q1", "name": "Marine Le Pen", "votona_id": "lepen"},
        "party": {"id": "Q2", "name": "Rassemblement national", "short_name": "RN", "status": "ok"},
        "claim_text": "La dette <explose>", "claim_date": "2026-10-01", "date_is_fallback": False,
        "verdict": "false", "theme": "Économie & travail",
        "votona_topics": [{"slug": "reduire-la-dette", "label": "Réduire la dette"}],
        "reviews": [{"source_id": "afp", "source_name": "AFP Factuel", "url": "https://a/1", "title": "T",
                     "rating_original": "Faux", "rating_normalized": "false", "review_date": "2026-10-02"},
                    {"source_id": "tf1", "source_name": "TF1 Info", "url": "https://b/1", "title": "T2",
                     "rating_original": "Faux", "rating_normalized": "false", "review_date": "2026-10-03"}]}


def test_open_data_one_row_per_review_and_valid_rss(tmp_path):
    write_open_data([FACT], datetime(2026, 10, 22, tzinfo=timezone.utc), tmp_path)
    rows = list(csv.DictReader((tmp_path / "donnees" / "facts.csv").open(encoding="utf-8")))
    assert [r["source_id"] for r in rows] == ["afp", "tf1"]
    assert rows[0]["rating_original"] == "Faux" and rows[0]["votona_topics"] == "reduire-la-dette"
    item = ET.parse(tmp_path / "flux.xml").getroot().find("channel/item")
    assert item.findtext("link") == "https://b/1"  # vérification la plus récente
    assert "<explose>" in item.findtext("title")
    assert "« Faux » selon AFP Factuel" in item.findtext("description")
