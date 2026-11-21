"""Screen official Challenger qualifying PDFs for cohort surnames (no imports).
Requires PyMuPDF for this optional research command only.
Candidates require manual identity and result verification, including dates.
"""
import argparse
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline",action="store_true")
    p.add_argument("--delay",type=float,default=3)
    args=p.parse_args()
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
                if "QUALIFYING" not in text.upper() or "2026" not in text:
                    raise ValueError("Qualifying/year not confirmed in PDF")
                result["source"]=resource.metadata()
                result["candidates"]=[]
                norm=" "+normalized(text)+" "
                for player in roster:
                    surname=normalized(player["name"].split()[-1])
                    if " "+surname+" " in norm:
                        lines=text.splitlines()
                        contexts=[" | ".join(lines[max(0,i-2):i+4]) for i,line in enumerate(lines) if " "+surname+" " in " "+normalized(line)+" "]
                        result["candidates"].append({**player,"surname_contexts":contexts})
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
            Path("research/local/challenger-qualifying-screen-2026.json").write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Entries",len(reports),"PDFs read",sum("source" in r for r in reports),"pending or errors",sum("error" in r for r in reports),"candidate draws",sum(bool(r.get("candidates")) for r in reports),flush=True)


if __name__=="__main__":main()
