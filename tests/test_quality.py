import json
import tempfile
import unittest
from pathlib import Path

from tennishub.database import connect, latest_import
from tennishub.importer import import_bundle
from tennishub.quality import assess_season, assess_range, inventory_status
from tests.test_importer import AS_OF, RANKING_DATE, RANKINGS, row, resource


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.connection = connect(Path(self.temp.name) / "tennis.sqlite3")
        self.addCleanup(self.connection.close)
        self.load(2025)

    def load(self, year):
        datasets = [resource(f"{year}.csv", [row(tourney_id=f"{year}-1", tourney_date=f"{year}0201", round="F")]),
                    resource(f"{year}_challenger.csv", []), resource(f"atp_quali/{year}_atp_quali.csv", [])]
        import_bundle(self.connection,year,AS_OF,RANKING_DATE,RANKINGS,datasets,datasets)

    def review(self, year):
        snapshot = latest_import(self.connection,year)
        return {"seasons": {str(year): {"inventory_verified":True,"import_id":snapshot["id"],
                "all_atp_tiers_included":True,"inventory_sources":["https://example.test/independent"],
                "itf_status":"verified_absent_for_cohort","cohort_size":2,"ranking_date":str(RANKING_DATE)}}}

    def test_known_points_100_percent_does_not_certify_inventory(self):
        report = assess_season(self.connection,2025,reviews={})
        self.assertEqual(report["recorded_points_percent"],100)
        self.assertFalse(report["complete"])
        self.assertIn("tournament_inventory_not_verified",report["blockers"])
        self.assertEqual(report["missing_source_files"],[])

    def test_closed_season_requires_verified_inventory_for_same_snapshot(self):
        reviews = self.review(2025)
        self.assertTrue(assess_season(self.connection,2025,reviews=reviews)["complete"])
        reviews["seasons"]["2025"]["import_id"] = "outdated"
        self.assertFalse(assess_season(self.connection,2025,reviews=reviews)["complete"])

    def test_review_for_different_cohort_or_partial_itf_is_not_complete(self):
        for field,value in (("cohort_size",50),("itf_status","partial"),("ranking_date","2025-12-29")):
            reviews = self.review(2025)
            reviews["seasons"]["2025"][field] = value
            self.assertFalse(inventory_status(latest_import(self.connection,2025),reviews)["verified"])

    def test_current_year_cannot_be_closed_before_year_end(self):
        self.load(2026)
        report = assess_season(self.connection,2026,reviews=self.review(2026))
        self.assertEqual(report["recorded_points_percent"],100)
        self.assertFalse(report["complete"])
        self.assertIn("season_or_events_not_closed",report["blockers"])

    def test_missing_years_remain_visible_in_range(self):
        report = assess_range(self.connection,2024,2026)
        self.assertEqual([item["season"] for item in report["seasons"]],[2026,2025,2024])
        self.assertEqual(report["seasons"][0]["blockers"],["not_imported"])
        self.assertFalse(report["all_complete"])

    def test_historical_priority_does_not_delete_or_certify_deferred_events(self):
        datasets=[resource("2025.csv",[row(tourney_id="2025-1",tourney_date="20250201",round="F")]),
                  resource("2025_challenger.csv",[row(tourney_id="2025-777",tourney_date="20250301",tourney_level="C",round="F")]),
                  resource("atp_quali/2025_atp_quali.csv",[])]
        import_bundle(self.connection,2025,AS_OF,RANKING_DATE,RANKINGS,datasets,datasets)
        report=assess_season(self.connection,2025,reviews={})
        self.assertEqual((report["recorded_participations"],report["needs_review"]),(4,2))
        self.assertEqual((report["priority"]["participations"],report["priority"]["needs_review"]),(2,0))
        self.assertTrue(report["priority"]["recorded_points_resolved"])
        self.assertFalse(report["priority"]["certifies_complete_season"])
        self.assertFalse(report["complete"])

    def test_2026_retains_full_scope_without_historical_priority(self):
        self.load(2026)
        self.assertIsNone(assess_season(self.connection,2026)["priority"])

    def test_empty_primary_scope_is_not_counted_as_resolved(self):
        datasets=[resource("2025.csv",[]),resource("2025_challenger.csv",[row(tourney_id="2025-777",tourney_date="20250301",tourney_level="C",round="F")]),resource("atp_quali/2025_atp_quali.csv",[])]
        import_bundle(self.connection,2025,AS_OF,RANKING_DATE,RANKINGS,datasets,datasets)
        priority=assess_season(self.connection,2025)["priority"]
        self.assertEqual(priority["participations"],0)
        self.assertFalse(priority["recorded_points_resolved"])


if __name__ == "__main__":
    unittest.main()
