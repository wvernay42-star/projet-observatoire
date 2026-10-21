import csv
import shutil
from pathlib import Path

from pipeline.attribute import Referential
from pipeline.sync_candidates import FIELDS, parse_votona, sync

HTML = '''
  { id:"lepen", name:"Marine Le Pen", party:"Rassemblement National", color:"#2457A6",
  { id:"faure", name:"Olivier Faure", party:"Parti socialiste", withdrawn:true, color:"#E33",
  { id:"nouveau", name:"Jean Nouveau", party:"Sans étiquette", color:"#123",
'''


def test_parse_votona_reads_withdrawals():
    rows = parse_votona(HTML)
    assert [(r["votona_id"], r["status"]) for r in rows] == [
        ("lepen", "déclaré ou pressenti"), ("faure", "retiré"), ("nouveau", "déclaré ou pressenti")]


def test_sync_updates_adds_and_never_deletes(tmp_path):
    def write(name, header, rows):
        with (tmp_path / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
    write("candidates_2027.csv", FIELDS, [
        ["lepen", "Marine Le Pen", "Rassemblement National", "déclaré ou pressenti", "Q12927", "sûr", "Q205150", "u"],
        ["faure", "Olivier Faure", "Parti socialiste", "déclaré ou pressenti", "Q3351018", "sûr", "Q170972", "u"],
        ["ancien", "Ancien Candidat", "X", "déclaré ou pressenti", "", "à confirmer", "", "u"]])
    write("parties.csv", ["id", "name", "short_name", "country", "parlgov_id", "inception", "dissolved"], [])
    report = sync(HTML, tmp_path, Referential([], []))
    rows = {r["votona_id"]: r for r in csv.DictReader((tmp_path / "candidates_2027.csv").open(encoding="utf-8"))}
    assert rows["faure"]["status"] == "retiré" and rows["faure"]["person_id"] == "Q3351018"
    assert rows["ancien"]["status"] == "retiré de la liste Votona"
    assert rows["nouveau"]["person_match"] == "à confirmer"
    assert report["ajoutés"] == ["Jean Nouveau"]
