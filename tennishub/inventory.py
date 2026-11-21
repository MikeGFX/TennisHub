"""Read-only structural census; matching counts do not certify completeness."""
from collections import Counter
from .database import latest_import

INDIVIDUAL = {"250", "500", "G", "M", "C"}


def census(connection, year):
    snapshot = latest_import(connection, year)
    cohort = {row[0] for row in connection.execute("SELECT player_id FROM rankings WHERE import_id=?", (snapshot["id"],))}
    counts, participants = Counter(), {}
    for row in connection.execute("SELECT edition_id,stage,winner_id,loser_id FROM matches WHERE import_id=?", (snapshot["id"],)):
        key=(row["edition_id"],row["stage"])
        counts[key]+=1
        participants.setdefault(key,set()).update((row["winner_id"],row["loser_id"]))
    events=[dict(row) for row in connection.execute("SELECT * FROM events WHERE import_id=?",(snapshot["id"],))]
    stages={(row["edition_id"],row["stage"]) for row in events}
    summary=Counter((row["category"],row["stage"]) for row in events)
    anomalies=[]
    for event in events:
        if event["category"] not in INDIVIDUAL or event["stage"]!="main" or not event["final_recorded"]:
            continue
        size=event["draw_size"]
        if not size.isdigit():
            continue
        key=(event["edition_id"],"main")
        expected=int(size)-1
        if counts[key]!=expected:
            anomalies.append({"edition_id":key[0],"name":event["name"],"category":event["category"],"draw_size":int(size),"recorded_matches":counts[key],"expected_without_unrecorded_byes":expected,"cohort_players_observed":sorted(participants.get(key,set()) & cohort),"status":"needs_draw_verification"})
    missing_qualifying=[{"edition_id":event["edition_id"],"name":event["name"],"category":event["category"]} for event in events if event["stage"]=="main" and event["category"] in INDIVIDUAL and (event["edition_id"],"qualifying") not in stages]
    return {"season":year,"import_id":snapshot["id"],"as_of":snapshot["as_of"],"ranking_date":snapshot["ranking_date"],"inventory_verified":False,"draws":[{"category":key[0],"stage":key[1],"count":count} for key,count in sorted(summary.items())],"closed_draw_count_anomalies":anomalies,"main_draws_without_qualifying_records":missing_qualifying,"limitations":["Counts cannot detect an entirely absent tournament.","Draw size can differ from actual entrants due to byes.","No qualifying records is a coverage gap, not proof that an event held qualifying.","Players absent from recorded matches can still be missing from a tournament."]}
