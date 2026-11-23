"""Lettura locale per l'interfaccia futura; nessuna chiamata di rete."""

import json
from collections import defaultdict

from .points import ENGINE_VERSION, LABELS, ROUND_ORDER, PointsResult, evaluate_points, official_round

from .database import latest_import
from .results import match_was_played
from .quality import inventory_status
from .importer import search_key


def players(connection, query="", season=None):
    snapshot = latest_import(connection, season)
    rows = connection.execute(
        "SELECT p.id, p.name, p.ioc, r.rank, r.points AS ranking_points, p.search_key "
        "FROM rankings r JOIN players p ON p.id=r.player_id WHERE r.import_id=? ORDER BY r.rank",
        (snapshot["id"],)).fetchall()
    needle = search_key(query)
    return {"ranking_date": snapshot["ranking_date"], "season": snapshot["season"],
            "players": [{k: row[k] for k in row.keys() if k != "search_key"} for row in rows
                        if not needle or needle in row["search_key"] or needle == row["id"].casefold()]}


def resolve_player(connection, value):
    exact = connection.execute("SELECT * FROM players WHERE id=?", (value.upper(),)).fetchone()
    if exact:
        return exact
    needle = search_key(value)
    found = connection.execute("SELECT * FROM players WHERE instr(search_key, ?) > 0 ORDER BY name", (needle,)).fetchall()
    if len(found) != 1:
        choices = ", ".join(f"{row['name']} ({row['id']})" for row in found[:10])
        raise ValueError("Giocatore non trovato." if not found else "Nome ambiguo; usare l'ID ATP: " + choices)
    return found[0]


