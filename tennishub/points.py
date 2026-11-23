"""Punti ottenuti per edizione, distinti dalla selezione del ranking ATP.

Fonte: Rulebook ATP 2026, 9.03 G, pp. 272-273, ripubblicato da ITF.
Le informazioni mancanti producono un valore sconosciuto, mai uno zero implicito.
"""

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

RULES_URL = "https://www.itftennis.com/media/15608/atp-2026-points-table.pdf"
UNITED_URL = "https://www.atptour.com/-/media/0030c0c028734686b55efd45fe463926.pdf"
FINALS_URL = "https://www.nittoatpfinals.com/en/event/points-and-prize-money"
ENGINE_VERSION = "2026.7"
RULES_2025_URL = "https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf"
WALKOVER_URL = "https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook-chapter-10_exhibits_27apr26.pdf"
WALKOVER_2025_URL = "https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-10_exhibits_23dec.pdf"
ROUND_ORDER = {r: i for i, r in enumerate(("Q1", "Q2", "Q3", "RR", "R128", "R64", "R32", "R16", "QF", "SF", "F"))}
LABELS = {"W": "Vincitore", "F": "Finalista", "SF": "Semifinale", "QF": "Quarti",
          "R16": "Ottavi", "R32": "R32", "R64": "R64", "R128": "R128"}
TABLES = {
    "G": {"W": 2000, "F": 1300, "SF": 800, "QF": 400, "R16": 200, "R32": 100, "R64": 50, "R128": 10},
    "M96": {"W": 1000, "F": 650, "SF": 400, "QF": 200, "R16": 100, "R32": 50, "R64": 30, "R128": 10},
    "M56": {"W": 1000, "F": 650, "SF": 400, "QF": 200, "R16": 100, "R32": 50, "R64": 10},
    "50032": {"W": 500, "F": 330, "SF": 200, "QF": 100, "R16": 50, "R32": 0},
    "50048": {"W": 500, "F": 330, "SF": 200, "QF": 100, "R16": 50, "R32": 25, "R64": 0},
    "25032": {"W": 250, "F": 165, "SF": 100, "QF": 50, "R16": 25, "R32": 0},
    "25048": {"W": 250, "F": 165, "SF": 100, "QF": 50, "R16": 25, "R32": 13, "R64": 0},
    "C175": {"W": 175, "F": 90, "SF": 50, "QF": 25, "R16": 13, "R32": 0},
    "C125": {"W": 125, "F": 64, "SF": 35, "QF": 16, "R16": 8, "R32": 0},
    "C100": {"W": 100, "F": 50, "SF": 25, "QF": 14, "R16": 7, "R32": 0},
    "C75": {"W": 75, "F": 44, "SF": 22, "QF": 12, "R16": 6, "R32": 0},
    "C50": {"W": 50, "F": 25, "SF": 14, "QF": 8, "R16": 4, "R32": 0},
}
# (punti qualificato, punti sconfitta ultimo turno, punti sconfitta Q2 negli Slam)
QUALIFYING = {"G": (30, 16, 8), "M96": (20, 10, 0), "M56": (30, 16, 0),
              "50032": (25, 13, 0), "50048": (16, 8, 0),
              "25032": (13, 7, 0), "25048": (8, 4, 0),
              "C175": (6, 3, 0), "C125": (5, 3, 0), "C100": (4, 2, 0),
              "C75": (4, 2, 0), "C50": (3, 1, 0)}


@dataclass
class PointsResult:
    value: int = None
    reason: str = ""
    main_draw: int = None
    qualifying: int = None
    sources: list = field(default_factory=lambda: [RULES_URL])


@lru_cache(maxsize=1)
def challenger_editions():
    """Registri annuali delle edizioni Challenger verificate; le chiavi includono l'anno."""
    editions = {}
    for path in sorted(Path(__file__).with_name("rules").glob("challengers-20??.json")):
        for edition_id, metadata in json.loads(path.read_text(encoding="utf-8")).items():
            if not edition_id.startswith(path.stem[-4:] + "-") or edition_id in editions:
                raise ValueError(f"Edizione Challenger fuori registro annuale o duplicata: {edition_id}")
            editions[edition_id] = metadata
    return editions


@lru_cache(maxsize=None)
def evidence_file(name):
    return json.loads((Path(__file__).with_name("rules") / name).read_text(encoding="utf-8"))


def _seed_number(value):
    try:
        number = Decimal(str(value))
        return int(number) if number.is_finite() and number == number.to_integral_value() and number > 0 else None
    except (InvalidOperation, ValueError):
        return None


