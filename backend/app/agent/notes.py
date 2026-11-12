"""Checks for the optional model-written 'ai_note'.

The summary comes from a Python template and is always correct. The note is a bonus sentence from a 3B
model, so we only show it if it passes these checks. The checks catch the mistakes we actually saw; they
cannot prove every sentence true, which is why 'facts' and 'summary' are the real answer.
"""
import json
import re
from typing import Optional

MAX_LEN = 300

# FTG11, CSC1042, COMSCI3  /  GLA.FT
_CODE = re.compile(
    r"\b(?:[A-Z]{2,8}\d{1,4}[A-Z]{0,2}|[A-Z]{2,4}\.[A-Z]{1,3})\b")
_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
# "building FTG11" or "FTG11 building": a room or module code called a building
_BUILDING_CODE = re.compile(
    r"\bbuilding\s+[A-Z]{2,8}\d|\b[A-Z]{2,8}\d+[A-Z]*\s+(?:is\s+(?:a|an|the)\s+)?building\b", re.IGNORECASE)
_FREE = re.compile(r"for free|free of charge", re.IGNORECASE)
_QUANTITY = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?|rooms?|lectures?|labs?|classes|class|days?|buildings?)\b", re.IGNORECASE
)
_UNIT_ALIASES = {"hr": "hour", "min": "minute", "classes": "class"}


def _time(m) -> str:
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def _quantities(text: str) -> set:
    """(number, unit) pairs, normalised so '2 Hours' and '2.0 hour' match."""
    pairs = set()
    for number, unit in _QUANTITY.findall(text):
        unit = unit.lower()
        unit = unit if unit in ("class", "classes") else unit.rstrip(
            "s")   # never strip the s from "class"
        pairs.add((float(number), _UNIT_ALIASES.get(unit, unit)))
    return pairs


def check_note(note: str, summary: str, facts: dict, must_mention: tuple = ()) -> Optional[str]:
    """Return None if the note is acceptable, otherwise a short reason why it was rejected."""
    if not note or not note.strip():
        return "empty"
    if len(note) > MAX_LEN:
        return "too_long"
    if "\n" in note.strip():
        return "multi_line"

    known = json.dumps(facts, default=str) + " " + summary
    for code in _CODE.findall(note):
        if code not in known:
            return f"unknown_code:{code}"
    known_times = {_time(m) for m in _TIME.finditer(known)}
    for m in _TIME.finditer(note):
        if _time(m) not in known_times:
            return f"unknown_time:{m.group(0)}"

    if _BUILDING_CODE.search(note):
        return "room_called_building"
    if _FREE.search(note):
        return "for_free"

    for number, unit in _quantities(note) - _quantities(summary):
        return f"unsupported_quantity:{number:g} {unit}"

    if must_mention and not any(w.lower() in note.lower() for w in must_mention):
        return "missing_mention"
    return None
