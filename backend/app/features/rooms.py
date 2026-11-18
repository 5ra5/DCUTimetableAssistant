"""
Feature B (AI Room Locator): the text the student reads, built by PYTHON from the tools' results.

Why Python and not the model? A 3B model can mislead (e.g. say a room is "free" or invent a room name). The engine
therefore lets the model choose tools and add a short optional note, but this file writes the real answer from the
facts, so it is always consistent with the database.

`facts` is keyed by tool name:
    facts["find_rooms_in_building"]   always present   (see tools/rooms.py `_in_building`)
    facts["find_rooms_nearby"]        only if the search was widened (see tools/rooms.py `_nearby`)

Wording rules from the brief: always say "potentially available", never claim a room is guaranteed empty,
unlocked or open to students, and explain WHY the search was widened.
"""
import datetime as dt

from ..config import settings

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")

# CONCISENESS DIAL: how many room names are printed per building before "and N more". Lower = shorter summary.
# The full list (with 'free until' times) is always in `facts`, so nothing is lost.
SHOW_ROOMS = 2

def _caveat(total: int) -> str:
    """Never promise that a room is free, empty or accessible."""
    return (
        "This room is not guaranteed to be empty, unlocked or open to students."
        if total == 1
        else "These rooms are not guaranteed to be empty, unlocked or open to students."
    )

# Shown to the model when it is asked whether to widen the search (Decision.system in features.py).
DECISION_SYSTEM = (
    f"You decide the next step of a room search. The student needs at least {settings.min_rooms} rooms. "
    f"If the number of rooms found is {settings.min_rooms} or more, the action is 'finish'. "
    f"A wider search is allowed ONLY if the number of rooms found is below {settings.min_rooms} AND the search "
    "preference allows it. If both are true, the action is 'broaden_search'. Otherwise the action is 'finish'. "
    "State the number of rooms found, then the action.")

# Instruction for the optional one-sentence ai_note (checked by agent/notes.py before it is shown).
NOTE_INSTRUCTION = ("State ONE fact in a single sentence: how many rooms were found. Do not mention room names, "
                    "codes or times. Do not say a room is guaranteed to be free.")


# ---------------------------------------------------------------- small formatting helpers
def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _pretty_date(iso: str) -> str:
    """'2026-11-17' -> 'Tuesday 17 November 2026' (explicit tables, so the result never depends on the OS locale)."""
    d = dt.date.fromisoformat(iso)
    return f"{_WEEKDAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]} {d.year}"


def _short_date(iso: str) -> str:
    """'2026-11-17' -> 'Tue 17 Nov' (used in the summary; _pretty_date gives the long form)."""
    d = dt.date.fromisoformat(iso)
    return f"{_WEEKDAYS[d.weekday()][:3]} {d.day} {_MONTHS[d.month - 1][:3]}"


def _duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    parts = ([_plural(h, "hour")] if h else []) + ([_plural(m, "minute")] if m else [])
    return " ".join(parts)


def _group(rooms: list, available_total: int, show: int = SHOW_ROOMS) -> str:
    """Compact room list for one building, room CODES only: 'GLA.FT113, GLA.FT114 and 8 more'.
    Only the first `show` rooms are named; the full list (with 'free until' times, building names and distances)
    stays in `facts`."""
    named = [r["room_name"] for r in rooms[:show]]
    hidden = available_total - len(named)
    return ", ".join(named) + (f" and {hidden} more" if hidden > 0 else "")


def _expansion(facts: dict):
    """The widened-search result, or None when no widening actually happened (not run, or the tool declined
    because the preference forbids it / enough rooms were already found)."""
    second = facts.get("find_rooms_nearby")
    return second if second and not second.get("skipped") else None


def total_rooms(facts: dict) -> int:
    first, second = facts["find_rooms_in_building"], _expansion(facts)
    return first["count"] + (second["count"] if second else 0)