def _united_cup_2026(rows, player_id):
    evidence = evidence_file("united-cup-2026.json")
    table = {"RR": (55,45,40,35,25,20,15), "QF": (80,65,55,40,35,25,20),
             "SF": (130,105,90,60,40,35,25), "F": (180,140,120,90,60,40,35)}
    sources = [evidence["rule_source"], evidence["ranking_source"]]
    total = 0
    for row in rows:
        if not _winner(row, player_id):
            continue
        rank = evidence["rankings"].get(row["loser_id"])
        if row["round"] not in table or rank is None:
            return PointsResult(reason="United Cup: ranking congelato o turno non verificato.", sources=sources)
        index = next(i for i, upper in enumerate((10,20,30,50,100,250,float("inf"))) if rank <= upper)
        if "W/O" in row["score"].upper():
            return PointsResult(reason="United Cup: verificare che altri incontri della sfida siano stati giocati prima di assegnare punti al walkover.", sources=sources)
        total += table[row["round"]][index]
    return PointsResult(total, "United Cup: tabella 4.03 K e ranking congelato al 29 dicembre 2025.", total, 0, sources)


def _entry(row, player_id):
    return row.get("winner_entry" if row["winner_id"] == player_id else "loser_entry", "").upper()


def _winner(row, player_id):
    return row["winner_id"] == player_id


def _last(rows):
    return max(rows, key=lambda row: ROUND_ORDER.get(row["round"], -1))


def _rule(sample, edition_metadata, qualifying_only=False):
    level, draw = sample["tourney_level"], str(sample["draw_size"])
    if level == "G" and draw == "128":
        return "G"
    if level == "M" and draw in {"48", "56", "96"}:
        return "M96" if draw == "96" else "M56"
    if level in {"250", "500"} and draw in {"28", "32", "48"}:
        return level + ("48" if draw == "48" else "32")
    verified_qualifying = (qualifying_only and draw in {"16", "24"} and edition_metadata
                           and str(edition_metadata.get("qualifying_draw_size")) == draw
                           and edition_metadata.get("qualifying_source"))
    if level == "C" and (draw in {"28", "32"} or verified_qualifying) and edition_metadata:
        key = "C" + str(edition_metadata["level"])
        if key in TABLES:
            return key
    return None


def _qualifying_bonus(rows, main, rule, player_id, allow_lucky_loser=False, require_ll_label=False, documented_qualifier=False):
    """Restituisce (valore, spiegazione); il valore manca se la prova e' incompleta."""
    entries = ({_entry(row, player_id) for row in main} | ({"Q"} if documented_qualifier else set())) - {""}
    if "LL" in entries and not allow_lucky_loser:
        return None, "Lucky loser: verificare il trattamento dei punti delle qualificazioni."
    if any(row["round"] not in {"Q1", "Q2", "Q3"} for row in rows):
        return None, "Turno anomalo nel file delle qualificazioni."
    last_round = "Q3" if rule == "G" else "Q2"
    if any(row["round"] == "Q3" for row in rows) and rule != "G":
        return None, "Numero di turni di qualificazione non previsto."
    losses = [row for row in rows if not _winner(row, player_id)]
    if len(losses) > 1:
        return None, "Piu' sconfitte nelle qualificazioni della stessa edizione."
    won_qualifying = any(row["round"] == last_round and _winner(row, player_id) for row in rows)
    if main:
        if losses or "LL" in entries:
            if not allow_lucky_loser or require_ll_label and "LL" not in entries:
                return None, "Qualificazioni perse con ingresso nel main draw: verificare lucky loser."
            if "Q" in entries or won_qualifying or not losses:
                return None, "Lucky loser: percorso qualificazioni mancante o incoerente."
            value, explanation = _qualifying_bonus(rows, [], rule, player_id)
            return value, "Lucky loser: punti del turno perso in qualificazione, senza bonus qualificato. " + explanation
        if "Q" in entries or won_qualifying:
            return QUALIFYING[rule][0], "Bonus qualificato aggiunto una sola volta."
        if rows:
            return None, "Percorso di qualificazione incompleto e ingresso non confermato."
        return 0, "Nessun ingresso da qualificazioni rilevato."
    if not rows or not losses:
        return None, "Qualificazioni ancora aperte o risultati del main draw mancanti."
    last = _last(rows)
    if _winner(last, player_id):
        return None, "Esito delle qualificazioni incoerente."
    if last["round"] == "Q1":
        return 0, "Sconfitta al primo turno di qualificazione."
    if not any(row["round"] == "Q1" and _winner(row, player_id) for row in rows):
        return None, "Manca il primo turno di qualificazione: possibile bye o dato assente."
    if rule == "G" and last["round"] == "Q2":
        return QUALIFYING[rule][2], "Sconfitta al secondo turno di qualificazione Slam."
    if last["round"] == last_round:
        return QUALIFYING[rule][1], "Sconfitta nell'ultimo turno di qualificazione."
    return None, "Turno di qualificazione non risolto."


