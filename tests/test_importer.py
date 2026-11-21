import csv
import io
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tennishub.database import connect, latest_import
from tennishub.importer import import_bundle
from tennishub.queries import coverage, players, season
from tennishub.sources import Resource, SourceClient, digest, top_rankings

AS_OF = date(2026, 11, 18)
RANKING_DATE = date(2026, 11, 16)
RANKINGS = [
    {"id": "Z355", "name": "Alexander Zverev", "ioc": "GER", "rank": 1, "points": 9320},
    {"id": "S0AG", "name": "Jannik Sinner", "ioc": "ITA", "rank": 2, "points": 7950},
]


def row(**extra):
    return {"tourney_id": "2026-807", "tourney_name": "Acapulco", "tourney_date": "20260225",
            "tourney_level": "500", "draw_size": "32", "surface": "Hard", "round": "R32",
            "match_num": "1", "winner_id": "Z355", "winner_name": "Alexander Zverev", "winner_ioc": "GER",
            "loser_id": "S0AG", "loser_name": "Jannik Sinner", "loser_ioc": "ITA", "score": "6-4 6-4",
            "winner_entry": "", "loser_entry": "", **extra}


def resource(name, rows):
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=list(dict.fromkeys([*row(), *(key for item in rows for key in item)])))
    writer.writeheader()
    writer.writerows(rows)
    return Resource(name, "https://example.test/" + name, content.getvalue().encode(), "2026-11-18T00:00:00+00:00")


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.connection = connect(Path(self.temporary.name) / "tennis.sqlite3")
        self.addCleanup(self.connection.close)

    def run_import(self, datasets, rankings=RANKINGS, year=2026):
        return import_bundle(self.connection, year, AS_OF, RANKING_DATE, rankings, datasets, datasets)

    def test_davis_id_shared_by_different_ties_preserves_original_records(self):
        rows = [row(tourney_id="2026-D072", tourney_name="Davis Cup: GER vs ITA", tourney_level="D", round="RR"),
                row(tourney_id="2026-D072", tourney_name="Davis Cup: GER vs FRA", tourney_level="D", round="RR", loser_id="P003", loser_name="Other Player")]
        result = self.run_import([resource("2026.csv", rows)])
        self.assertEqual(result["matches"], 2)
        self.assertEqual(result["event_draws"], 2)
        self.assertEqual(result["issues"]["team_tie_identity"], 2)
        stored = self.connection.execute("SELECT edition_id, raw_json FROM matches").fetchall()
        self.assertEqual(len({item["edition_id"] for item in stored}), 2)
        self.assertTrue(all(json.loads(item["raw_json"])["tourney_id"] == "2026-D072" for item in stored))
        report = season(self.connection, "Z355", 2026)
        self.assertEqual(len(report["events"]), 2)
        self.assertTrue(all(event["earned_points"] == 0 for event in report["events"]))
        self.assertTrue(self.run_import([resource("2026.csv", rows)])["reused"])

    def test_missing_surface_uses_known_metadata_of_same_event(self):
        for first, second in (("", "Hard"), ("Hard", "")):
            data = [row(surface=first), row(surface=second, round="R16", loser_id="P003", loser_name="Other Player")]
            result = self.run_import([resource("2026.csv", data)])
            report = season(self.connection, "Z355", 2026)
            self.assertEqual(report["events"][0]["surface"], "Hard")
            self.assertEqual({match["raw"]["surface"] for match in report["events"][0]["matches"]}, {"", "Hard"})
            self.assertEqual(result["issues"]["event_surface_completed"], 1)

    def test_conflicting_known_surfaces_are_not_reconciled(self):
        with self.assertRaisesRegex(ValueError, "Metadati"):
            self.run_import([resource("2026.csv", [row(), row(surface="Clay", round="R16")])])

    def test_non_team_metadata_conflicts_are_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "Metadati"):
            self.run_import([resource("2026.csv", [row(), row(tourney_name="Other tournament", loser_id="P003", loser_name="Other Player")])])
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 0)

    def test_duplicate_statistics_can_fill_blanks_without_losing_zero(self):
        data = [resource("2026.csv", [row(w_ace="", l_ace="0"), row(w_ace="14", l_ace="", match_num="2")])]
        result = self.run_import(data)
        self.assertEqual(result["matches"], 1)
        self.assertEqual(result["issues"]["duplicate_enrichment"], 1)
        match = season(self.connection, "Z355", 2026)["events"][0]["matches"][0]
        self.assertEqual((match["raw"]["w_ace"], match["raw"]["l_ace"]), ("14", "0"))
        self.assertEqual(len(match["sources"]), 2)

    def test_conflicting_nonempty_statistics_still_abort(self):
        with self.assertRaisesRegex(ValueError, "discordanti"):
            self.run_import([resource("2026.csv", [row(w_ace="14"), row(w_ace="16")])])
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 0)

    def test_conflicting_draw_size_keeps_results_but_blocks_points(self):
        rows = [row(draw_size="28"), row(draw_size="32", round="R16", winner_id="P003", winner_name="Other Player", loser_id="Z355", loser_name="Alexander Zverev")]
        result = self.run_import([resource("2026.csv", rows)])
        self.assertEqual(result["matches"], 2)
        self.assertEqual(result["issues"]["draw_size_conflict"], 1)
        event = season(self.connection, "Z355", 2026)["events"][0]
        self.assertIsNone(event["earned_points"])
        self.assertIn("discordante", event["points_reason"])
        self.assertEqual({match["raw"]["draw_size"] for match in event["matches"]}, {"28", "32"})

    def test_event_name_case_variant_does_not_drop_match(self):
        result = self.run_import([resource("2026.csv", [row(tourney_name="ATP Cup"), row(tourney_name="Atp Cup", round="R16", loser_id="P003", loser_name="Other Player")])])
        self.assertEqual((result["matches"], result["event_draws"]), (2, 1))
        self.assertEqual(result["issues"]["event_label_variant"], 1)
        self.assertEqual({match["raw"]["tourney_name"] for match in season(self.connection, "Z355", 2026)["events"][0]["matches"]}, {"ATP Cup", "Atp Cup"})

    def test_historical_team_cups_do_not_create_individual_titles(self):
        for year, code in ((2010, "615"), (2020, "8888")):
            self.run_import([resource(f"{year}.csv", [row(tourney_id=f"{year}-{code}", tourney_date=f"{year}0201", tourney_level="A", round="F")])], year=year)
            report = season(self.connection, "Z355", year)
            self.assertEqual(report["summary"]["titles"], 0)
            self.assertEqual(report["events"][0]["competition_type"], "team")

    def test_generic_a_category_does_not_imply_team_competition(self):
        self.run_import([resource("2024.csv", [row(tourney_id="2024-451", tourney_date="20240201", tourney_name="Doha", tourney_level="A", round="F")])], year=2024)
        report = season(self.connection, "Z355", 2024)
        self.assertEqual(report["events"][0]["competition_type"], "individual")
        self.assertIsNone(report["events"][0]["earned_points"])

    def test_dusseldorf_reusing_world_team_id_is_individual_after_2012(self):
        self.run_import([resource("2013.csv", [row(tourney_id="2013-615", tourney_date="20130501", tourney_name="Dusseldorf", tourney_level="250", round="F")])], year=2013)
        report = season(self.connection, "Z355", 2013)
        self.assertEqual(report["events"][0]["competition_type"], "individual")
        self.assertEqual(report["summary"]["titles"], 1)

    def test_repeat_import_does_not_duplicate_rows(self):
        data = [resource("2026.csv", [row()])]
        first = self.run_import(data)
        second = self.run_import(data)
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM matches").fetchone()[0], 1)

    def test_duplicate_sources_keep_both_provenances(self):
        result = self.run_import([resource("2026.csv", [row()]), resource("ongoing_tourneys.csv", [row()])])
        self.assertEqual(result["matches"], 1)
        self.assertEqual(result["duplicates_removed"], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM match_sources").fetchone()[0], 2)

    def test_alias_for_same_id_is_reported_without_duplicate_match(self):
        data = [resource("2026.csv", [row(), row(loser_name="Jannik Sínner", match_num="23")])]
        result = self.run_import(data)
        self.assertEqual(result["matches"], 1)
        self.assertEqual(result["issues"]["duplicate_variant"], 1)
        self.assertEqual(len(season(self.connection, "Z355", 2026)["events"][0]["matches"][0]["sources"]), 2)

    def test_conflict_preserves_previous_import(self):
        first = self.run_import([resource("2026.csv", [row()])])
        with self.assertRaisesRegex(ValueError, "discordanti"):
            self.run_import([resource("2026.csv", [row(), row(score="6-0 6-0")])])
        self.assertEqual(latest_import(self.connection)["id"], first["import_id"])
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 1)

    def test_database_failure_rolls_back_partial_import(self):
        first = self.run_import([resource("2026.csv", [row()])])
        invalid_ranks = [RANKINGS[0], {**RANKINGS[1], "rank": 1}]
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_import([resource("2026.csv", [row(score="6-3 6-3")])], rankings=invalid_ranks)
        self.assertEqual(latest_import(self.connection)["id"], first["import_id"])
        self.assertEqual(self.connection.execute("SELECT count(*) FROM sources").fetchone()[0], 1)

    def test_source_correction_creates_snapshot_without_old_result_leaking(self):
        self.run_import([resource("2026.csv", [row()])])
        new = self.run_import([resource("2026.csv", [row(score="6-2 6-2")])])
        result = season(self.connection, "Z355", 2026)
        self.assertEqual(result["import_id"], new["import_id"])
        self.assertEqual(result["summary"]["matches_recorded"], 1)
        self.assertEqual(result["events"][0]["matches"][0]["score_winner_first"], "6-2 6-2")
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 2)

    def test_invalid_identity_is_reported_and_missing_round_is_preserved(self):
        result = self.run_import([resource("2026.csv", [row(round=""), row(loser_id="", round="R16")])])
        self.assertEqual(result["matches"], 1)
        self.assertEqual(result["issues"]["incomplete_identity"], 1)
        self.assertEqual(result["issues"]["missing_round"], 1)
        event = season(self.connection, "Z355", 2026)["events"][0]
        self.assertEqual(event["placement"], "Da verificare")
        self.assertIsNone(event["earned_points"])

    def test_future_and_other_season_are_excluded(self):
        result = self.run_import([resource("2026.csv", [row(), row(tourney_date="20261120", round="F"), row(tourney_id="2025-807")])])
        self.assertEqual(result["matches"], 1)
        self.assertEqual(result["excluded_by_date_or_season"], 2)

    def test_qualifying_and_main_draw_are_one_participation_with_unknown_points(self):
        result = self.run_import([resource("2026.csv", [row()]), resource("atp_quali/2026_atp_quali.csv", [row(round="Q2")])])
        self.assertEqual(result["event_draws"], 2)
        report = season(self.connection, "Z355", 2026)
        self.assertEqual(report["summary"]["events"], 1)
        self.assertEqual(report["summary"]["matches_recorded"], 2)
        self.assertIsNone(report["events"][0]["earned_points"])

    def test_points_are_calculated_for_requested_player(self):
        self.run_import([resource("2026.csv", [row(round="R16")])])
        sinner = season(self.connection, "S0AG", 2026)
        self.assertEqual(sinner["events"][0]["earned_points"], 50)
        self.assertEqual(sinner["summary"]["losses"], 1)
        self.assertIsNone(season(self.connection, "Z355", 2026)["events"][0]["earned_points"])

    def test_unverified_year_does_not_use_current_points(self):
        self.run_import([resource("2024.csv", [row(tourney_id="2024-807", tourney_date="20240225", round="R16")])], year=2024)
        self.assertIsNone(season(self.connection, "S0AG", 2024)["events"][0]["earned_points"])

    def test_first_round_wild_card_at_slam_receives_zero_points(self):
        self.run_import([resource("2026.csv", [row(tourney_level="G", draw_size="128", round="R128", loser_entry="WC")])])
        report = season(self.connection, "S0AG", 2026)
        self.assertEqual(report["events"][0]["earned_points"], 0)
        self.assertEqual(report["events"][0]["points_status"], "calculated")

    def test_missing_elimination_does_not_invent_a_placement(self):
        final = row(round="F", winner_id="B001", winner_name="Other winner", loser_id="B002", loser_name="Other finalist")
        self.run_import([resource("2026.csv", [row(round="SF"), final])])
        report = season(self.connection, "Z355", 2026)
        self.assertEqual(report["events"][0]["placement"], "Da verificare")
        self.assertIsNone(report["events"][0]["earned_points"])

    def test_name_search_ignores_accents_and_preserves_ranking_date(self):
        self.run_import([resource("2026.csv", [row()])], rankings=[RANKINGS[0], {**RANKINGS[1], "name": "Jannik Sínner"}])
        found = players(self.connection, "sinner")
        self.assertEqual(found["ranking_date"], "2026-11-16")
        self.assertEqual(found["players"][0]["id"], "S0AG")

    def test_coverage_counts_unknown_values_separately_from_zero(self):
        self.run_import([resource("2026.csv", [row(round="R32")])])
        report = coverage(self.connection, 2026)
        self.assertEqual(report["participations"], 2)
        self.assertEqual(report["calculated"], 1)
        self.assertEqual(report["needs_review"], 1)
        self.assertEqual(report["unresolved"][0]["player_id"], "Z355")

    def test_qualifying_elimination_has_final_status(self):
        self.run_import([resource("atp_quali/2026_atp_quali.csv", [row(round="Q1")])])
        event = season(self.connection, "S0AG", 2026)["events"][0]
        self.assertFalse(event["provisional"])
        self.assertEqual(event["points_breakdown"], {"main_draw": 0, "qualifying": 0})

    def test_matches_follow_qualifying_then_main_draw_rounds(self):
        self.run_import([resource("2026.csv", [row(round="R32")]),
                         resource("atp_quali/2026_atp_quali.csv", [row(round="Q2"), row(round="Q1")])])
        report = season(self.connection, "Z355", 2026)
        self.assertEqual([match["round"] for match in report["events"][0]["matches"]], ["Q1", "Q2", "R32"])


