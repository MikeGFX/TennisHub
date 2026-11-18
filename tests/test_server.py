import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tennishub.database import connect
from tennishub.importer import import_bundle
from tennishub.server import make_server
from tests.test_importer import AS_OF, RANKING_DATE, RANKINGS, resource, row


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / "tennishub.sqlite3"
        connection = connect(self.database)
        for year in (2025, 2026):
            dataset = resource(f"{year}.csv", [row(tourney_id=f"{year}-807", tourney_date=f"{year}0225", round="R16")])
            import_bundle(connection, year, AS_OF, RANKING_DATE, RANKINGS, [dataset], [dataset])
        connection.close()
        self.server = make_server(self.database, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def get(self, path, method="GET"):
        try:
            response = urlopen(Request(self.base + path, method=method), timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    def test_browser_entry_and_assets_are_served(self):
        for path in ("/", "/assets/app.js", "/assets/app.css", "/favicon.svg"):
            with self.subTest(path=path):
                code, headers, body = self.get(path)
                self.assertEqual(code, 200)
                self.assertTrue(body)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn('lang="it"', self.get("/")[2].decode())

    def test_bootstrap_lists_real_imported_years(self):
        code, _, body = self.get("/api/bootstrap")
        result = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual([item["year"] for item in result["seasons"]], [2026, 2025])
        self.assertEqual(result["default_season"], 2026)
        self.assertFalse(result["needs_import"])

    def test_player_search_and_season_flow(self):
        code, _, body = self.get("/api/players?year=2026&q=sinner")
        self.assertEqual(code, 200)
        player = json.loads(body)["players"][0]
        self.assertEqual(player["id"], "S0AG")
        code, _, body = self.get("/api/season?year=2026&player=" + player["id"])
        self.assertEqual(code, 200)
        season = json.loads(body)
        self.assertEqual(season["player_name"], "Jannik Sinner")
        self.assertEqual(season["events"][0]["earned_points"], 50)
        self.assertEqual(season["events"][0]["matches"][0]["raw"]["winner_name"], "Alexander Zverev")
        self.assertTrue(season["events"][0]["matches"][0]["sources"])

    def test_changing_year_does_not_apply_wrong_points_table(self):
        code, _, body = self.get("/api/season?year=2025&player=S0AG")
        self.assertEqual(code, 200)
        result = json.loads(body)
        self.assertEqual(result["season"], 2025)
        self.assertIsNone(result["events"][0]["earned_points"])
        self.assertEqual(result["events"][0]["points_status"], "needs_review")

    def test_invalid_input_returns_readable_json_errors(self):
        for path, expected in (("/api/players", 400), ("/api/season?year=oops&player=Z355", 400),
                               ("/api/season?year=2026", 400), ("/api/season?year=2026&player=DOESNOTEXIST", 404),
                               ("/api/players?year=2001", 404)):
            with self.subTest(path=path):
                code, headers, body = self.get(path)
                self.assertEqual(code, expected)
                self.assertIn("application/json", headers["Content-Type"])
                self.assertTrue(json.loads(body)["error"])

    def test_static_routes_cannot_expose_database_or_source_files(self):
        for path in ("/data/local/tennishub.sqlite3", "/assets/../database.py", "/assets/%2e%2e/database.py", "/.git/config"):
            self.assertEqual(self.get(path)[0], 404)

    def test_server_is_local_and_does_not_accept_mutations(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertEqual(self.get("/api/season?year=2026&player=Z355", "POST")[0], 501)
        self.assertEqual(json.loads(self.get("/api/bootstrap")[2])["default_season"], 2026)

    def test_empty_archive_has_setup_state(self):
        self.database.unlink()
        code, _, body = self.get("/api/bootstrap")
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(body)["needs_import"])
        self.assertEqual(self.get("/api/players?year=2026")[0], 503)

    def test_head_returns_headers_without_body(self):
        code, headers, body = self.get("/", "HEAD")
        self.assertEqual(code, 200)
        self.assertGreater(int(headers["Content-Length"]), 0)
        self.assertEqual(body, b"")


if __name__ == "__main__":
    unittest.main()
