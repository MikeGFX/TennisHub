"""Screen official Challenger qualifying PDFs for cohort surnames (no imports).
Requires PyMuPDF for this optional research command only.
Candidates require manual identity and result verification, including dates.
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
from tennishub.sources import SourceClient


def normalized(text):
    return re.sub(r"[^A-Z0-9]+", " ", unicodedata.normalize("NFKD",text).encode("ascii","ignore").decode().upper()).strip()


def identify_candidate(text, player):
    """Distinguish complete roster names from homonyms and incidental words."""
    surname = normalized(player["name"].split()[-1])
    families = {"Alejandro Davidovich Fokina":"Davidovich Fokina", "Felix Auger-Aliassime":"Auger-Aliassime",
                "Botic van de Zandschulp":"Van de Zandschulp", "Botic Van De Zandschulp":"Van de Zandschulp",
                "Luca Van Assche":"Van Assche", "Alex de Minaur":"De Minaur"}
    expected_family = normalized(families.get(player["name"],player["name"].split()[-1]))
    entries = []
    truncated_family_match = False
    for line in text.splitlines():
        match = re.fullmatch(r"([^,]+),\s*(.+)", line.strip())
        if not match:
            continue
        family, given = match.groups()
        clean_family = normalized(re.sub(r"^\d+\s+", "", family))
        truncated = any(mark in family for mark in ("...", "\u2026", "\ufffd"))
        family_prefix = truncated and len(clean_family)>=4 and expected_family.startswith(clean_family)
        if family_prefix:
            truncated_family_match = True
        if " " + surname + " " in " " + normalized(family) + " " or family_prefix:
            entries.append({"printed":line.strip(),"full_name":normalized(given+" "+re.sub(r"^\d+\s+", "", family))})
    exact = [entry for entry in entries if entry["full_name"] == normalized(player["name"])]
    if exact:
        status = "exact_full_name"
    elif entries and all(not any(mark in entry["printed"] for mark in ("...", "\u2026", "\ufffd")) for entry in entries):
        status = "different_full_name_review"
    else:
        status = "ambiguous_or_outside_entrant_list"
    return {"identity_status":status,"printed_entries":entries,"truncated_family_match":truncated_family_match}


def validate_draw(text, event):
    """Validate the year/week and a usable entrant list before screening names."""
    if not re.search(r"(?:QUALIFYING\s+SINGLES|SINGLES\s+QUALIFYING)", text.upper()):
        raise ValueError("Qualifying singles heading not confirmed")
    months = ("January February March April May June July August September October November December").split()
    header = text[:1800]
    if "CHALLENGER" not in header.upper():
        raise ValueError("PDF does not identify an ATP Challenger; circuit/edition requires review")
    found = re.search(r"\b(\d{1,2})\s+("+"|".join(months)+r")\b", header, re.I)
    if not found or not re.search(r"\b2026\b", header):
        raise ValueError("Tournament year/week not confirmed in PDF header")
    observed = date(2026, next(i for i,m in enumerate(months,1) if m.lower()==found.group(2).lower()), int(found.group(1)))
    expected = date.fromisoformat(event["first_recorded_date"])
    if abs((observed-expected).days)>6:
        raise ValueError("PDF week differs from recorded edition; manual verification required")
    entrant_lines = [line for line in text.splitlines() if re.fullmatch(r"[^,]+,\s*.+",line.strip())]
    if len(entrant_lines)<8:
        raise ValueError("Usable qualifying entrant list not confirmed")
    return {"header_date":str(observed),"recorded_event_date":str(expected),"entrant_name_lines":len(entrant_lines)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline",action="store_true")
    p.add_argument("--delay",type=float,default=3)
    p.add_argument("--output",default="research/local/challenger-qualifying-screen-2026.json")
    args=p.parse_args()
    destination=Path(args.output)
    destination.parent.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(Path(".cache/pdf-qa").resolve()))
    import pymupdf
    cache=".cache/inventory"
    client=SourceClient(cache,offline=args.offline)
    reports=[]
    with open_existing("data/local/tennishub.sqlite3") as connection:
        snapshot=latest_import(connection,2026)
        roster=[dict(row) for row in connection.execute("SELECT p.id,p.name FROM rankings r JOIN players p ON p.id=r.player_id WHERE r.import_id=?",(snapshot["id"],))]
        events=connection.execute("SELECT * FROM events WHERE import_id=? AND category='C' AND stage='main' ORDER BY first_recorded_date,edition_id",(snapshot["id"],)).fetchall()
        stopped=False
        for index,event in enumerate(events,1):
            code=event["edition_id"].split("-",1)[1]
            url=f"https://www.protennislive.com/posting/2026/{code}/qs.pdf"
            result={"edition_id":event["edition_id"],"event":event["name"],"url":url}
            try:
                try:
                    resource=SourceClient(cache,offline=True).get("qs-"+code,url)
                except FileNotFoundError:
                    if stopped or args.offline:
                        raise ValueError("Not cached; verification pending")
                    time.sleep(max(0,args.delay))
                    resource=client.get("qs-"+code,url)
                if not resource.body.startswith(b"%PDF"):
                    raise ValueError("Not a PDF")
                doc=pymupdf.open(stream=resource.body,filetype="pdf")
                text="\n".join(page.get_text() for page in doc)
                result["document_validation"] = validate_draw(text,event)
                result["source"]=resource.metadata()
                result["candidates"]=[]
                norm=" "+normalized(text)+" "
                for player in roster:
                    surname=normalized(player["name"].split()[-1])
                    identification=identify_candidate(text,player)
                    if " "+surname+" " in norm or identification["truncated_family_match"]:
                        lines=text.splitlines()
                        contexts=[" | ".join(lines[max(0,i-2):i+4]) for i,line in enumerate(lines) if " "+surname+" " in " "+normalized(line)+" "]
                        result["candidates"].append({**player,**identification,"surname_contexts":contexts})
                if result["candidates"]:
                    Path(".cache/qs-2026-"+code+".txt").write_text(text,encoding="utf-8")
            except HTTPError as error:
                result["error"]=str(error)
                if error.code in (403,429):stopped=True
            except Exception as error:
                result["error"]=str(error)
            reports.append(result)
            if index%20==0 or result.get("candidates"):
                print(index,"/",len(events),event["name"],result.get("error") or [x["name"] for x in result.get("candidates",[])],flush=True)
            output={"import_id":snapshot["id"],"as_of":snapshot["as_of"],"inventory_verified":False,"method":"Surname screening only; confirm identity, played results and event dates before importing.","draws":reports}
            destination.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Entries",len(reports),"PDFs read",sum("source" in r for r in reports),"pending or errors",sum("error" in r for r in reports),"candidate draws",sum(bool(r.get("candidates")) for r in reports),flush=True)


if __name__=="__main__":main()
