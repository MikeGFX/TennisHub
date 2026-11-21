import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tennishub.database import connect, latest_import
from tennishub.importer import import_bundle
from tennishub.queries import season
from tennishub.sources import csv_rows
from tennishub.supplements import load_supplements, ROOT
from tests.test_importer import AS_OF, RANKING_DATE, row, resource


class SupplementTests(unittest.TestCase):
    def test_canberra_adds_missing_participation_without_double_bonus(self):
        directory=self.enterContext(tempfile.TemporaryDirectory())
        connection=connect(Path(directory)/"test.sqlite3")
        self.addCleanup(connection.close)
        extra,provenance=load_supplements(2026,AS_OF)
        main=resource("2026_challenger.csv",[row(tourney_id="2026-7393",tourney_name="Canberra",tourney_date="20260105",tourney_level="C",draw_size="32",round="F",winner_id="B0PG",winner_name="Alexander Blockx",loser_id="J0DZ",loser_name="Rafael Jodar",loser_entry="Q")])
        roster=[{"id":"F0DM","name":"Arthur Fery","ioc":"GBR","rank":1,"points":100},{"id":"J0DZ","name":"Rafael Jodar","ioc":"ESP","rank":2,"points":90}]
        before=import_bundle(connection,2026,AS_OF,RANKING_DATE,roster,[main],[main])
        old=season(connection,"J0DZ",2026)["events"][0]["earned_points"]
        datasets=[main,*extra];sources=[main,*provenance]
        after=import_bundle(connection,2026,AS_OF,RANKING_DATE,roster,datasets,sources)
        fery=season(connection,"F0DM",2026)["events"][0]
        jodar=season(connection,"J0DZ",2026)["events"][0]
        self.assertEqual(fery["earned_points"],3)
        self.assertEqual(fery["placement"],"Qualificazioni: Q2")
        self.assertEqual((fery["wins"],fery["losses"]),(1,1))
        self.assertFalse(fery["provisional"])
        self.assertEqual(len(fery["matches"]),2)
        self.assertTrue(all(m["stage"]=="qualifying" for m in fery["matches"]))
        self.assertEqual(jodar["earned_points"],old)
        self.assertEqual(jodar["points_breakdown"],{"main_draw":64,"qualifying":5})
        self.assertEqual(len(jodar["matches"]),3)
        self.assertEqual(after["matches"]-before["matches"],3)
        self.assertTrue(import_bundle(connection,2026,AS_OF,RANKING_DATE,roster,datasets,sources)["reused"])
        self.assertEqual(connection.execute("SELECT count(*) FROM imports").fetchone()[0],2)
        self.assertEqual(connection.execute("SELECT count(*) FROM matches WHERE import_id=?",(before["import_id"],)).fetchone()[0],1)
        self.assertTrue(all("curated" in m["sources"][0]["source_name"] for m in fery["matches"]))

    def test_does_not_apply_before_documented_availability_or_wrong_year(self):
        self.assertEqual(load_supplements(2026,date(2026,1,9)),([],[]))
        self.assertEqual(load_supplements(2025,AS_OF),([],[]))

    def test_modified_transcription_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"2026.json").write_bytes((ROOT/"2026.json").read_bytes())
            (root/"2026-canberra-qualifying.csv").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError,"Hash"):
                load_supplements(2026,AS_OF,root)

    def test_shared_qualifying_final_is_present_only_once(self):
        datasets,_=load_supplements(2026,AS_OF)
        rows=[row for _,row in csv_rows(datasets[0])]
        self.assertEqual(len(rows),3)
        self.assertEqual(sum(r["round"]=="Q2" for r in rows),1)
        self.assertTrue(all(r["source_date_precision"]=="tournament_week" for r in rows))

    def test_missing_qualifier_marker_is_completed_by_verified_path(self):
        from tennishub.points import evaluate_points
        main=row(tourney_id="2026-7393",tourney_name="Canberra",tourney_level="C",round="F",draw_size="32",winner_id="B0PG",loser_id="J0DZ",loser_entry="")
        datasets,_=load_supplements(2026,AS_OF)
        extra=[{"raw":r,"stage":"qualifying"} for _,r in csv_rows(datasets[0]) if "J0DZ" in (r["winner_id"],r["loser_id"])]
        self.assertEqual(evaluate_points([{"raw":main,"stage":"main"}],"J0DZ").value,64)
        self.assertEqual(evaluate_points([{"raw":main,"stage":"main"},*extra],"J0DZ").value,69)

    def test_unverified_qualifying_format_remains_unknown(self):
        from tennishub.points import evaluate_points
        datasets,_=load_supplements(2026,AS_OF)
        extra=[{"raw":r,"stage":"qualifying"} for _,r in csv_rows(datasets[0]) if "F0DM" in (r["winner_id"],r["loser_id"])]
        evidence={"2026-7393":{"level":125,"source":"https://example.test/level"}}
        self.assertIsNone(evaluate_points(extra,"F0DM",editions=evidence).value)