def season(connection, player, year):
    snapshot = latest_import(connection, year)
    person = resolve_player(connection, player)
    player_id = person["id"]
    player_matches = (
        "WITH player_matches AS (SELECT * FROM matches WHERE import_id=? AND winner_id=? "
        "UNION ALL SELECT * FROM matches WHERE import_id=? AND loser_id=?) "
    )
    parameters = (snapshot["id"], player_id, snapshot["id"], player_id)
    records = connection.execute(
        player_matches + "SELECT m.*, e.name, e.category, e.surface, e.final_recorded, e.draw_size AS event_draw_size "
        "FROM player_matches m CROSS JOIN events e WHERE e.import_id=m.import_id AND e.edition_id=m.edition_id AND e.stage=m.stage "
        "ORDER BY m.match_date, m.match_key", parameters).fetchall()
    provenances = defaultdict(list)
    for source in connection.execute(
            player_matches + "SELECT s.match_key, s.source_name, s.source_line FROM player_matches m "
            "CROSS JOIN match_sources s WHERE s.import_id=m.import_id AND s.match_key=m.match_key "
            "ORDER BY s.source_name, s.source_line", parameters):
        provenances[source["match_key"]].append({"source_name": source["source_name"], "source_line": source["source_line"]})
    groups = defaultdict(list)
    for record in records:
        groups[record["edition_id"]].append(record)
    events = []
    def shown_round(row):
        return official_round(row["edition_id"], row["winner_id"], row["loser_id"], row["round"])

    for edition_id, rows in groups.items():
        rows.sort(key=lambda row: (row["stage"] == "main", ROUND_ORDER.get(shown_round(row), -1), row["match_date"], row["match_key"]))
        main = [row for row in rows if row["stage"] == "main"]
        primary = main or rows
        last = max(primary, key=lambda row: (ROUND_ORDER.get(row["round"], {"Q1": -3, "Q2": -2, "Q3": -1}.get(row["round"], -99)), row["match_date"]))
        team_editions = {f"{year}-9900", f"{year}-9210"}
        if year <= 2012:
            team_editions.add(f"{year}-615")
        if 2020 <= year <= 2022:
            team_editions.add(f"{year}-8888")
        is_team = last["category"] == "D" or edition_id in team_editions
        played = [row for row in rows if match_was_played(row["score"])]
        wins = sum(row["winner_id"] == player_id for row in played)
        losses = len(played) - wins
        final_win = last["round"] == "F" and last["winner_id"] == player_id and not is_team
        known_end = bool(last["final_recorded"]) or last["loser_id"] == player_id and last["round"] in LABELS
        if not main:
            known_end = last["loser_id"] == player_id and last["round"] in {"Q1", "Q2", "Q3"}
        missing_elimination = main and known_end and not is_team and not final_win and last["round"] != "RR" and last["winner_id"] == player_id
        if not main:
            placement = "Qualificazioni: " + (last["round"] or "turno sconosciuto")
        elif is_team:
            placement = f"Singolare a squadre: {wins}V/{losses}S"
        elif final_win:
            placement = "Vincitore"
        elif not last["round"] or missing_elimination:
            placement = "Da verificare"
        elif known_end:
            placement = "Gironi" if last["round"] == "RR" else LABELS.get(last["round"], last["round"])
        else:
            placement = "In corso: " + last["round"]
        inputs = [{"raw": json.loads(row["raw_json"]), "stage": row["stage"]} for row in rows]
        result = (evaluate_points(inputs, player_id=player_id, season=year) if last["event_draw_size"] else
                  PointsResult(reason="Formato del tabellone discordante nella fonte: punti da verificare.", sources=[]))
        points, reason = result.value, result.reason
        events.append({
            "id": edition_id, "name": last["name"], "category": last["category"], "surface": last["surface"],
            "competition_type": "team" if is_team else "individual",
            "first_recorded_date": min(row["match_date"] for row in rows),
            "last_recorded_date": max(row["match_date"] for row in rows),
            "placement": placement, "provisional": not known_end and not is_team,
            "earned_points": points, "points_status": "calculated" if points is not None else "needs_review",
            "points_reason": reason, "wins": wins, "losses": losses,
            "points_breakdown": {"main_draw": result.main_draw, "qualifying": result.qualifying},
            "points_sources": result.sources,
            "matches": [{"date": row["match_date"], "stage": row["stage"], "round": shown_round(row),
                         **({"source_round": row["round"]} if shown_round(row) != row["round"] else {}),
                         "winner_id": row["winner_id"], "loser_id": row["loser_id"],
                         "score_winner_first": row["score"], "played": match_was_played(row["score"]), "raw": json.loads(row["raw_json"]),
                         "sources": provenances[row["match_key"]]} for row in rows],
        })
    events.sort(key=lambda event: (event["first_recorded_date"], event["id"]))
    return {"player_id": player_id, "player_name": person["name"], "season": year,
            "as_of": snapshot["as_of"], "ranking_date": snapshot["ranking_date"], "import_id": snapshot["id"],
            "points_engine_version": ENGINE_VERSION, "inventory": inventory_status(snapshot),
            "summary": {"events": len(events), "matches_recorded": len(records),
                        "wins": sum(event["wins"] for event in events), "losses": sum(event["losses"] for event in events),
                        "titles": sum(event["placement"] == "Vincitore" for event in events),
                        "known_earned_points_subtotal": sum(event["earned_points"] or 0 for event in events),
                        "events_with_unknown_points": sum(event["earned_points"] is None for event in events)},
            "events": events}


def status(connection, year=None):
    snapshot = latest_import(connection, year)
    return {**json.loads(snapshot["summary_json"]),
            "sources": [dict(row) for row in connection.execute("SELECT name, url, sha256, retrieved_at, modified_at FROM sources WHERE import_id=? ORDER BY name", (snapshot["id"],))],
            "issue_examples": [dict(row) for row in connection.execute("SELECT source_name, source_line, code, message FROM issues WHERE import_id=? LIMIT 20", (snapshot["id"],))]}


def coverage(connection, year, categories=None):
    roster = players(connection, season=year)
    unresolved, reasons = [], defaultdict(int)
    total = provisional = 0
    for player in roster["players"]:
        report = season(connection, player["id"], year)
        events = [event for event in report["events"] if categories is None or event["category"] in categories]
        total += len(events)
        provisional += sum(event["provisional"] for event in events)
        for event in events:
            if event["earned_points"] is None:
                reasons[event["points_reason"]] += 1
                unresolved.append({"player_id": player["id"], "player_name": player["name"],
                                   "event_id": event["id"], "event_name": event["name"],
                                   "category": event["category"], "reason": event["points_reason"]})
    return {"season": year, "ranking_date": roster["ranking_date"], "points_engine_version": ENGINE_VERSION,
            "players": len(roster["players"]), "participations": total, "provisional_events": provisional,
            "calculated": total - len(unresolved), "needs_review": len(unresolved),
            "reasons": dict(sorted(reasons.items())), "unresolved": unresolved}
