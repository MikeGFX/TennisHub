"""Distinzione tra incontri giocati e avanzamenti senza incontro."""

import re


def match_was_played(score):
    value = (score or "").strip().upper()
    if not value or any(code in value for code in ("W/O", "BYE", "ABN")):
        return False
    if "DEF" in value and not re.search(r"\d+-\d+", value):
        return False
    return True
