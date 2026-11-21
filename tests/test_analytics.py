import tempfile
import unittest
from pathlib import Path

from tennishub.analytics import head_to_head, player_search, points_history
from tennishub.database import connect
from tennishub.importer import import_bundle
from tests.test_importer import AS_OF, RANKING_DATE, RANKINGS, row, resource


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.connection = connect(Path(self.temporary.name) / "tennis.sqlite3")
        self.addCleanup(self.connection.close)
        self.load(2025, [row(tourney_id="2025-1", tourney_date="20250201", round="F")])
        self.load(2026, [row(tourney_id="2026-1", round="F")])
        self.main = [row(tourney_id="2026-1", round="F", winner_id="S0AG", winner_name="Jannik Sinner", loser_id="Z355", loser_name="Alexander Zverev"),
                     row(tourney_id="2026-2", round="F", surface="Clay"),
                     row(tourney_id="2026-3", round="F", surface="Grass", score="6-4 1-0 RET"),
                     row(tourney_id="2026-4", round="F", surface="Clay", score="W/O", winner_id="S0AG", winner_name="Jannik Sinner", loser_id="Z355", loser_name="Alexander Zverev")]
        self.qualifying = [row(tourney_id="2026-5", round="Q1", surface="Clay", winner_id="S0AG", winner_name="Jannik Sinner", loser_id="Z355", loser_name="Alexander Zverev")]
        self.load(2026, self.main, self.qualifying)

    def load(self, year, main, qualifying=None):
        datasets = [resource(f"{year}.csv", main)]
        if qualifying:
            datasets.append(resource(f"atp_quali/{year}_atp_quali.csv", qualifying))
        return import_bundle(self.connection, year, AS_OF, RANKING_DATE, RANKINGS, datasets, datasets)

    def test_latest_snapshot_once_per_year_and_retirements_count(self):
        result = head_to_head(self.connection, "Z355", "S0AG")
        self.assertEqual(result["summary"], {"matches": 5, "first_wins": 3, "second_wins": 2, "excluded_results": 1})
        self.assertEqual([item["year"] for item in result["coverage"]], [2025, 2026])
        self.assertEqual(len(result["matches"]), 6)

    def test_surface_year_and_stage_filters_combine(self):
        result = head_to_head(self.connection, "Alexander Zverev", "Sinner", year=2026, surface="Clay", stage="main")
        self.assertEqual(result["summary"]["matches"], 1)
        self.assertEqual(result["summary"]["first_wins"], 1)
        self.assertEqual(result["summary"]["excluded_results"], 1)
        self.assertEqual(len(result["matches"]), 2)
        self.assertEqual(head_to_head(self.connection, "Z355", "S0AG", surface="Carpet")["summary"]["matches"], 0)

    def test_swapping_players_reverses_record_but_keeps_matches(self):
        a = head_to_head(self.connection, "Z355", "S0AG")
        b = head_to_head(self.connection, "S0AG", "Z355")
        self.assertEqual(a["summary"]["first_wins"], b["summary"]["second_wins"])
        self.assertEqual(a["matches"], b["matches"])

    def test_invalid_and_ambiguous_selections_do_not_fabricate_results(self):
        for first, second, options in [("Z355", "Z355", {}), ("missing", "S0AG", {}), ("Z355", "S0AG", {"surface":"invalid"}), ("Z355", "S0AG", {"year":2024})]:
            with self.assertRaises(ValueError):
                head_to_head(self.connection, first, second, **options)

    def test_search_can_find_opponents_outside_the_top_50(self):
        self.connection.execute("INSERT INTO players VALUES ('OUT1', 'Other Player', 'ITA', 'other player')")
        self.assertEqual(player_search(self.connection, "Other")["players"][0]["id"], "OUT1")
        self.assertEqual(player_search(self.connection, "does-not-exist")["players"], [])

    def test_history_keeps_unknown_values_distinct_from_zero(self):
        report = points_history(self.connection, "Z355")
        self.assertEqual(report["points_kind"], "earned_in_tournaments")
        earlier, current = report["seasons"]
        self.assertEqual(earlier["total"], 500)
        self.assertEqual(current["known_subtotal"], 1330)
        self.assertIsNone(current["total"])
        self.assertEqual(current["unknown_events"], 1)
        self.assertEqual(current["calculated_events"], 4)
        self.assertEqual(current["timeline"][-1]["cumulative_known_points"], 1330)
        self.assertTrue(any(event["earned_points"] == 0 for event in current["timeline"]))
        self.assertTrue(any(event["earned_points"] is None for event in current["timeline"]))

    def test_no_recorded_events_does_not_claim_a_complete_zero_total(self):
        self.connection.execute("INSERT INTO players VALUES ('OUT1', 'Other Player', 'ITA', 'other player')")
        reports = points_history(self.connection, "OUT1")["seasons"]
        self.assertTrue(all(item["events"] == 0 and item["total"] is None for item in reports))

    def test_unvalidated_year_is_unavailable_instead_of_a_zero_total(self):
        self.load(2024, [row(tourney_id="2024-1", tourney_date="20240201", round="F")])
        series = points_history(self.connection, "Z355")["seasons"][0]
        self.assertIsNone(series["total"])
        self.assertEqual(series["calculated_events"], 0)
        self.assertIsNone(series["timeline"][0]["earned_points"])


if __name__ == "__main__":
    unittest.main()