class SourceTests(unittest.TestCase):
    def test_top_50_are_selected_by_position_not_response_order(self):
        rows = [{"id": f"P{rank:03}", "name": f"Player {rank}", "rank": rank, "points": 2000 - rank} for rank in range(51, 0, -1)]
        source = Resource("rankings", "https://example.test", json.dumps({"rankings": rows}).encode(), "now")
        selected = top_rankings(source)
        self.assertEqual(len(selected), 50)
        self.assertEqual(selected[0]["rank"], 1)
        self.assertEqual(selected[-1]["rank"], 50)

    def test_incomplete_top_50_is_rejected(self):
        source = Resource("rankings", "https://example.test", b'{"rankings": []}', "now")
        with self.assertRaisesRegex(ValueError, "1–50"):
            top_rankings(source)

    def test_corrupted_offline_cache_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "refs").mkdir()
            (root / "objects").mkdir()
            source = Resource("test", "https://example.test", b"expected", "now")
            (root / "refs" / (digest(source.url.encode()) + ".json")).write_text(json.dumps(source.metadata()))
            (root / "objects" / source.sha256).write_bytes(b"corrupted")
            with self.assertRaisesRegex(ValueError, "Cache non valida"):
                SourceClient(root, offline=True).get("test", source.url)


if __name__ == "__main__":
    unittest.main()
