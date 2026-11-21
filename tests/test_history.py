import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from tennishub.database import connect
from tennishub.history import import_history
from tennishub.sources import BASE, Resource
from tests.test_importer import AS_OF, RANKING_DATE, RANKINGS, row, resource


class FakeClient:
    def __init__(self, missing=None, conflict=False):
        self.calls = Counter()
        self.objects = {}
        files = []
        rankings = RANKINGS + [{"id": f"X{i:03}", "name": f"Player {i}", "rank": i, "points": 1, "ioc": "ITA"} for i in range(3, 51)]
        self.objects[BASE + "/api/ranking/dates"] = json.dumps({"dates": [str(RANKING_DATE)]}).encode()
        self.objects[BASE + "/api/ranking?date=" + str(RANKING_DATE)] = json.dumps({"rankings": rankings}).encode()
        for year in (2023, 2024):
            for name in (f"{year}.csv", f"{year}_challenger.csv", f"atp_quali/{year}_atp_quali.csv"):
                url = BASE + "/data/" + name
                if name == missing:
                    continue
                files.append({"name": name, "url": url})
                data = [row(tourney_id=f"{year}-1", tourney_date=f"{year}0201")]
                if "challenger" in name:
                    data = [row(tourney_id=f"{year}-2", tourney_date=f"{year}0301", tourney_level="C", round="F")]
                elif "atp_quali" in name:
                    data[0]["round"] = "Q1"
                if conflict and name == "2024.csv":
                    data.append({**data[0], "score": "6-0 6-0"})
                self.objects[url] = resource(name, data).body
        self.objects[BASE + "/api/data-files"] = json.dumps({"files": files}).encode()

    def get(self, name, url, modified_at=None):
        self.calls[url] += 1
        return Resource(name, url, self.objects[url], "2026-11-21T00:00:00+00:00")


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.connection = connect(Path(self.temp.name) / "tennis.sqlite3")
        self.addCleanup(self.connection.close)

    def test_interval_shares_metadata_and_is_idempotent(self):
        client = FakeClient()
        completed = []
        result = import_history(self.connection, client, 2023, 2024, AS_OF, RANKING_DATE, progress=lambda item: completed.append(item["season"]))
        self.assertEqual(completed, [2023, 2024])
        self.assertEqual(result["imported"], 2)
        for suffix in ("/api/data-files", "/api/ranking/dates", "/api/ranking?date=" + str(RANKING_DATE)):
            self.assertEqual(client.calls[BASE + suffix], 1)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM matches").fetchone()[0], 6)
        repeated = import_history(self.connection, FakeClient(), 2023, 2024, AS_OF, RANKING_DATE)
        self.assertEqual((repeated["imported"], repeated["reused"]), (0, 2))
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 2)

    def test_missing_file_is_rejected_before_any_season_is_written(self):
        client = FakeClient(missing="atp_quali/2024_atp_quali.csv")
        with self.assertRaisesRegex(ValueError, "Storico non avviato"):
            import_history(self.connection, client, 2023, 2024, AS_OF, RANKING_DATE)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 0)
        self.assertEqual(sum(client.calls.values()), 1)

    def test_failed_year_preserves_completed_year_and_can_resume(self):
        with self.assertRaisesRegex(ValueError, "stagione 2024"):
            import_history(self.connection, FakeClient(conflict=True), 2023, 2024, AS_OF, RANKING_DATE)
        self.assertEqual([row[0] for row in self.connection.execute("SELECT season FROM imports")], [2023])
        resumed = import_history(self.connection, FakeClient(), 2023, 2024, AS_OF, RANKING_DATE)
        self.assertEqual((resumed["imported"], resumed["reused"]), (1, 1))
        self.assertEqual(self.connection.execute("SELECT count(*) FROM matches").fetchone()[0], 6)

    def test_invalid_ranges_do_not_fetch_or_write(self):
        for first, last in ((2024, 2023), (1967, 2020), (2024, 2026)):
            client = FakeClient()
            with self.assertRaises(ValueError):
                import_history(self.connection, client, first, last, AS_OF)
            self.assertEqual(sum(client.calls.values()), 0)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM imports").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
