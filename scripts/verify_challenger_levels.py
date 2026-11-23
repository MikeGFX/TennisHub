"""Verify Challenger edition levels from official ProTennisLive main-draw PDFs.

Research command only (requires PyMuPDF from .cache/pdf-qa). For each Challenger
edition played by the selected cohort in the season snapshot it checks circuit,
tournament week, city, the printed "Challenger NN" label and the printed points
ladder against the validated table. Only fully consistent editions are proposed
for the registry; everything else stays pending for manual review.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.error import HTTPError

from tennishub.database import open_existing, latest_import
from tennishub.points import TABLES
from tennishub.sources import SourceClient

MONTHS = "January February March April May June July August September October November December".split()


def normalized(text):
    return re.sub(r"[^A-Z0-9]+", " ", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()).strip()


def expected_ladder(level):
    table = TABLES["C" + str(level)]
    return [table[key] for key in ("R32", "R16", "QF", "SF", "F", "W")]


def validate_main_draw(text, event, season):
    """Return the verified level and the checks performed, or raise ValueError."""
    header = text[:2500]
    if "MAIN DRAW SINGLES" not in header.upper():
        raise ValueError("Main draw singles heading not confirmed")
    label = re.search(r"\|\s*Challenger\s+(\d+)\b", header)
    if not label:
        raise ValueError("PDF does not print an ATP Challenger level")
    level = int(label.group(1))
    if "C" + str(level) not in TABLES:
        raise ValueError(f"Unsupported Challenger level {level}")
    dates = re.search(r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")\b[^|\n]*?\b(20\d\d)\s*\|", header)
    if not dates:
        raise ValueError("Tournament week not found in PDF header")
    day, month = int(dates.group(1)), MONTHS.index(dates.group(2).capitalize()) + 1
    recorded = date.fromisoformat(event["first_recorded_date"])
    candidates = [date(year, month, day) for year in (season - 1, season)]
    start = min(candidates, key=lambda value: abs((value - recorded).days))
    if abs((start - recorded).days) > 6:
        raise ValueError(f"PDF week {start} differs from recorded edition {recorded}")
    ladder = [int(value) for value in re.findall(r"(\d+)\s+pts?\b", header)[:6]]
    if ladder != expected_ladder(level):
        raise ValueError(f"Printed points {ladder} differ from Challenger {level} table {expected_ladder(level)}")
    city = normalized(re.sub(r"\s+\d+$", "", event["name"])).split()[0]
    if city not in normalized(header):
        raise ValueError(f"City '{event['name']}' not found in PDF header")
    return level, {"printed_label": label.group(0).strip("| "), "printed_points": ladder,
                   "pdf_week_start": str(start), "recorded_first_date": str(recorded)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--delay", type=float, default=6)
    parser.add_argument("--output", default="research/local/challenger-levels-2025.json")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(".cache/pdf-qa").resolve()))
    import pymupdf
    cache = ".cache/inventory"
    online = SourceClient(cache, offline=args.offline)
    reports, stopped = [], False
    with open_existing("data/local/tennishub.sqlite3") as connection:
        snapshot = latest_import(connection, args.season)
        events = connection.execute(
            "SELECT DISTINCT e.* FROM events e JOIN matches m ON m.import_id=e.import_id AND m.edition_id=e.edition_id "
            "JOIN rankings r ON r.import_id=e.import_id AND r.player_id IN (m.winner_id, m.loser_id) "
            "WHERE e.import_id=? AND e.category='C' AND e.stage='main' ORDER BY e.first_recorded_date, e.edition_id",
            (snapshot["id"],)).fetchall()
        for index, event in enumerate(events, 1):
            code = event["edition_id"].split("-", 1)[1]
            url = f"https://www.protennislive.com/posting/{args.season}/{code}/mds.pdf"
            result = {"edition_id": event["edition_id"], "event": event["name"], "draw_size": event["draw_size"], "url": url}
            try:
                try:
                    resource = SourceClient(cache, offline=True).get(f"mds-{args.season}-{code}", url)
                except FileNotFoundError:
                    if stopped or args.offline:
                        raise ValueError("Not cached; verification pending")
                    time.sleep(max(0, args.delay))
                    resource = online.get(f"mds-{args.season}-{code}", url)
                if not resource.body.startswith(b"%PDF"):
                    raise ValueError("Not a PDF")
                text = "\n".join(page.get_text() for page in pymupdf.open(stream=resource.body, filetype="pdf"))
                if str(event["draw_size"]) != "32":
                    raise ValueError("Draw size other than 32 requires manual review")
                result["level"], result["checks"] = validate_main_draw(text, event, args.season)
                result["source"] = resource.metadata()
            except HTTPError as error:
                result["error"] = str(error)
                stopped = stopped or error.code in (403, 429)
            except Exception as error:
                result["error"] = str(error)
            reports.append(result)
            if index % 20 == 0 or "error" in result:
                print(index, "/", len(events), event["name"], result.get("error", result.get("level")), flush=True)
        output = {"season": args.season, "import_id": snapshot["id"], "as_of": snapshot["as_of"],
                  "method": "Official main-draw PDF: circuit label, week, city and printed points ladder must all agree.",
                  "editions": reports}
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Editions", len(reports), "verified", sum("level" in r for r in reports), "pending", sum("error" in r for r in reports), flush=True)


if __name__ == "__main__":
    main()
