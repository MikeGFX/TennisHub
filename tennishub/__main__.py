"""Comandi locali: import, players, season, status, coverage, serve."""

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from urllib.error import URLError

from . import queries
from .database import connect, open_existing
from .importer import import_bundle
from .history import import_history
from .sources import SourceClient, load_bundle

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description="TennisHub: archivio personale ATP locale")
    parser.add_argument("--db", type=Path, default=ROOT / "data/local/tennishub.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import", help="Importa una stagione e una classifica dei primi 50")
    importer.add_argument("--season", type=int, default=2026)
    importer.add_argument("--as-of", type=date.fromisoformat, required=True, help="Ultima data da includere, YYYY-MM-DD")
    importer.add_argument("--ranking-date", type=date.fromisoformat)
    importer.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/importer")
    importer.add_argument("--offline", action="store_true")
    historical = commands.add_parser("import-history", help="Importa un intervallo di stagioni passate per H2H e risultati")
    historical.add_argument("--from-season", type=int, required=True)
    historical.add_argument("--to-season", type=int, required=True)
    historical.add_argument("--as-of", type=date.fromisoformat, required=True)
    historical.add_argument("--ranking-date", type=date.fromisoformat)
    historical.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/importer")
    historical.add_argument("--offline", action="store_true")
    listing = commands.add_parser("players", help="Elenca o cerca i primi 50 importati")
    listing.add_argument("--query", default="")
    listing.add_argument("--season", type=int)
    listing.add_argument("--json", action="store_true")
    detail = commands.add_parser("season", help="Mostra la stagione di un giocatore per nome o ID ATP")
    detail.add_argument("player")
    detail.add_argument("--season", type=int, default=2026)
    detail.add_argument("--json", action="store_true")
    state = commands.add_parser("status", help="Riepilogo di importazione, fonti e anomalie")
    state.add_argument("--season", type=int)
    audit = commands.add_parser("coverage", help="Copertura del calcolo punti sui primi 50")
    audit.add_argument("--season", type=int, default=2026)
    audit.add_argument("--json", action="store_true")
    review = commands.add_parser("completeness", help="Verifica separatamente punti e inventario delle stagioni")
    review.add_argument("--from-season", type=int, default=2016)
    review.add_argument("--to-season", type=int, default=2026)
    review.add_argument("--json", action="store_true")
    inventory = commands.add_parser("inventory", help="Censimento strutturale in sola lettura dei tabelloni")
    inventory.add_argument("--season", type=int, default=2026)
    inventory.add_argument("--json", action="store_true")
    web = commands.add_parser("serve", help="Apri l'interfaccia locale nel browser")
    web.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    connection = None
    try:
        if args.command == "serve":
            from .server import serve
            if not 1 <= args.port <= 65535:
                raise ValueError("La porta deve essere compresa tra 1 e 65535.")
            serve(args.db, args.port)
        elif args.command == "import-history":
            client = SourceClient(args.cache_dir, args.offline)
            connection = connect(args.db)
            result = import_history(connection, client, args.from_season, args.to_season, args.as_of,
                                    args.ranking_date, progress=lambda item: print(
                                        f"Stagione {item['season']}: {item['matches']} incontri, "
                                        + ("gia presente" if item["reused"] else "importata"), file=sys.stderr, flush=True))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "import":
            if not 1968 <= args.season <= args.as_of.year:
                raise ValueError("La stagione deve essere compresa tra 1968 e l'anno della data limite.")
            client = SourceClient(args.cache_dir, args.offline)
            ranking_date, rankings, datasets, resources = load_bundle(client, args.season, args.as_of, args.ranking_date)
            connection = connect(args.db)
            result = import_bundle(connection, args.season, args.as_of, ranking_date, rankings, datasets, resources)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            connection = open_existing(args.db)
            if args.command == "players":
                result = queries.players(connection, args.query, args.season)
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print("Classifica del", result["ranking_date"])
                    for player in result["players"]:
                        print(f"{player['rank']:>2}  {player['id']:<5} {player['name']:<30} {player['ranking_points']:>6}  {player['ioc']}")
            elif args.command == "season":
                result = queries.season(connection, args.player, args.season)
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print(f"{result['player_name']} — {result['season']} — dati al {result['as_of']}")
                    for event in result["events"]:
                        points = str(event["earned_points"]) if event["earned_points"] is not None else "Da verificare"
                        print(f"{event['name']:<35} {event['placement']:<35} {points:>14}")
                    print("Riepilogo:", json.dumps(result["summary"], ensure_ascii=False))
                    print("Punti ottenuti calcolati; il subtotale esclude i valori da verificare. Non e' il ranking ATP.")
            elif args.command == "inventory":
                from .inventory import census
                result = census(connection, args.season)
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print("Censimento strutturale: non certifica la completezza dei tornei.")
                    for item in result["draws"]:
                        print(f"{item['category']} {item['stage']}: {item['count']} tabelloni")
                    print("Tabelloni principali senza qualificazioni registrate:", len(result["main_draws_without_qualifying_records"]))
                    print("Qualificazioni con soli percorsi curati, non tabelloni completi:", len(result["qualifying_draws_with_curated_paths_only"]))
                    print("Conteggi da verificare sui tabelloni ufficiali:", len(result["closed_draw_count_anomalies"]))
            elif args.command == "completeness":
                from .quality import assess_range
                result = assess_range(connection, args.from_season, args.to_season)
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print("Punti calcolabili sulle partecipazioni registrate; non e' una certificazione di tutti i tornei.")
                    for item in result["seasons"]:
                        if "recorded_participations" in item:
                            print(f"{item['season']}: {item['calculated']}/{item['recorded_participations']} punti calcolabili; "
                                  f"{item['needs_review']} da verificare; stagione completa: {'si' if item['complete'] else 'no'}")
                        else:
                            print(f"{item['season']}: non importata")
            elif args.command == "coverage":
                result = queries.coverage(connection, args.season)
                if not args.json:
                    result = {key: value for key, value in result.items() if key != "unresolved"}
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(queries.status(connection, args.season), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, URLError, sqlite3.Error) as error:
        print("Errore:", str(error), file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
