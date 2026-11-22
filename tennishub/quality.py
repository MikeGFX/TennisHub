"""Verifica separata dei punti registrati e della completezza delle stagioni."""

import json
from functools import lru_cache
from pathlib import Path

from .database import latest_import


@lru_cache(maxsize=1)
def season_reviews():
    return json.loads((Path(__file__).with_name("rules") / "season-reviews.json").read_text(encoding="utf-8"))


def historical_priority(year):
    priority = season_reviews().get("historical_priority")
    return priority if priority and year <= priority["through_season"] else None


def inventory_status(snapshot, reviews=None):
    review = (season_reviews() if reviews is None else reviews).get("seasons", {}).get(str(snapshot["season"]), {})
    verified = (review.get("inventory_verified") is True and review.get("import_id") == snapshot["id"]
                and review.get("all_atp_tiers_included") is True and bool(review.get("inventory_sources"))
                and review.get("itf_status") in ("integrated_and_reconciled", "verified_absent_for_cohort")
                and review.get("cohort_size") == json.loads(snapshot["summary_json"])["selected_players"]
                and review.get("ranking_date") == snapshot["ranking_date"])
    return {"historical_priority": historical_priority(snapshot["season"]), "verified": verified, "itf_status": review.get("itf_status", "not_integrated_or_reconciled"),
            "itf_source": review.get("itf_source"),
            "qualifying_status": review.get("qualifying_status", "not_reconciled"),
            "qualifying_census_progress": review.get("census_progress", {}),
            "confirmed_missing_participations": review.get("confirmed_missing_participations", []) if review.get("census_import_id") == snapshot["id"] else [], "notes": review.get("notes", "Inventario completo dei tornei non ancora riconciliato con una fonte indipendente.")}


def assess_season(connection, year, reviews=None):
    from .queries import coverage
    snapshot = latest_import(connection, year)
    points = coverage(connection, year)
    priority = historical_priority(year)
    priority_result = None
    if priority:
        selected = coverage(connection, year, categories=set(priority["categories"]))
        priority_result = {"label": priority["label"], "categories": priority["categories"], "include_qualifying": priority["include_qualifying"],
                           "participations": selected["participations"], "calculated": selected["calculated"], "needs_review": selected["needs_review"],
                           "recorded_points_resolved": bool(selected["participations"]) and selected["needs_review"] == 0,
                           "certifies_complete_season": False, "reasons": selected["reasons"]}
    inventory = inventory_status(snapshot, reviews)
    sources = {row[0] for row in connection.execute("SELECT name FROM sources WHERE import_id=?", (snapshot["id"],))}
    required = {f"{year}.csv", f"{year}_challenger.csv", f"atp_quali/{year}_atp_quali.csv"}
    missing = sorted(required - sources)
    issues = {row[0]: row[1] for row in connection.execute("SELECT code, count(*) FROM issues WHERE import_id=? GROUP BY code", (snapshot["id"],))}
    blockers = []
    if points["needs_review"] or not points["participations"]:
        blockers.append("points_not_fully_resolved")
    if missing:
        blockers.append("required_source_files_missing")
    if not inventory["verified"]:
        blockers.append("tournament_inventory_not_verified")
    if snapshot["as_of"][:4] <= str(year) or points["provisional_events"]:
        blockers.append("season_or_events_not_closed")
    return {"season": year, "as_of": snapshot["as_of"], "ranking_date": snapshot["ranking_date"],
            "import_id": snapshot["id"], "cohort_size": points["players"],
            "recorded_participations": points["participations"], "calculated": points["calculated"],
            "needs_review": points["needs_review"], "provisional_events": points["provisional_events"],
            "recorded_points_percent": round(100 * points["calculated"] / points["participations"], 2) if points["participations"] else None,
            "points_reasons": points["reasons"], "priority": priority_result, "inventory": inventory,
            "missing_source_files": missing, "source_issues": issues,
            "complete": not blockers, "blockers": blockers}


def assess_range(connection, first, last):
    if not 1968 <= first <= last:
        raise ValueError("Intervallo di stagioni non valido.")
    reports = []
    for year in range(last, first - 1, -1):
        try:
            reports.append(assess_season(connection, year))
        except ValueError as error:
            reports.append({"season": year, "complete": False, "blockers": ["not_imported"], "error": str(error)})
    return {"scope": season_reviews()["scope"], "seasons": reports,
            "all_complete": all(report["complete"] for report in reports)}
