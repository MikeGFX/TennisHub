"""Read-only secondary-source review of Santa Cruz 2 qualifying results.
The official PDF remains unverified. This command never imports results.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urljoin

from tennishub.database import open_existing, latest_import
from tennishub.sources import SourceClient

URL = "https://www.statpick.ai/tournaments/tennis/santa-cruz-de-la-sierra-2-challenger-atp/2026/950103974"


def key(value):
    return " ".join(re.findall(r"[a-z0-9]+",unicodedata.normalize("NFKD",value).encode("ascii","ignore").decode().lower()))


class QualifyingResults(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip=0
        self.heading=None
        self.heading_text=[]
        self.title=""
        self.day=""
        self.round=""
        self.match=None
        self.in_player=False
        self.player_won=False
        self.span_depth=0
        self.name=[]
        self.matches=[]
        self.qualifying_list_depth=0

    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag in ("script","style"):
            self.skip+=1
        if self.skip:return
        if tag in ("title","h3","h4"):
            self.heading=tag;self.heading_text=[]
        if tag=="ul" and (self.qualifying_list_depth or self.round.startswith("Qualifying ")):
            self.qualifying_list_depth+=1
        if tag=="a" and self.qualifying_list_depth and attributes.get("href","").startswith("/matches/tennis/") and self.round.startswith("Qualifying "):
            self.match={"source_round":self.round,"source_date":self.day,"url":urljoin(URL,attributes["href"]),"players":[]}
        if self.match is not None:
            if tag=="p":
                self.in_player=True
                self.player_won="data-win" in attributes
            if tag=="span" and self.in_player:
                self.span_depth+=1
                if self.span_depth==1:self.name=[]

    def handle_data(self,data):
        if self.skip:return
        if self.heading:self.heading_text.append(data)
        if self.match is not None and self.span_depth:self.name.append(data)

    def handle_endtag(self,tag):
        if tag in ("script","style"):
            self.skip=max(0,self.skip-1);return
        if self.skip:return
        if tag=="ul" and self.qualifying_list_depth:
            self.qualifying_list_depth-=1
            if not self.qualifying_list_depth:self.round=""
        if tag==self.heading:
            text=" ".join("".join(self.heading_text).split())
            if tag=="title":self.title=text
            if tag=="h3":self.day=text;self.round=""
            if tag=="h4":self.round=text
            self.heading=None
        if self.match is not None:
            if tag=="span" and self.span_depth:
                self.span_depth-=1
                if self.span_depth==0:
                    name=re.sub(r"^[^\w]+","","".join(self.name)).strip()
                    name=re.sub(r"\s+\([^)]*\)$","",name)
                    self.match["players"].append(name)
                    if self.player_won:self.match["source_winner"]=name
            if tag=="p":self.in_player=False
            if tag=="a":
                if len(self.match["players"])!=2 or not all(self.match["players"]):
                    raise ValueError("Unexpected qualifying match structure")
                self.matches.append(self.match);self.match=None;self.in_player=False;self.span_depth=0


def parse_results(body):
    parser=QualifyingResults();parser.feed(body.decode("utf-8"))
    title=key(parser.title)
    if "santa cruz de la sierra 2" not in title or "2026" not in title:
        raise ValueError("Wrong tournament or year")
    if not parser.matches:
        raise ValueError("No qualifying results found")
    unique={}
    for match in parser.matches:
        if not any(day in match["source_date"] for day in ("Oct 11", "Oct 12")):
            raise ValueError("Qualifying date outside expected tournament")
        if match["url"] in unique and unique[match["url"]]!=match:
            raise ValueError("Conflicting duplicate results")
        unique[match["url"]]=match
    return list(unique.values())


WIKI_URL = "https://it.wikipedia.org/wiki/Santa_Cruz_Challenger_II_2026_-_Singolare"


class QualifiersList(HTMLParser):
    def __init__(self):
        super().__init__();self.heading=None;self.buffer=[];self.active=False;self.name=None;self.names=[];self.title=""
    def handle_starttag(self,tag,attrs):
        if tag in ("title","h2"):
            self.heading=tag;self.buffer=[]
        if tag=="li" and self.active:self.name=[]
    def handle_data(self,data):
        if self.heading:self.buffer.append(data)
        if self.name is not None:self.name.append(data)
    def handle_endtag(self,tag):
        if tag==self.heading:
            text=" ".join("".join(self.buffer).split())
            if tag=="title":self.title=text
            else:self.active=key(text).startswith("qualificati")
            self.heading=None
        if tag=="li" and self.name is not None:
            value=re.sub(r"\s*\([^)]*\)","","".join(self.name)).strip()
            self.names.append(value);self.name=None


def parse_qualifiers(body):
    parser=QualifiersList();parser.feed(body.decode("utf-8"))
    if "santa cruz challenger ii 2026" not in key(parser.title):
        raise ValueError("Wrong edition for qualifiers list")
    if len(parser.names)!=6 or len(set(map(key,parser.names)))!=6:
        raise ValueError("Expected six distinct qualifiers")
    return parser.names


def qualifier_key(name):
    value=key(name)
    aliases={"arklon huertas del pino":"arklon huertas del pino cordova"}
    return aliases.get(value,value)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline",action="store_true")
    p.add_argument("--output",default="research/local/santa-cruz-secondary-review-2026.json")
    args=p.parse_args()
    resource=SourceClient(".cache/inventory",offline=args.offline).get("santa-statpick",URL)
    matches=parse_results(resource.body)
    wiki=SourceClient(".cache/inventory",offline=args.offline).get("santa-wiki-it",WIKI_URL)
    qualifiers=parse_qualifiers(wiki.body)
    final_round=[m for m in matches if m["source_round"].startswith("Qualifying R3")]
    winners=[m.get("source_winner","") for m in final_round]
    if len(winners)!=6 or set(map(qualifier_key,winners))!=set(map(qualifier_key,qualifiers)):
        raise ValueError("Qualifying winners disagree with corroborating qualifiers list")
    observed=sorted({name for match in matches for name in match["players"]})
    with open_existing("data/local/tennishub.sqlite3") as connection:
        snapshot=latest_import(connection,2026)
        cohort=[dict(row) for row in connection.execute("SELECT p.id,p.name FROM rankings r JOIN players p ON p.id=r.player_id WHERE r.import_id=? ORDER BY r.rank",(snapshot["id"],))]
        candidates=[dict(player,observed_name=name) for player in cohort for name in observed
                    if key(name)==key(player["name"]) or key(player["name"].split()[-1]) in key(name).split()]
        report={"edition_id":"2026-3143","event":"Santa Cruz de la Sierra 2","season":2026,
                "import_id":snapshot["id"],"ranking_date":snapshot["ranking_date"],"as_of":snapshot["as_of"],"source":resource.metadata(),
                "source_type":"secondary", "corroborating_qualifiers_source":wiki.metadata(), "corroborated_qualifiers":qualifiers,
                "name_variant_note":"Arklon Huertas del Pino and Arklon Huertas Del Pino Cordova are explicitly reconciled in the six-qualifier comparison.","official_document_verified":False,"complete_draw_verified":False,"inventory_verified":False,
                "observed_qualifying_matches":len(matches),"observed_participants":observed,"cohort_candidates":candidates,"matches":matches,
                "limitations":["Only participants in published result cards are compared; absent or unplayed entries are not established.","Source round labels are preserved, not mapped to ATP Q1/Q2.","No ranking points or match results are imported.","Official PDF currently returns an ITF event; primary-source verification remains pending."]}
    destination=Path(args.output);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Secondary qualifying results:",len(matches),"observed participants:",len(observed),"cohort candidates:",len(candidates))
    print("Official document remains pending. Output:",destination)


if __name__=="__main__":main()
