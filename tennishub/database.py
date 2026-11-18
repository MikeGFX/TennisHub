"""Schema locale: ogni importazione e' una fotografia immutabile e datata."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS imports (
    id TEXT PRIMARY KEY, season INTEGER NOT NULL, as_of TEXT NOT NULL,
    ranking_date TEXT NOT NULL, created_at TEXT NOT NULL, summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    import_id TEXT NOT NULL REFERENCES imports(id), name TEXT NOT NULL,
    url TEXT NOT NULL, sha256 TEXT NOT NULL, retrieved_at TEXT NOT NULL, modified_at TEXT,
    PRIMARY KEY (import_id, name)
);
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, ioc TEXT, search_key TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rankings (
    import_id TEXT NOT NULL REFERENCES imports(id), rank INTEGER NOT NULL CHECK(rank > 0),
    player_id TEXT NOT NULL REFERENCES players(id), points INTEGER NOT NULL CHECK(points >= 0),
    PRIMARY KEY (import_id, rank), UNIQUE (import_id, player_id)
);
CREATE TABLE IF NOT EXISTS events (
    import_id TEXT NOT NULL REFERENCES imports(id), edition_id TEXT NOT NULL,
    stage TEXT NOT NULL CHECK(stage IN ('main', 'qualifying')), name TEXT NOT NULL,
    category TEXT NOT NULL, surface TEXT NOT NULL, draw_size TEXT NOT NULL,
    first_recorded_date TEXT NOT NULL, last_recorded_date TEXT NOT NULL,
    final_recorded INTEGER NOT NULL CHECK(final_recorded IN (0, 1)),
    PRIMARY KEY (import_id, edition_id, stage)
);
CREATE TABLE IF NOT EXISTS matches (
    import_id TEXT NOT NULL, match_key TEXT NOT NULL,
    edition_id TEXT NOT NULL, stage TEXT NOT NULL, match_date TEXT NOT NULL,
    round TEXT NOT NULL, winner_id TEXT NOT NULL REFERENCES players(id),
    loser_id TEXT NOT NULL REFERENCES players(id), score TEXT NOT NULL, raw_json TEXT NOT NULL,
    PRIMARY KEY (import_id, match_key), CHECK(winner_id != loser_id),
    FOREIGN KEY (import_id, edition_id, stage) REFERENCES events(import_id, edition_id, stage)
);
CREATE INDEX IF NOT EXISTS matches_winner ON matches(import_id, winner_id);
CREATE INDEX IF NOT EXISTS matches_loser ON matches(import_id, loser_id);
CREATE TABLE IF NOT EXISTS match_sources (
    import_id TEXT NOT NULL, match_key TEXT NOT NULL, source_name TEXT NOT NULL,
    source_line INTEGER NOT NULL,
    PRIMARY KEY (import_id, match_key, source_name, source_line),
    FOREIGN KEY (import_id, match_key) REFERENCES matches(import_id, match_key),
    FOREIGN KEY (import_id, source_name) REFERENCES sources(import_id, name)
);
CREATE TABLE IF NOT EXISTS issues (
    import_id TEXT NOT NULL REFERENCES imports(id), source_name TEXT NOT NULL,
    source_line INTEGER NOT NULL, code TEXT NOT NULL, message TEXT NOT NULL
);
"""


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, 1):
        connection.close()
        raise ValueError("Versione del database non supportata.")
    if version == 0:
        connection.executescript(SCHEMA)
        connection.execute("PRAGMA user_version = 1")
    return connection


def open_existing(path):
    path = Path(path).resolve()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def latest_import(connection, season=None):
    if season is None:
        row = connection.execute("SELECT * FROM imports ORDER BY as_of DESC, created_at DESC, rowid DESC LIMIT 1").fetchone()
    else:
        row = connection.execute("SELECT * FROM imports WHERE season=? ORDER BY as_of DESC, created_at DESC, rowid DESC LIMIT 1", (season,)).fetchone()
    if row is None:
        raise ValueError("Nessuna importazione disponibile per la stagione richiesta.")
    return row
