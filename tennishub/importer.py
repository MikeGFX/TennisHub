"""Importazioni atomiche e idempotenti; nessuna sostituzione silenziosa di conflitti."""

import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime

from .sources import csv_rows, digest, utc_now


def search_key(name):
    return " ".join("".join(char for char in unicodedata.normalize("NFKD", name.casefold())
                            if not unicodedata.combining(char)).split())


def prepare(datasets, season, as_of):
    matches, players, events, issues = {}, {}, {}, []
    duplicates = excluded = 0
    draw_conflicts = set()
    # Alcuni file storici riutilizzano un ID Davis per sfide fra nazioni diverse.
    # Separiamo solo questi casi; il tourney_id originale rimane nel JSON della fonte.
    davis_names = defaultdict(set)
    for resource in datasets:
        for _, row in csv_rows(resource):
            if row["tourney_level"].strip() != "D" or not row["tourney_id"].strip().startswith(str(season) + "-"):
                continue
            try:
                day = datetime.strptime(row["tourney_date"].strip(), "%Y%m%d").date()
            except ValueError:
                continue
            if day <= as_of:
                davis_names[row["tourney_id"].strip()].add(row["tourney_name"].strip())
    separable_ties = set()
    for event_id, names in davis_names.items():
        pairs = [re.search(r":\s*([A-Z]{3}) vs ([A-Z]{3})$", name) for name in names]
        if len(names) > 1 and all(pairs) and len({frozenset(pair.groups()) for pair in pairs}) == len(names):
            separable_ties.add(event_id)
    for resource in datasets:
        stage = "qualifying" if resource.name.startswith("atp_quali/") else "main"
        for line, original in csv_rows(resource):
            row = {key: (value or "").strip() for key, value in original.items() if key is not None}
            if not row["tourney_id"].startswith(str(season) + "-"):
                excluded += 1
                continue
            try:
                day = datetime.strptime(row["tourney_date"], "%Y%m%d").date()
            except ValueError:
                issues.append((resource.name, line, "invalid_date", "Data incontro non valida; riga esclusa."))
                continue
            if day > as_of:
                excluded += 1
                continue
            for side in ("winner", "loser"):
                row[side + "_id"] = row[side + "_id"].upper()
            if (not row["winner_id"] or not row["loser_id"] or
                    row["winner_id"] == row["loser_id"] or
                    not row["winner_name"] or not row["loser_name"]):
                issues.append((resource.name, line, "incomplete_identity", "Giocatore mancante o identita' non valida; riga esclusa."))
                continue
            if not row["round"]:
                issues.append((resource.name, line, "missing_round", "Turno assente: incontro conservato, piazzamento da verificare."))
            edition_id = row["tourney_id"]
            if row["tourney_level"] == "D" and edition_id in separable_ties:
                edition_id += "-tie-" + digest(row["tourney_name"].encode("utf-8"))[:12]
            identity = [edition_id, stage, row["round"], row["winner_id"], row["loser_id"]]
            key = digest(json.dumps(identity).encode())
            if key in matches:
                previous = matches[key]["raw"]
                presentation = {"winner_name", "loser_name", "match_num"}
                differences = {field for field in (previous.keys() | row.keys()) - presentation
                               if previous.get(field, "") != row.get(field, "")}
                enrichable = {field for field in differences if field == "minutes" or field.startswith(("w_", "l_"))}
                if differences - enrichable or any(previous.get(field) and row.get(field) for field in differences):
                    raise ValueError(f"Dati discordanti per lo stesso incontro: {resource.name}:{line}. Importazione annullata.")
                if differences:
                    for field in differences:
                        if not previous.get(field):
                            previous[field] = row[field]
                    issues.append((resource.name, line, "duplicate_enrichment", "Statistiche mancanti completate da un duplicato concordante; entrambe le provenienze conservate."))
                if any(previous.get(field) != row.get(field) for field in presentation):
                    issues.append((resource.name, line, "duplicate_variant", "Stesso incontro e stessi ID con nome o numero riga diversi; provenienze conservate."))
                matches[key]["sources"].append((resource.name, line))
                duplicates += 1
                continue
            matches[key] = {"raw": row, "edition_id": edition_id, "stage": stage, "day": str(day), "sources": [(resource.name, line)]}
            for side in ("winner", "loser"):
                player_id = row[side + "_id"]
                candidate = {"id": player_id, "name": row[side + "_name"],
                             "ioc": row.get(side + "_ioc", ""), "day": str(day)}
                if player_id not in players or candidate["day"] >= players[player_id]["day"]:
                    players[player_id] = candidate
            event_key = (edition_id, stage)
            metadata = (row["tourney_name"], row["tourney_level"], row["surface"], row["draw_size"])
            if event_key not in events:
                if edition_id != row["tourney_id"]:
                    issues.append((resource.name, line, "team_tie_identity", "ID Davis condiviso da sfide diverse: identita locale separata, ID originale conservato."))
                events[event_key] = {"metadata": metadata, "first": str(day), "last": str(day), "final": False}
            event = events[event_key]
            if event["metadata"] != metadata:
                previous_metadata = event["metadata"]
                same_event = all(previous_metadata[index] == metadata[index] for index in (0, 1, 3))
                if previous_metadata[0].casefold() == metadata[0].casefold() and previous_metadata[1:] == metadata[1:]:
                    issues.append((resource.name, line, "event_label_variant", "Nome della stessa edizione con sole maiuscole diverse; etichetta originale conservata nei dati della fonte."))
                elif same_event and (not previous_metadata[2] or not metadata[2]):
                    if metadata[2]:
                        event["metadata"] = metadata
                    issues.append((resource.name, line, "event_surface_completed", "Superficie assente in alcune righe: usato il valore noto della stessa edizione; dati originali conservati."))
                elif previous_metadata[:3] == metadata[:3] and previous_metadata[3] != metadata[3]:
                    event["metadata"] = (*metadata[:3], "")
                    if event_key not in draw_conflicts:
                        issues.append((resource.name, line, "draw_size_conflict", "Dimensione tabellone discordante: conservati risultati e valori originali, formato locale sconosciuto e punti da verificare."))
                        draw_conflicts.add(event_key)
                else:
                    raise ValueError(f"Metadati del torneo discordanti: {resource.name}:{line}.")
            event["first"] = min(event["first"], str(day))
            event["last"] = max(event["last"], str(day))
            event["final"] |= row["round"] == "F" and bool(row["score"])
    return matches, players, events, issues, duplicates, excluded


