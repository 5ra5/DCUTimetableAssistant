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
# "room GLA.FT" or "GLA.FT room": a dotted code is always a BUILDING (rooms are like FTG11)
_ROOM_BUILDING = re.compile(
    r"\broom\s+[A-Z]{2,4}\.[A-Z]|\b[A-Z]{2,4}\.[A-Z]{1,3}\s+room\b", re.IGNORECASE)
_FREE = re.compile(r"for free|free of charge", re.IGNORECASE)
_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
_NUMBER_WORDS = {w: i for i, w in enumerate(_WORDS)} | {"no": 0}
_QUANTITY = re.compile(
    r"\b(\d+(?:\.\d+)?|" + "|".join(_NUMBER_WORDS) +
    r")\s*(hours?|hrs?|minutes?|mins?|rooms?|lectures?|labs?|classes|class|days?|buildings?)\b", re.IGNORECASE
)
_UNIT_ALIASES = {"hr": "hour", "min": "minute", "classes": "class"}


def _time(m) -> str:
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def _quantities(text: str) -> set:
    """(number, unit) pairs, normalised so '2 Hours', '2.0 hour' and 'two hours' match."""
    pairs = set()
    for number, unit in _QUANTITY.findall(text):
        unit = unit.lower()
        unit = unit if unit in ("class", "classes") else unit.rstrip(
            "s")   # never strip the s from "class"
        value = _NUMBER_WORDS.get(number.lower())
        value = float(number) if value is None else float(value)
        pairs.add((value, _UNIT_ALIASES.get(unit, unit)))
    return pairs


def _mentions(note: str, word: str) -> bool:
    """Whole-token match, so the figure "20" is not found inside "200" (but "expand" still matches "expanded")."""
    return re.search(r"(?<!\w)" + re.escape(word) + r"(?!\d)", note, re.IGNORECASE) is not None


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
    if _ROOM_BUILDING.search(note):
        return "building_called_room"
    if _FREE.search(note):
        return "for_free"

    for number, unit in _quantities(note) - _quantities(summary):
        return f"unsupported_quantity:{number:g} {unit}"

    if must_mention and not any(_mentions(note, w) for w in must_mention):
        return "missing_mention"
    return None
