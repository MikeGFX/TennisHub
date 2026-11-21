"""Versioned, verified transcriptions of individual missing results."""
from datetime import date
import json
from pathlib import Path

from .sources import Resource, digest

ROOT = Path(__file__).resolve().parents[1] / "data" / "curated"


def load_supplements(season, as_of, root=ROOT):
    manifest_path = root / f"{season}.json"
    if not manifest_path.exists():
        return [], []
    body = manifest_path.read_bytes()
    manifest = json.loads(body)
    if manifest["season"] != season:
        raise ValueError("Stagione non coerente nel registro delle integrazioni.")
    datasets = []
    names = set()
    for item in manifest["items"]:
        if date.fromisoformat(item["available_by"]) > as_of:
            continue
        filename = item["file"]
        if Path(filename).name != filename or not filename.endswith(".csv"):
            raise ValueError("Percorso non valido per un integrazione.")
        name = item["name"]
        if not name.startswith("challenger_quali/curated/") or name in names:
            raise ValueError("Nome o fase dell integrazione non validi.")
        names.add(name)
        content = (root / filename).read_bytes()
        if digest(content) != item["sha256"]:
            raise ValueError("Hash della trascrizione non valido: " + filename)
        datasets.append(Resource(name, item["source_url"] + "#verified-transcription", content,
                                 item["verified_on"] + "T00:00:00+00:00"))
    if not datasets:
        return [], []
    manifest_resource = Resource(f"curated/{season}.json",
        f"https://github.com/MikeGFX/TennisHub/blob/main/data/curated/{season}.json",
        body, max(item["verified_on"] for item in manifest["items"]) + "T00:00:00+00:00")
    return datasets, [*datasets, manifest_resource]
