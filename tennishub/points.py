"""Punti ottenuti per edizione, distinti dalla selezione del ranking ATP.

Fonte: Rulebook ATP 2026, 9.03 G, pp. 272-273, ripubblicato da ITF.
Le informazioni mancanti producono un valore sconosciuto, mai uno zero implicito.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

RULES_URL = "https://www.itftennis.com/media/15608/atp-2026-points-table.pdf"
UNITED_URL = "https://www.atptour.com/-/media/0030c0c028734686b55efd45fe463926.pdf"
FINALS_URL = "https://www.nittoatpfinals.com/en/event/points-and-prize-money"
ENGINE_VERSION = "2026.3"
RULES_2025_URL = "https://www.atptour.com/-/media/files/rulebook/2025/2025-rulebook-chapter-9_pif-atp-rankings_10feb.pdf"
WALKOVER_URL = "https://www.atptour.com/-/media/files/rulebook/2026/2026-rulebook-chapter-10_exhibits_27apr26.pdf"
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
    path = Path(__file__).with_name("rules") / "challengers-2026.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _entry(row, player_id):
    return row.get("winner_entry" if row["winner_id"] == player_id else "loser_entry", "").upper()


def _winner(row, player_id):
    return row["winner_id"] == player_id


def _last(rows):
    return max(rows, key=lambda row: ROUND_ORDER.get(row["round"], -1))


def _rule(sample, edition_metadata):
    level, draw = sample["tourney_level"], str(sample["draw_size"])
    if level == "G" and draw == "128":
        return "G"
    if level == "M" and draw in {"48", "56", "96"}:
        return "M96" if draw == "96" else "M56"
    if level in {"250", "500"} and draw in {"28", "32", "48"}:
        return level + ("48" if draw == "48" else "32")
    if level == "C" and draw in {"28", "32"} and edition_metadata:
        key = "C" + str(edition_metadata["level"])
        if key in TABLES:
            return key
    return None


def _qualifying_bonus(rows, main, rule, player_id):
    """Restituisce (valore, spiegazione); il valore manca se la prova e' incompleta."""
    entries = {_entry(row, player_id) for row in main} - {""}
    if "LL" in entries:
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
        if losses:
            return None, "Qualificazioni perse con ingresso nel main draw: verificare lucky loser."
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
    # Il vincitore di un walkover nel main draw avanza per i punti come da Exhibit K.
    # Ritiri prima del proprio match e risultati amministrativi restano da verificare.
    safe_walkovers = [row for row in main if "W/O" in row["score"].upper() and _winner(row, player_id)] if season == 2026 else []
    if any(not row["score"].strip() or any(code in row["score"].upper() for code in ("W/O", "DEF", "ABN", "BYE"))
           for row in rows if not any(row is safe for safe in safe_walkovers)):
        return PointsResult(reason="Walkover perso, risultato speciale o non concluso: verifica necessaria.", sources=[rules_url])
    if edition_id == f"{season}-9900":
        if season != 2026:
            return PointsResult(reason="United Cup: ranking congelato e regole dell'edizione da verificare.", sources=[rules_url])
        # GJ37 e' nella fascia 21-30 sia al 22 sia al 29 dicembre 2025.
        # I documenti ufficiali consultati differiscono sulla data di congelamento;
        # non si applica il ranking del match agli avversari non ancora verificati.
        total = 0
        for row in main:
            if not _winner(row, player_id):
                continue
            if row["loser_id"] != "GJ37" or row["round"] != "RR":
                return PointsResult(reason="United Cup: ranking congelato o turno ancora da verificare.", sources=[UNITED_URL])
            total += 40
        return PointsResult(total, "United Cup: vittorie con fascia avversario verificata.", total, 0, [UNITED_URL])
    if category == "F":
        if any(row["round"] not in {"RR", "SF", "F"} for row in main):
            return PointsResult(reason="Turno Finals sconosciuto.", sources=[rules_url])
        total = sum({"RR": 200, "SF": 400, "F": 500}[row["round"]] for row in main if _winner(row, player_id))
        return PointsResult(total, "Punti delle vittorie: RR 200, SF 400, finale 500.", total, 0, [rules_url, FINALS_URL])
    metadata = (challenger_editions() if editions is None else editions).get(edition_id)
    rule = _rule(sample, metadata)
    if rule is None:
        return PointsResult(reason="Livello dell'edizione Challenger o formato del tabellone non verificato.", sources=[rules_url])
    sources = [rules_url] + ([metadata["source"]] if category == "C" else [])
    if safe_walkovers:
        sources.append(WALKOVER_URL)
    bonus, bonus_reason = _qualifying_bonus(qualifying, main, rule, player_id)
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
            if points_round == second_round and bracket > draw:
                seed = last.get("loser_seed", "")
                if not seed.isdigit() or not 1 <= int(seed) <= bracket - draw:
                    return PointsResult(reason="Possibile bye o turno mancante: verificare il tabellone.", qualifying=bonus, sources=sources)
                points_round, reason = first_round, "Sconfitta al debutto dopo bye: punti del primo turno."
            if _entry(last, player_id) == "WC" and category in {"G", "M"} and points_round == first_round:
                return PointsResult(bonus, "Wild card eliminata al primo turno: zero punti nel main draw.", 0, bonus, sources)
        if points_round not in table:
            return PointsResult(reason="Turno non presente nella tabella punti.", qualifying=bonus, sources=sources)
        base = table[points_round]
    if safe_walkovers:
        reason += " Avanzamento per walkover vinto incluso secondo Exhibit K."
    return PointsResult(base + bonus, reason + " " + bonus_reason, base, bonus, sources)


def calculate_points(matches, player_id="Z355", season=2026):
    result = evaluate_points(matches, player_id, season)
    return result.value, result.reason