def evaluate_points(matches, player_id, season=2026, editions=None):
    if season not in (2025, 2026):
        return PointsResult(reason="Regole punti di questa stagione ancora da validare.")
    if not matches:
        return PointsResult(reason="Nessun incontro disponibile.")
    rows = [match["raw"] for match in matches]
    if len({row["tourney_id"] for row in rows}) != 1 or any(player_id not in (row["winner_id"], row["loser_id"]) for row in rows):
        return PointsResult(reason="Incontri di edizioni o giocatori diversi.")
    main = [match["raw"] for match in matches if match["stage"] == "main"]
    qualifying = [match["raw"] for match in matches if match["stage"] == "qualifying"]
    sample = (main or qualifying)[0]
    edition_id, category = sample["tourney_id"], sample["tourney_level"]
    if not edition_id.startswith(f"{season}-"):
        return PointsResult(reason="Edizione non appartenente alla stagione richiesta.")
    rules_url = RULES_2025_URL if season == 2025 else RULES_URL
    if category == "D" or edition_id == f"{season}-9210":
        return PointsResult(0, "Competizione a squadre senza punti ATP individuali.", 0, 0, [rules_url])
    no_points = evidence_file("edition-evidence.json").get(edition_id, {}).get("no_ranking_points")
    if no_points and no_points.get("official_records", {}).get(player_id) == 0:
        return PointsResult(0, "Evento senza punti per il ranking ATP: " + no_points["event"] + ".", 0, 0,
                            [no_points["source"], no_points["official_record_source"].format(player_id=player_id.lower())])
    # Il vincitore di un walkover nel main draw avanza per i punti come da Exhibit K
    # (2025: p. 338; 2026). Ritiri prima del proprio match e risultati amministrativi restano da verificare.
    safe_walkovers = [row for row in main if "W/O" in row["score"].upper() and _winner(row, player_id)]
    edition_evidence = evidence_file("edition-evidence.json").get(edition_id, {})
    sanction = edition_evidence.get("disciplinary_defaults", {}).get(player_id)
    if sanction and sanction.get("forfeit_event_points") is True:
        if any(row["loser_id"] == player_id and row["winner_id"] == sanction["opponent_id"] and row["round"] == sanction["round"] and "DEF" in row["score"].upper() for row in main):
            return PointsResult(0, "Default disciplinare documentato: punti dell evento revocati, regola 8.04 M.", 0, 0, [sanction["rule_source"], sanction["source"]])
    withdrawal = edition_evidence.get("medical_withdrawals", {}).get(player_id)
    medical_walkovers = [row for row in rows if "W/O" in row["score"].upper() and not _winner(row, player_id)] if withdrawal else []
    if medical_walkovers and not any(row["score"].strip() and not any(code in row["score"].upper() for code in ("W/O", "DEF", "ABN", "BYE")) for row in rows):
        return PointsResult(reason="Ritiro medico prima di un incontro giocato: verificare punti e percorso.", sources=[rules_url, withdrawal["source"]])
    default_wins = [row for row in main if "DEF" in row["score"].upper() and _winner(row, player_id)
                    and re.search(r"\d+-\d+", row["score"])] if season == 2026 else []
    allowed_special = safe_walkovers + medical_walkovers + default_wins
    if any(not row["score"].strip() or any(code in row["score"].upper() for code in ("W/O", "DEF", "ABN", "BYE"))
           for row in rows if not any(row is safe for safe in allowed_special)):
        return PointsResult(reason="Walkover perso, risultato speciale o non concluso: verifica necessaria.", sources=[rules_url])
    if edition_id == f"{season}-9900":
        if season != 2026:
            return PointsResult(reason="United Cup: ranking congelato e regole dell'edizione da verificare.", sources=[rules_url])
        return _united_cup_2026(main, player_id)
    if category == "F":
        if any(row["round"] not in {"RR", "SF", "F"} for row in main):
            return PointsResult(reason="Turno Finals sconosciuto.", sources=[rules_url])
        total = sum({"RR": 200, "SF": 400, "F": 500}[row["round"]] for row in main if _winner(row, player_id))
        return PointsResult(total, "Punti delle vittorie: RR 200, SF 400, finale 500.", total, 0, [rules_url, FINALS_URL])
    metadata = (challenger_editions() if editions is None else editions).get(edition_id)
    rule = _rule(sample, metadata, qualifying_only=not main)
    if rule is None:
        return PointsResult(reason="Livello dell'edizione Challenger o formato del tabellone non verificato.", sources=[rules_url])
    sources = [rules_url] + ([metadata["source"]] if category == "C" else [])
    if qualifying and metadata and metadata.get("qualifying_source"):
        sources.append(metadata["qualifying_source"])
    if safe_walkovers or default_wins:
        sources.append(WALKOVER_2025_URL if season == 2025 else WALKOVER_URL)
    if medical_walkovers and withdrawal["source"] not in sources:
        sources.append(withdrawal["source"])
    # 2025: regola 9.03 G 3-4; senza etichetta LL nella fonte serve una prova dell'edizione.
    documented_ll = edition_evidence.get("lucky_losers", {}).get(player_id)
    # Ingresso da qualificato documentato dal tabellone ufficiale quando la fonte non riporta "Q".
    documented_q = edition_evidence.get("qualifier_entries", {}).get(player_id)
    bonus, bonus_reason = _qualifying_bonus(qualifying, main, rule, player_id, allow_lucky_loser=True,
                                            require_ll_label=season == 2025 and not documented_ll,
                                            documented_qualifier=bool(documented_q))
    if documented_q and bonus and documented_q["source"] not in sources:
        sources.append(documented_q["source"])
    if documented_ll and bonus is not None and bonus_reason.startswith("Lucky loser"):
        sources += [documented_ll["source"], documented_ll["qualifying_source"]]
    if bonus is None:
        return PointsResult(reason=bonus_reason, sources=sources)
    if not main:
        return PointsResult(bonus, bonus_reason, 0, bonus, sources)
    table = TABLES[rule]
    last = _last(main)
    if last["round"] not in table:
        return PointsResult(reason="Turno del tabellone principale sconosciuto.", qualifying=bonus, sources=sources)
    losses = [row for row in main if not _winner(row, player_id)]
    if len(losses) > 1 or losses and losses[0] is not last:
        return PointsResult(reason="Esiti incoerenti nel tabellone a eliminazione.", qualifying=bonus, sources=sources)
    if last["round"] == "F" and _winner(last, player_id):
        base, reason = table["W"], "Punti del titolo."
    elif not losses:
        return PointsResult(reason="Tabellone principale ancora aperto o eliminazione mancante.", qualifying=bonus, sources=sources)
    else:
        points_round, reason = last["round"], "Punti del turno di eliminazione."
        if len(main) == 1:
            draw = int(sample["draw_size"])
            bracket = 1 << (draw - 1).bit_length()
            first_round = "R" + str(bracket)
            second_round = "R" + str(bracket // 2)
            documented_bye = player_id in edition_evidence.get("confirmed_byes", {})
            if points_round == second_round and (bracket > draw or documented_bye):
                seed = _seed_number(last.get("loser_seed", ""))
                bye_confirmed = seed is not None and 1 <= seed <= bracket - draw
                if not bye_confirmed:
                    verified = edition_evidence.get("confirmed_byes", {}).get(player_id)
                    if verified:
                        seed = verified.get("seed")
                        bye_confirmed = verified.get("confirmed") is True or seed is not None and 1 <= seed <= bracket - draw
                        if verified["source"] not in sources:
                            sources.append(verified["source"])
                if not bye_confirmed:
                    return PointsResult(reason="Possibile bye o turno mancante: verificare il tabellone.", qualifying=bonus, sources=sources)
                points_round, reason = first_round, "Sconfitta al debutto dopo bye: punti del primo turno."
            if _entry(last, player_id) == "WC" and category in {"G", "M"} and points_round == first_round:
                return PointsResult(bonus, "Wild card eliminata al primo turno: zero punti nel main draw.", 0, bonus, sources)
        if points_round not in table:
            return PointsResult(reason="Turno non presente nella tabella punti.", qualifying=bonus, sources=sources)
        base = table[points_round]
    if medical_walkovers:
        reason += " Ritiro medico documentato dopo incontri giocati."
    if default_wins:
        reason += " Vittoria per default ad incontro iniziato."
    if safe_walkovers:
        reason += " Avanzamento per walkover vinto incluso secondo Exhibit K."
    return PointsResult(base + bonus, reason + " " + bonus_reason, base, bonus, sources)


def calculate_points(matches, player_id="Z355", season=2026):
    result = evaluate_points(matches, player_id, season)
    return result.value, result.reason
