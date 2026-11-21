"""Confronti e serie di punti sulle sole fotografie importate piu' recenti."""

import json
from collections import Counter

from .database import latest_import
from .importer import search_key
from .queries import resolve_player, season

SURFACES = ("Hard", "Clay", "Grass", "Carpet", "Unknown")
UNPLAYED = ("W/O", "DEF", "ABN", "BYE")


def archive_years(connection):
    return [row[0] for row in connection.execute("SELECT DISTINCT season FROM imports ORDER BY season")]


def player_search(connection, query=""):
    needle = search_key(query)
    rows = connection.execute(
        "SELECT id, name, ioc FROM players WHERE instr(search_key, ?) > 0 OR lower(id)=? ORDER BY name LIMIT 30",
        (needle, needle)).fetchall()
    return {"players": [dict(row) for row in rows]}


def head_to_head(connection, first, second, year=None, surface="all", stage="all"):
    if surface not in (*SURFACES, "all") or stage not in ("all", "main", "qualifying"):
        raise ValueError("Filtro H2H non valido.")
    left, right = resolve_player(connection, first), resolve_player(connection, second)
    if left["id"] == right["id"]:
        raise ValueError("Scegli due giocatori diversi.")
    years = archive_years(connection)
    if year is not None and year not in years:
        raise ValueError("Stagione non presente nell'archivio.")
    snapshots, matches = [], []
    for value in years:
        if year is not None and value != year:
            continue
        snapshot = latest_import(connection, value)
        snapshots.append({"year": value, "as_of": snapshot["as_of"], "import_id": snapshot["id"]})
        rows = connection.execute(
            "WITH pair AS (SELECT * FROM matches WHERE import_id=? AND winner_id=? AND loser_id=? "
            "UNION ALL SELECT * FROM matches WHERE import_id=? AND winner_id=? AND loser_id=?) "
            "SELECT m.*, e.name, e.category, e.surface FROM pair m CROSS JOIN events e "
            "WHERE e.import_id=m.import_id AND e.edition_id=m.edition_id AND e.stage=m.stage",
            (snapshot["id"], left["id"], right["id"], snapshot["id"], right["id"], left["id"])).fetchall()
        for row in rows:
            if stage != "all" and row["stage"] != stage:
                continue
            raw = json.loads(row["raw_json"])
            counted = bool(row["score"].strip()) and not any(code in row["score"].upper() for code in UNPLAYED)
            matches.append({"key": row["match_key"], "year": value, "date": row["match_date"],
                            "tournament": row["name"], "category": row["category"],
                            "surface": row["surface"] if row["surface"] in SURFACES else "Unknown",
                            "stage": row["stage"], "round": row["round"],
                            "winner_id": row["winner_id"], "winner_name": raw["winner_name"],
                            "loser_id": row["loser_id"], "score_winner_first": row["score"], "counted": counted})
    by_surface = []
    for value in SURFACES:
        subset = [match for match in matches if match["surface"] == value and match["counted"]]
        counts = Counter(match["winner_id"] for match in subset)
        by_surface.append({"surface": value, "matches": len(subset), "first_wins": counts[left["id"]],
                           "second_wins": counts[right["id"]]})
    selected = [match for match in matches if surface == "all" or match["surface"] == surface]
    counted = [match for match in selected if match["counted"]]
    counts = Counter(match["winner_id"] for match in counted)
    return {"first": {key: left[key] for key in ("id", "name", "ioc")},
            "second": {key: right[key] for key in ("id", "name", "ioc")},
            "coverage": snapshots, "available_years": years,
            "filters": {"year": year, "surface": surface, "stage": stage},
            "summary": {"matches": len(counted), "first_wins": counts[left["id"]],
                        "second_wins": counts[right["id"]], "excluded_results": len(selected) - len(counted)},
            "by_surface": by_surface,
            "matches": sorted(selected, key=lambda match: (match["date"], match["key"]), reverse=True)}


def points_history(connection, player):
    person = resolve_player(connection, player)
    series = []
    for year in archive_years(connection):
        report = season(connection, person["id"], year)
        cumulative, partial, events = 0, False, []
        ordered = sorted(report["events"], key=lambda event: (event["last_recorded_date"], event["id"]))
        for event in ordered:
            if event["earned_points"] is None:
                partial = True
            else:
                cumulative += event["earned_points"]
            events.append({"id": event["id"], "name": event["name"], "date": event["last_recorded_date"],
                           "earned_points": event["earned_points"], "cumulative_known_points": cumulative,
                           "partial": partial, "provisional": event["provisional"]})
        summary = report["summary"]
        series.append({"year": year, "as_of": report["as_of"], "ranking_date": report["ranking_date"],
                       "import_id": report["import_id"], "points_engine_version": report["points_engine_version"],
                       "known_subtotal": cumulative, "unknown_events": summary["events_with_unknown_points"],
                       "events": summary["events"], "calculated_events": summary["events"] - summary["events_with_unknown_points"],
                       "total": None if partial or not events else cumulative, "timeline": events})
    return {"player_id": person["id"], "player_name": person["name"], "points_kind": "earned_in_tournaments", "seasons": series}