def import_bundle(connection, season, as_of, ranking_date, rankings, datasets, resources):
    signature = {"version": 1, "season": season, "as_of": str(as_of),
                 "ranking_date": str(ranking_date),
                 "sources": sorted((resource.name, resource.url, resource.sha256) for resource in resources)}
    import_id = digest(json.dumps(signature, sort_keys=True).encode())
    previous = connection.execute("SELECT summary_json FROM imports WHERE id=?", (import_id,)).fetchone()
    if previous:
        return {**json.loads(previous["summary_json"]), "reused": True}
    matches, players, events, issues, duplicates, excluded = prepare(datasets, season, as_of)
    if not matches:
        raise ValueError("Nessun incontro valido per la stagione richiesta.")
    # La classifica e' l'autorita' per il nome e il paese dei giocatori selezionati.
    for row in rankings:
        players[row["id"]] = row
        if not any(row["id"] in (match["raw"]["winner_id"], match["raw"]["loser_id"]) for match in matches.values()):
            issues.append(("rankings", row["rank"], "no_season_matches", f"Nessun incontro rilevato per {row['id']} nella stagione."))
    codes = defaultdict(int)
    for _, _, code, _ in issues:
        codes[code] += 1
    summary = {"import_id": import_id, "season": season, "as_of": str(as_of),
               "ranking_date": str(ranking_date), "selected_players": len(rankings),
               "players_in_archive": len(players), "event_draws": len(events),
               "matches": len(matches), "duplicates_removed": duplicates,
               "excluded_by_date_or_season": excluded, "issues": dict(codes), "reused": False}
    with connection:
        connection.execute("INSERT INTO imports VALUES (?, ?, ?, ?, ?, ?)",
                           (import_id, season, str(as_of), str(ranking_date), utc_now(), json.dumps(summary)))
        for resource in resources:
            connection.execute("INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)",
                               (import_id, resource.name, resource.url, resource.sha256, resource.retrieved_at, resource.modified_at))
        for player in players.values():
            connection.execute("INSERT INTO players VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, ioc=excluded.ioc, search_key=excluded.search_key",
                               (player["id"], player["name"], player.get("ioc", ""), search_key(player["name"])))
        connection.executemany("INSERT INTO rankings VALUES (?, ?, ?, ?)",
                               [(import_id, row["rank"], row["id"], row["points"]) for row in rankings])
        for (edition_id, stage), event in events.items():
            connection.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (import_id, edition_id, stage, *event["metadata"], event["first"], event["last"], int(event["final"])))
        for key, match in matches.items():
            row = match["raw"]
            connection.execute("INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (import_id, key, match["edition_id"], match["stage"], match["day"], row["round"],
                                row["winner_id"], row["loser_id"], row["score"], json.dumps(row, ensure_ascii=False)))
            connection.executemany("INSERT INTO match_sources VALUES (?, ?, ?, ?)",
                                   [(import_id, key, name, line) for name, line in match["sources"]])
        connection.executemany("INSERT INTO issues VALUES (?, ?, ?, ?, ?)",
                               [(import_id, *issue) for issue in issues])
    return summary
