"""Verifica ripetibile delle fonti: singolare di Alexander Zverev nel 2026.

Solo libreria standard Python. Non e' un motore universale di ranking:
qualificazioni, Challenger e casi non verificati producono punti null.
I CSV e gli output con i singoli incontri rimangono locali e ignorati da Git.
"""

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tennishub.points import LABELS, ROUND_ORDER, calculate_points
PLAYER_ID = "Z355"
YEAR = 2026
BASE = "https://stats.tennismylife.org"
FILES = (
    "2026.csv",
    "ongoing_tourneys.csv",
    "2026_challenger.csv",
    "challenger_ongoing_tourneys.csv",
    "atp_quali/2026_atp_quali.csv",
)
RULES_URL = "https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook_31mar26.pdf"
UNITED_URL = "https://www.atptour.com/-/media/0030c0c028734686b55efd45fe463926.pdf"
FINALS_URL = "https://www.nittoatpfinals.com/en/event/points-and-prize-money"
FROZEN_RANK_URL = "https://www.atptour.com/es/players/dewiki/gj37/rankings-history"


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "TennisHub-personal-research/0.1"}), timeout=30) as response:
        return response.read()


def load_sources(cache, offline):
    cache.mkdir(parents=True, exist_ok=True)
    manifest_path = cache / "manifest.json"
    if offline:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        catalog = json.loads(fetch(BASE + "/api/data-files"))
        available = {entry["name"]: entry for entry in catalog["files"]}
        manifest = {}
        for filename in FILES:
            entry = available[filename]
            # URL documentati dal catalogo pubblico, senza host esterni.
            if not entry["url"].startswith(BASE + "/data/"):
                raise ValueError("URL inatteso nel catalogo: " + entry["url"])
            content = fetch(entry["url"])
            (cache / filename.replace("/", "_")).write_bytes(content)
            manifest[filename] = {
                "url": entry["url"], "source_modified_at": entry.get("mtime"),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    datasets = {}
    for filename in FILES:
        content = (cache / filename.replace("/", "_")).read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest[filename]["sha256"]:
            raise ValueError("Cache modificata: " + filename)
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        required = {"tourney_id", "tourney_date", "winner_id", "loser_id", "round", "score", "match_num"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Schema CSV inatteso: " + filename)
        datasets[filename] = list(reader)
    return datasets, manifest


def select_matches(datasets, as_of):
    selected = {}
    duplicate_count = 0
    counts = {}
    event_finished = set()
    for filename, rows in datasets.items():
        counts[filename] = {"rows": len(rows), "player_rows": 0}
        for row in rows:
            if not row["tourney_id"].startswith(str(YEAR) + "-"):
                continue
            if datetime.strptime(row["tourney_date"], "%Y%m%d").date() > as_of:
                continue
            if row["round"] == "F" and row["score"].strip():
                event_finished.add(row["tourney_id"])
            if PLAYER_ID not in (row["winner_id"], row["loser_id"]):
                continue
            counts[filename]["player_rows"] += 1
            stage = "qualifying" if "quali/" in filename else "main"
            key = (row["tourney_id"], stage, row["round"], row["winner_id"], row["loser_id"])
            if key in selected:
                previous = selected[key]
                # Un conflitto non viene risolto scegliendo silenziosamente una fonte.
                if previous["raw"] != row:
                    raise ValueError("Incontri duplicati con dati discordanti: " + str(key))
                previous["sources"].append(filename)
                duplicate_count += 1
            else:
                selected[key] = {"raw": row, "stage": stage, "sources": [filename]}
    return list(selected.values()), event_finished, counts, duplicate_count


def build_report(matches, finished, as_of, manifest, counts, duplicate_count):
    groups = defaultdict(list)
    identities = defaultdict(set)
    for match in matches:
        groups[match["raw"]["tourney_id"]].append(match)
        for side in ("winner", "loser"):
            identities[match["raw"][side + "_name"]].add(match["raw"][side + "_id"])
    events = []
    for tid, event_matches in groups.items():
        event_matches.sort(key=lambda m: (m["raw"]["tourney_date"], ROUND_ORDER.get(m["raw"]["round"], -1), int(m["raw"]["match_num"])))
        rows = [m["raw"] for m in event_matches]
        last = max(rows, key=lambda row: ROUND_ORDER.get(row["round"], -1))
        wins = sum(row["winner_id"] == PLAYER_ID for row in rows)
        losses = len(rows) - wins
        points, reason = calculate_points(event_matches)
        team = rows[0]["tourney_level"] == "D" or tid in {"2026-9900", "2026-9210"}
        if team:
            placement = f"Singolare a squadre: {wins}V/{losses}S"
            status = "partecipazione rilevata; piazzamento squadra non ricostruito"
        elif tid in finished or losses and last["round"] != "RR":
            placement = "Vincitore" if last["round"] == "F" and last["winner_id"] == PLAYER_ID else LABELS.get(last["round"], last["round"])
            status = "percorso individuale concluso nella fonte"
        else:
            placement = f"In corso: {last['round']} ({wins}V/{losses}S)"
            status = "provvisorio"
        events.append({
            "id": tid, "name": rows[0]["tourney_name"], "category": rows[0]["tourney_level"],
            "surface": rows[0]["surface"], "first_recorded_date": rows[0]["tourney_date"],
            "last_recorded_date": rows[-1]["tourney_date"], "placement": placement,
            "status": status, "wins": wins, "losses": losses,
            "earned_points_calculated": points, "points_reason": reason, "matches": event_matches,
        })
    events.sort(key=lambda e: (e["first_recorded_date"], e["id"]))
    return {
        "player": "Alexander Zverev", "player_id": PLAYER_ID, "year": YEAR, "as_of": str(as_of),
        "snapshot_notice": "Fotografia dei file scaricati; il filtro data non ricrea versioni storiche dei dati.",
        "summary": {"events": len(events), "matches": len(matches),
                    "wins": sum(e["wins"] for e in events), "losses": sum(e["losses"] for e in events),
                    "titles": sum(e["placement"] == "Vincitore" for e in events),
                    "known_earned_points": sum(e["earned_points_calculated"] or 0 for e in events),
                    "events_with_unknown_points": sum(e["earned_points_calculated"] is None for e in events),
                    "duplicates_removed": duplicate_count},
        "source_files": manifest, "source_counts": counts,
        "identity_warnings": {name: sorted(ids) for name, ids in identities.items() if len(ids) > 1},
        "rules": {"ATP_2026": RULES_URL, "United_Cup_2026": UNITED_URL,
                  "United_Cup_opponent_frozen_rank": FROZEN_RANK_URL, "Finals": FINALS_URL},
        "events": events,
    }


def markdown(report):
    summary = report["summary"]
    lines = ["# Alexander Zverev — stagione 2026", "", f"Verifica al {report['as_of']}; ultimi risultati presenti nei file, stagione ancora in corso.", "",
             f"{summary['events']} partecipazioni · {summary['matches']} incontri · {summary['wins']} vittorie / {summary['losses']} sconfitte · {summary['titles']} titoli individuali.", "",
             f"Punti ottenuti calcolati: **{summary['known_earned_points']}**; eventi con punti non calcolabili: **{summary['events_with_unknown_points']}**.", "",
             "Il totale e' la somma dei punti ottenuti nei tornei rilevati, compresi quelli ancora in corso. Non e' il ranking ATP, ne' un conteggio certificato dall'ATP. Un risultato non rilevato dalla fonte non compare nel report.", "",
             "Le date sono quelle registrate per gli incontri del giocatore: non rappresentano le date di inizio/fine del torneo e il fuso della fonte non e' dichiarato. Punteggi riportati dal punto di vista del vincitore.", "",
             "| Prima data registrata | Torneo | Categoria | Piazzamento / stato | Punti calcolati | V–S |",
             "|---|---|---|---|---:|---:|"]
    for event in report["events"]:
        points = event["earned_points_calculated"]
        lines.append(f"| {event['first_recorded_date']} | {event['name']} | {event['category']} | {event['placement']} | {points if points is not None else 'Da verificare'} | {event['wins']}–{event['losses']} |")
    lines += ["", "## Incontri e motivazione dei punti", ""]
    for event in report["events"]:
        lines += [f"### {event['name']}", "", event["points_reason"], "", "| Data fonte | Turno | Avversario | Esito Zverev | Punteggio (vincitore prima) |", "|---|---|---|---|---|"]
        for match in event["matches"]:
            row = match["raw"]
            won = row["winner_id"] == PLAYER_ID
            opponent = row["loser_name"] if won else row["winner_name"]
            lines.append(f"| {row['tourney_date']} | {row['round']} | {opponent} | {'Vittoria' if won else 'Sconfitta'} | {row['score']} |")
        lines.append("")
    lines += ["## Qualita' dei dati", ""]
    if report["identity_warnings"]:
        lines += ["Lo stesso nome compare con identificativi diversi. Conserviamo i dati originali: prima degli H2H verificare queste identita'.", ""]
        lines += [f"- {name}: {', '.join(ids)}." for name, ids in report["identity_warnings"].items()]
    else:
        lines += ["Nessun nome con piu' identificativi rilevato nel campione. Questo controllo non certifica l'intero archivio."]
    lines += ["## Fonti e riproducibilita'", "", "Dati per uso personale: mantenere cache e risultati dettagliati fuori dai commit pubblici.", ""]
    for filename, metadata in report["source_files"].items():
        lines += [f"- [{filename}]({metadata['url']}): scaricato {metadata['retrieved_at']}; modificato nella fonte {metadata['source_modified_at']}; SHA-256 `{metadata['sha256']}`."]
    lines += [""] + [f"- [{name}]({url})" for name, url in report["rules"].items()]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True, help="Ultima data inclusa, YYYY-MM-DD")
    parser.add_argument("--offline", action="store_true", help="Usa la cache e controllane gli hash")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache" / "tml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "research" / "local")
    args = parser.parse_args()
    if args.as_of.year != YEAR:
        parser.error("Questa prova verifica soltanto la stagione 2026.")
    datasets, manifest = load_sources(args.cache_dir, args.offline)
    matches, finished, counts, duplicates = select_matches(datasets, args.as_of)
    if not matches:
        raise ValueError("Nessun incontro trovato per Z355 nella finestra richiesta.")
    report = build_report(matches, finished, args.as_of, manifest, counts, duplicates)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "zverev-2026.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "zverev-2026.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print("Report:", args.output_dir / "zverev-2026.md")


if __name__ == "__main__":
    main()
