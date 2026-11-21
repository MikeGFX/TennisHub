"""Importazione ripetibile di un intervallo storico con fonti condivise per esecuzione."""

from .importer import import_bundle
from .sources import BASE, json_object, load_bundle


class SnapshotClient:
    def __init__(self, client):
        self.client = client
        self.resources = {}

    def get(self, name, url, modified_at=None):
        if url not in self.resources:
            self.resources[url] = self.client.get(name, url, modified_at)
        return self.resources[url]


def import_history(connection, client, first_year, last_year, as_of, ranking_date=None, progress=None):
    if not 1968 <= first_year <= last_year < as_of.year:
        raise ValueError("Scegli un intervallo di stagioni passate dal 1968 all'anno precedente alla data limite.")
    shared = SnapshotClient(client)
    catalog = json_object(shared.get("data-files", BASE + "/api/data-files"))
    files = catalog.get("files")
    if not isinstance(files, list):
        raise ValueError("Indice dei CSV non valido.")
    available = {entry["name"] for entry in files}
    missing = [name for year in range(first_year, last_year + 1)
               for name in (f"{year}.csv", f"{year}_challenger.csv", f"atp_quali/{year}_atp_quali.csv")
               if name not in available]
    if missing:
        raise ValueError("Storico non avviato: file necessari assenti: " + ", ".join(missing))
    results = []
    for year in range(first_year, last_year + 1):
        try:
            selected_date, rankings, datasets, resources = load_bundle(shared, year, as_of, ranking_date)
            result = import_bundle(connection, year, as_of, selected_date, rankings, datasets, resources)
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise ValueError(f"Storico interrotto nella stagione {year}: {error}. Le stagioni completate sono conservate.") from error
        results.append(result)
        if progress:
            progress(result)
    return {"from_season": first_year, "to_season": last_year, "as_of": str(as_of),
            "ranking_date": results[0]["ranking_date"], "seasons": results,
            "imported": sum(not result["reused"] for result in results),
            "reused": sum(result["reused"] for result in results)}
