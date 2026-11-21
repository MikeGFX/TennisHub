"""Read-only comparison of the selected cohort with Tennis Abstract classic pages.

Run: python -B -m scripts.census_season --season 2026
External-only records are review candidates, never automatic imports or proof
of omissions. The two sites may share upstream data. Event dates may be week
start dates: newer results in an existing event can postdate the local snapshot.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from urllib.error import HTTPError
import time

from tennishub.database import open_existing, latest_import
from tennishub.sources import SourceClient


def name_key(value):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower())


def edition_key(value):
    if value.endswith("-davis-cup"):
        return value
    parts = value.split("-")
    if re.match(r"^\d{4}-M-DC-", value):
        return parts[0] + "-davis-cup"
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise ValueError("Unrecognized edition identifier: " + value)
    return parts[0] + "-" + str(int(parts[1]))


def parse_page(body, expected_id):
    text = body.decode("utf-8")
    identity = re.search(r"var atp_id\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not identity or identity.group(1).upper() != expected_id.upper():
        raise ValueError("Missing or mismatched ATP identity")
    marker = re.search(r"var matchmx\s*=\s*", text)
    if not marker:
        raise ValueError("Complete results table not found")
    rows, _ = json.JSONDecoder().raw_decode(text[marker.end():])
    if not isinstance(rows, list) or any(not isinstance(row, list) or len(row) < 44 for row in rows):
        raise ValueError("Unexpected match schema")
    return rows


def signature(edition, round_, opponent, outcome):
    return (edition_key(edition), round_, name_key(opponent), outcome)


def compare(connection, snapshot, player, rows):
    pid = player["id"]
    local = []
    for row in connection.execute("SELECT m.*, pw.name winner_name, pl.name loser_name FROM matches m JOIN players pw ON pw.id=m.winner_id JOIN players pl ON pl.id=m.loser_id WHERE m.import_id=? AND (m.winner_id=? OR m.loser_id=?)", (snapshot["id"], pid, pid)):
        won = row["winner_id"] == pid
        raw = json.loads(row["raw_json"])
        key = signature((str(snapshot["season"])+"-davis-cup") if raw.get("tourney_level")=="D" else raw["tourney_id"], row["round"], row["loser_name"] if won else row["winner_name"], "W" if won else "L")
        local.append(key)
    external, records, skipped = [], {}, []
    for row in rows:
        day = row[0]
        if not isinstance(day, str) or not re.fullmatch(r"\d{8}", day):
            raise ValueError("Invalid external tournament date")
        if not day.startswith(str(snapshot["season"])):
            continue
        if day > snapshot["as_of"].replace("-", ""):
            skipped.append({"date": day, "event": row[1]})
            continue
        key = signature(row[43], row[8], row[11], row[4])
        external.append(key)
        records[key] = {"edition": key[0], "event": row[1], "category": row[3], "round": row[8], "opponent": row[11], "outcome": row[4], "score": row[9], "date": day}
    lc, ec = Counter(local), Counter(external)
    only_external, only_local = ec-lc, lc-ec
    local_events = {key[0] for key in local}
    return {**player, "local_matches": len(local), "external_matches": len(external),
            "matched": sum((lc & ec).values()),
            "external_only": [dict(records[key], occurrences=count, new_edition=key[0] not in local_events) for key,count in sorted(only_external.items())],
            "local_only": [{"edition":key[0], "round":key[1], "opponent_key":key[2], "outcome":key[3], "occurrences":count} for key,count in sorted(only_local.items())],
            "after_cutoff": skipped}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--season",type=int,default=2026)
    p.add_argument("--db",default="data/local/tennishub.sqlite3")
    p.add_argument("--offline",action="store_true")
    p.add_argument("--delay",type=float,default=3.0,help="Minimum seconds between remote requests")
    p.add_argument("--output",default="research/local/census-2026.json")
    args=p.parse_args()
    client=SourceClient(".cache/inventory",offline=args.offline)
    reports=[]
    with open_existing(args.db) as connection:
        snapshot=latest_import(connection,args.season)
        roster=connection.execute("SELECT p.id,p.name,r.rank FROM rankings r JOIN players p ON p.id=r.player_id WHERE r.import_id=? ORDER BY r.rank",(snapshot["id"],)).fetchall()
        remote_blocked = False
        last_request = 0
        for row in roster:
            player=dict(row)
            slug=re.sub(r"[^A-Za-z0-9]", "", unicodedata.normalize("NFKD", player["name"]).encode("ascii","ignore").decode())
            url="https://www.tennisabstract.com/cgi-bin/player-classic.cgi?p="+quote(slug)
            try:
                try:
                    resource=SourceClient(".cache/inventory",offline=True).get("ta-"+player["id"],url)
                except FileNotFoundError:
                    if args.offline or remote_blocked:
                        raise ValueError("Not cached; remote comparison pending")
                    time.sleep(max(0,args.delay-(time.monotonic()-last_request)))
                    last_request=time.monotonic()
                    resource=client.get("ta-"+player["id"],url)
                result=compare(connection,snapshot,player,parse_page(resource.body,player["id"]))
                result["source"]=resource.metadata()
            except HTTPError as error:
                if error.code in (403,429):
                    remote_blocked=True
                result={**player,"error":str(error),"url":url}
            except Exception as error:
                result={**player,"error":str(error),"url":url}
            reports.append(result)
            print(player["rank"], player["name"], result.get("error") or "matched=%s external-only=%s local-only=%s" % (result["matched"],len(result["external_only"]),len(result["local_only"])),flush=True)
        output={"created_at":datetime.now(timezone.utc).isoformat(),"season":args.season,"import_id":snapshot["id"],"as_of":snapshot["as_of"],"ranking_date":snapshot["ranking_date"],"inventory_verified":False,
                "limitations":["Sources may share upstream records.","Tournament dates are not necessarily match dates.","External-only records need manual reconciliation.","A matching page does not certify ITF or qualifying coverage."],"players":reports}
    destination=Path(args.output);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Report:",destination)


if __name__ == "__main__":
    main()
