"""Accesso alle fonti pubbliche TML, cache verificata e validazione degli schemi."""

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://stats.tennismylife.org"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(content):
    return hashlib.sha256(content).hexdigest()


@dataclass
class Resource:
    name: str
    url: str
    body: bytes
    retrieved_at: str
    modified_at: str = None

    @property
    def sha256(self):
        return digest(self.body)

    def metadata(self):
        return {"name": self.name, "url": self.url, "sha256": self.sha256,
                "retrieved_at": self.retrieved_at, "modified_at": self.modified_at}


class SourceClient:
    def __init__(self, cache_dir, offline=False):
        self.cache_dir = Path(cache_dir)
        self.offline = offline

    def get(self, name, url, modified_at=None):
        ref = self.cache_dir / "refs" / (digest(url.encode()) + ".json")
        if self.offline:
            metadata = json.loads(ref.read_text(encoding="utf-8"))
            content = (self.cache_dir / "objects" / metadata["sha256"]).read_bytes()
            if metadata["url"] != url or digest(content) != metadata["sha256"]:
                raise ValueError("Cache non valida per " + name)
            return Resource(name, url, content, metadata["retrieved_at"], metadata.get("modified_at"))
        with urlopen(Request(url, headers={"User-Agent": "TennisHub-personal-import/0.1"}), timeout=30) as response:
            content = response.read()
            modified_at = modified_at or response.headers.get("Last-Modified")
        resource = Resource(name, url, content, utc_now(), modified_at)
        obj = self.cache_dir / "objects" / resource.sha256
        obj.parent.mkdir(parents=True, exist_ok=True)
        ref.parent.mkdir(parents=True, exist_ok=True)
        obj.write_bytes(content)
        temporary = ref.with_suffix(".tmp")
        temporary.write_text(json.dumps(resource.metadata()) + "\n", encoding="utf-8")
        temporary.replace(ref)
        return resource


def json_object(resource):
    data = json.loads(resource.body)
    if not isinstance(data, dict):
        raise ValueError("Oggetto JSON atteso: " + resource.name)
    return data


def ranking_dates(resource):
    values = json_object(resource).get("dates")
    if not isinstance(values, list) or not values:
        raise ValueError("Elenco date classifica assente.")
    return sorted({date.fromisoformat(value[:10]) for value in values})


def top_rankings(resource, limit=50):
    rows = json_object(resource).get("rankings")
    if not isinstance(rows, list):
        raise ValueError("Classifica assente dalla risposta TML.")
    selected = []
    for row in rows:
        rank = int(row["rank"])
        if 1 <= rank <= limit:
            if not isinstance(row["id"], str) or not isinstance(row["name"], str):
                raise ValueError("Nome o ID assente nella classifica.")
            player_id, name = str(row["id"]).strip().upper(), str(row["name"]).strip()
            points = int(row["points"])
            if not player_id or not name or points < 0:
                raise ValueError("Giocatore incompleto nella classifica.")
            selected.append({"id": player_id, "name": name, "rank": rank,
                             "points": points, "ioc": str(row.get("ioc") or "").strip()})
    if sorted(row["rank"] for row in selected) != list(range(1, limit + 1)):
        raise ValueError(f"La classifica non contiene esattamente le posizioni 1–{limit}.")
    if len({row["id"] for row in selected}) != limit:
        raise ValueError("Identificativi giocatore duplicati nella classifica.")
    return sorted(selected, key=lambda row: row["rank"])


def csv_rows(resource):
    reader = csv.DictReader(io.StringIO(resource.body.decode("utf-8-sig")))
    required = {"tourney_id", "tourney_name", "tourney_date", "tourney_level", "draw_size",
                "surface", "round", "winner_id", "winner_name", "loser_id", "loser_name", "score"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Schema CSV inatteso: " + resource.name)
    for line, row in enumerate(reader, 2):
        yield line, row


def load_bundle(client, season, as_of, requested_ranking_date=None):
    dates_resource = client.get("ranking-dates", BASE + "/api/ranking/dates")
    available_dates = ranking_dates(dates_resource)
    if requested_ranking_date:
        if requested_ranking_date not in available_dates or requested_ranking_date > as_of:
            raise ValueError("Data classifica non disponibile o successiva al limite richiesto.")
        ranking_date = requested_ranking_date
    else:
        eligible = [day for day in available_dates if day <= as_of]
        if not eligible:
            raise ValueError("Nessuna classifica disponibile entro la data richiesta.")
        ranking_date = max(eligible)
    rankings = client.get("rankings", BASE + "/api/ranking?date=" + str(ranking_date))
    catalog = client.get("data-files", BASE + "/api/data-files")
    files = json_object(catalog).get("files")
    if not isinstance(files, list):
        raise ValueError("Indice dei CSV non valido.")
    by_name = {entry["name"]: entry for entry in files}
    names = [f"{season}.csv", f"{season}_challenger.csv", f"atp_quali/{season}_atp_quali.csv"]
    if season == as_of.year:
        names += ["ongoing_tourneys.csv", "challenger_ongoing_tourneys.csv"]
    resources = [dates_resource, rankings, catalog]
    datasets = []
    for name in names:
        if name not in by_name:
            raise ValueError("File necessario assente dall'indice TML: " + name)
        entry = by_name[name]
        if not entry["url"].startswith(BASE + "/data/"):
            raise ValueError("URL inatteso nell'indice TML.")
        resource = client.get(name, entry["url"], entry.get("mtime"))
        resources.append(resource)
        datasets.append(resource)
    from .supplements import load_supplements
    extra_datasets, extra_resources = load_supplements(season, as_of)
    return ranking_date, top_rankings(rankings), datasets + extra_datasets, resources + extra_resources
