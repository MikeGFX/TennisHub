"""Interfaccia locale in sola lettura, servita soltanto su loopback."""

import json
import sqlite3
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import queries, analytics
from .database import open_existing

ASSETS = Path(__file__).with_name("web")
STATIC_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
                "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
                "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/favicon.svg": ("favicon.svg", "image/svg+xml"),
                "/assets/analytics.js": ("analytics.js", "text/javascript; charset=utf-8"),
                "/assets/analytics.css": ("analytics.css", "text/css; charset=utf-8")}


def bootstrap(database):
    if not Path(database).is_file():
        return {"seasons": [], "default_season": None, "needs_import": True}
    connection = open_existing(database)
    try:
        years = [row[0] for row in connection.execute("SELECT DISTINCT season FROM imports ORDER BY season DESC")]
        snapshots = []
        for year in years:
            snapshot = connection.execute(
                "SELECT as_of, ranking_date FROM imports WHERE season=? ORDER BY as_of DESC, created_at DESC, rowid DESC LIMIT 1",
                (year,)).fetchone()
            snapshots.append({"year": year, "as_of": snapshot["as_of"], "ranking_date": snapshot["ranking_date"]})
        return {"seasons": snapshots, "default_season": years[0] if years else None, "needs_import": not bool(years)}
    finally:
        connection.close()


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, database, **kwargs):
        self.database = database
        super().__init__(*args, **kwargs)

    def _respond(self, status, body, content_type="application/json; charset=utf-8", head=False):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
        self.end_headers()
        if not head:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Il browser puo' annullare una richiesta quando cambia giocatore.

    def _get(self, head=False):
        url = urlsplit(self.path)
        if url.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[url.path]
            self._respond(HTTPStatus.OK, (ASSETS / filename).read_bytes(), content_type, head)
            return
        parameters = parse_qs(url.query, keep_blank_values=True)
        connection = None
        try:
            if url.path == "/api/bootstrap":
                result = bootstrap(self.database)
            elif url.path in {"/api/player-search", "/api/h2h", "/api/points-history"}:
                connection = open_existing(self.database)
                if url.path == "/api/player-search":
                    result = analytics.player_search(connection, parameters.get("q", [""])[0])
                elif url.path == "/api/points-history":
                    player = parameters.get("player", [""])[0].strip()
                    if not player:
                        self._respond(HTTPStatus.BAD_REQUEST, {"error": "Seleziona un giocatore."}, head=head)
                        return
                    result = analytics.points_history(connection, player)
                else:
                    first = parameters.get("first", [""])[0].strip()
                    second = parameters.get("second", [""])[0].strip()
                    year = parameters.get("year", ["all"])[0]
                    surface = parameters.get("surface", ["all"])[0]
                    stage = parameters.get("stage", ["all"])[0]
                    if not first or not second or first.casefold() == second.casefold() or (year != "all" and not year.isdigit()) or surface not in (*analytics.SURFACES, "all") or stage not in ("all", "main", "qualifying"):
                        self._respond(HTTPStatus.BAD_REQUEST, {"error": "Scegli due giocatori diversi e filtri validi."}, head=head)
                        return
                    result = analytics.head_to_head(connection, first, second, None if year == "all" else int(year), surface, stage)
            elif url.path in {"/api/players", "/api/season"}:
                try:
                    year = int(parameters.get("year", [""])[0])
                except ValueError:
                    self._respond(HTTPStatus.BAD_REQUEST, {"error": "Seleziona una stagione valida."}, head=head)
                    return
                connection = open_existing(self.database)
                if url.path == "/api/players":
                    result = queries.players(connection, parameters.get("q", [""])[0], year)
                else:
                    player = parameters.get("player", [""])[0].strip()
                    if not player:
                        self._respond(HTTPStatus.BAD_REQUEST, {"error": "Seleziona un giocatore."}, head=head)
                        return
                    result = queries.season(connection, player, year)
            else:
                self._respond(HTTPStatus.NOT_FOUND, {"error": "Pagina non trovata."}, head=head)
                return
            self._respond(HTTPStatus.OK, result, head=head)
        except ValueError as error:
            self._respond(HTTPStatus.NOT_FOUND, {"error": str(error)}, head=head)
        except sqlite3.Error:
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Archivio non disponibile. Controlla l'importazione dei dati e riprova."}, head=head)
        finally:
            if connection is not None:
                connection.close()

    def do_GET(self):
        self._get()

    def do_HEAD(self):
        self._get(head=True)

    def log_message(self, format, *args):
        pass


def make_server(database, port=8765):
    return ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, database=Path(database)))


def serve(database, port=8765):
    server = make_server(database, port)
    print(f"TennisHub: http://127.0.0.1:{server.server_port}", flush=True)
    print("Premi Ctrl+C per arrestare il server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
