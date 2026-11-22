"""Audit a public ITF results snapshot against the selected cohort; no imports."""
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime
import csv
import io
import json
from pathlib import Path
import re
import unicodedata

from tennishub.database import open_existing, latest_import
from tennishub.sources import SourceClient

URL="https://www.valuebetennis.com/datasets/valuebetennis-matchs-2026.csv"


def name_key(value):
    return re.sub(r"[^a-z0-9]","",unicodedata.normalize("NFKD",value).encode("ascii","ignore").decode().lower())


def audit_rows(rows, roster, as_of, aliases=None):
    aliases=aliases or {}
    names={name_key(p["name"]):p["id"] for p in roster}
    alias_keys={name_key(info["alias"]):(pid,info["source_player_id"]) for pid,info in aliases.items()}
    valid=[];invalid=[];excluded=0
    for row in rows:
        if row["genre"]!="atp":continue
        try:
            day=datetime.fromisoformat(row["date"]).date()
        except (ValueError,TypeError):
            invalid.append({"match_id":row.get("match_id"),"reason":"invalid_date"});continue
        if day.year!=2026 or day>as_of:
            excluded+=1;continue
        p1,p2=row["joueur1_id"],row["joueur2_id"]
        if not p1 or not p2 or p1==p2 or not row["joueur1"] or not row["joueur2"] or row["vainqueur_id"] not in (p1,p2) or not row["score"]:
            invalid.append({"match_id":row.get("match_id"),"reason":"incomplete_result_or_identity"});continue
        valid.append(row)
    mapped=defaultdict(set)
    for row in valid:
        for side in ("joueur1","joueur2"):
            value=name_key(row[side]);pid=names.get(value)
            if value in alias_keys:
                pid,expected=alias_keys[value]
                if row[side+"_id"]!=expected:raise ValueError("Source alias ID changed; review required")
            if pid:mapped[pid].add(row[side+"_id"])
    id_map={}
    for pid,values in mapped.items():
        for value in values:
            if value in id_map and id_map[value]!=pid:raise ValueError("One source ID maps to different cohort players")
            id_map[value]=pid
    itf=[row for row in valid if row["categorie"]=="ITF"]
    hits=[];source_names=Counter()
    for row in itf:
        for side in ("joueur1","joueur2"):
            source_names[(row[side+"_id"],row[side])]+=1
            pid=id_map.get(row[side+"_id"])
            if pid:hits.append({"player_id":pid,"source_player_id":row[side+"_id"],"source_name":row[side],"match_id":row["match_id"],"date":row["date"],"event":row["tournoi"],"event_id":row["tournoi_id"],"source_round":row["tour"],"score":row["score"]})
    similar=[]
    for (source_id,name),count in sorted(source_names.items()):
        words={name_key(word) for word in name.split()}
        for p in roster:
            if name_key(p["name"].split()[-1]) in words:
                similar.append({"cohort_player_id":p["id"],"cohort_name":p["name"],"source_player_id":source_id,"source_name":name,"appearances":count})
    return {"source_rows":len(rows),"male_rows_through_cutoff":len(valid),"excluded_male_rows_by_date":excluded,
            "invalid_male_rows":invalid,"itf_matches_observed":len(itf),"itf_event_ids_observed":len({r["tournoi_id"] for r in itf}),
            "first_itf_timestamp":min((r["date"] for r in itf),default=None),"last_itf_timestamp":max((r["date"] for r in itf),default=None),
            "itf_month_counts":dict(sorted(Counter(r["date"][:7] for r in itf).items())),"source_round_counts":dict(sorted(Counter(r["tour"] for r in itf).items())),
            "cohort_size":len(roster),"mapped_cohort_players":len(mapped),
            "player_mappings":[{**p,"source_player_ids":sorted(mapped.get(p["id"],set()))} for p in roster],
            "unmapped_players":[p for p in roster if not mapped.get(p["id"])],"ambiguous_player_mappings":[pid for pid,values in mapped.items() if len(values)>1],
            "cohort_itf_candidates":hits,"similar_name_candidates":similar,
            "inventory_verified":False,"absence_of_itf_participation_certified":False,
            "limitations":["Publisher includes only live-observed settled matches, not a certified tournament census.","Zero hits in this snapshot does not prove absence from all ITF events.","Player mappings and raw round codes are diagnostic only; no records or points are imported."]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline",action="store_true")
    parser.add_argument("--output",default="research/local/itf-valuebetennis-audit-2026.json")
    args=parser.parse_args()
    resource=SourceClient(".cache/inventory",offline=args.offline).get("valuebetennis-matchs-2026.csv",URL)
    alias_proof=json.loads(Path("research/valuebetennis-player-aliases-2026.json").read_text(encoding="utf-8"))
    if resource.sha256!=alias_proof["source_sha256"]:raise ValueError("Source snapshot changed; revalidate the alias evidence")
    reader=csv.DictReader(io.StringIO(resource.body.decode("utf-8-sig")),delimiter=";")
    required={"match_id","date","genre","categorie","joueur1","joueur1_id","joueur2","joueur2_id","vainqueur_id","score","tournoi","tournoi_id","tour"}
    if not required.issubset(reader.fieldnames or []):raise ValueError("Unexpected ITF snapshot schema")
    with open_existing("data/local/tennishub.sqlite3") as connection:
        snapshot=latest_import(connection,2026)
        if snapshot["id"]!=alias_proof["import_id"]:raise ValueError("Local snapshot changed; revalidate alias comparisons")
        roster=[dict(r) for r in connection.execute("SELECT p.id,p.name FROM rankings r JOIN players p ON p.id=r.player_id WHERE r.import_id=? ORDER BY r.rank",(snapshot["id"],))]
        report=audit_rows(list(reader),roster,date.fromisoformat(snapshot["as_of"]),alias_proof["players"])
        report.update(source=resource.metadata(),import_id=snapshot["id"],ranking_date=snapshot["ranking_date"],as_of=snapshot["as_of"],
                      attribution="Valuebetennis, Resultats et cotes de tennis depuis 2021, https://www.valuebetennis.com/donnees.htm",license="CC BY 4.0",license_source="https://www.valuebetennis.com/donnees.htm")
    destination=Path(args.output);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ITF matches observed:",report["itf_matches_observed"],"mapped players:",report["mapped_cohort_players"],"cohort candidates:",len(report["cohort_itf_candidates"]),"invalid rows:",len(report["invalid_male_rows"]))
    print("Absence or inventory completeness is not certified. Output:",destination)


if __name__=="__main__":main()