# ---------------------------------------------------------------- hooks used by FeatureConfig
def rooms_is_empty(facts: dict) -> bool:
    """True -> the response status is 'none' (nothing found)."""
    return total_rooms(facts) == 0


def rooms_note_when(facts: dict) -> bool:
    """Only ask the model for a note when there is something positive to say."""
    return total_rooms(facts) > 0


def rooms_note_must_mention(facts: dict) -> tuple:
    return ("room", "rooms")


def rooms_decision_question(first: dict) -> str:
    """The plain-language question the model answers when asked whether to widen the search."""
    allowed = "yes" if first["can_expand"] else "no"
    return (f"Rooms found: {first['count']}. Minimum needed: {settings.min_rooms}. "
            f"Search preference allows a wider search: {allowed}.")


def rooms_needs_next(first: dict) -> bool:
    """THE RULE (Python has the last word): widen only if we are short AND the student's preference allows it."""
    return first["count"] < settings.min_rooms and first["can_expand"]


# ---------------------------------------------------------------- the summary
def _widening_sentence(first: dict, second: dict, building_code: str) -> str:
    n = first["count"]
    lead = (
        f"Only {_plural(n, 'room')} in {building_code}"
        if n
        else f"No rooms in {building_code}"
    )

    stages = second["stages_used"]

    if not stages:
        tip = "" if second["search_preference"] == "more_options" else " (try 'More options')"
        return f"{lead}, so the search could not be widened{tip}."

    if "nearby" in stages and "campus_wide" in stages:
        where = "nearby buildings, then the rest of campus"
    elif "nearby" in stages:
        where = "nearby buildings"
    else:
        where = "other buildings on campus"

    checked_codes = list(dict.fromkeys(
        hit["building_code"] for hit in second["searched"]
    ))

    checked = (
        f" Buildings checked: {', '.join(checked_codes)}."
        if checked_codes
        else ""
    )

    none_found = ", but none were free" if second["count"] == 0 else ""

    return (
        f"{lead}, so the search was widened to {where}{none_found}."
        + checked
    )


def rooms_summary(facts: dict) -> str:
    """At most THREE short sentences, one per line:
         1. the result: how many rooms, when, which ones
         2. why the search was widened, or what to try next when nothing was found (only if needed)
         3. the caveat
    Full detail (every room, 'free until' times, buildings searched) is in `facts`, not repeated here."""
    first = facts["find_rooms_in_building"]
    second = _expansion(facts)
    building_code = first["building_code"]
    total = total_rooms(facts)
    when = f"{_short_date(first['date'])}, {first['start_time']}-{first['end_time']}"

    # --- sentence 1: the result. "N rooms" stays adjacent so the optional AI note can quote the number safely.
    if total:
        groups = []

        # Rooms found in the student's original building
        if first["count"]:
            original_rooms = _group(first["rooms"], first["count"])
            groups.append(f"{original_rooms} from {first['building_code']}")

        # Combine rooms found in all other buildings
        if second and second["count"]:
            other_rooms = _group(second["rooms"], second["count"])
            groups.append(f"{other_rooms} from other buildings")

        lines = [
            f"{_plural(total, 'room')} potentially available on {when}: "
            + ", ".join(groups) + "."
        ]
    else:
        lines = [f"No potentially available rooms on {when}."]

    # --- sentence 2
    if second:
        lines.append(_widening_sentence(first, second, building_code))
    elif total == 0:
        why = ("no timetable data for its rooms" if first["rooms_checked"] == 0 else "all checked rooms are booked")
        lines.append(f"{building_code}: {why}; try 'Closest buildings' or 'More options'.")
    elif total < settings.min_rooms and not first["can_expand"]:
        lines.append("Try 'Closest buildings' or 'More options' for more rooms.")

    # --- sentence 3: never promise a room is free/empty/open. Only shown when rooms were found.
    if total:
        lines.append(_caveat(total))
    return "\n".join(lines)