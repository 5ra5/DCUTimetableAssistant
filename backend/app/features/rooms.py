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

def _caveat(total: int) -> str:
    """Brief rule: never promise the room is free, empty or accessible."""
    these, have, they = ("This room has", "has", "it is") if total == 1 else ("These rooms have", "have", "they are")
    return (f"{these} no recorded timetable events or bookings in that period. That does not guarantee "
            f"{they} empty, unlocked or open to students.")

# Shown to the model when it is asked whether to widen the search (Decision.system in features.py).
DECISION_SYSTEM = (
    f"You decide the next step of a room search. The student needs at least {settings.min_rooms} rooms. "
    f"If the number of rooms found is below {settings.min_rooms} and a wider search is allowed, the action is "
    "broaden_search. In every other case the action is finish. State the number, then the action.")

NOTE_INSTRUCTION = ("State ONE fact in a single sentence: how many rooms were found. Do not mention room names, "
                    "codes or times. Do not say a room is guaranteed to be free.")


# ---------------------------------------------------------------- small formatting helpers
def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _pretty_date(iso: str) -> str:
    """'2026-11-17' -> 'Tuesday 17 November 2026' (explicit tables, so the result never depends on the OS locale)."""
    d = dt.date.fromisoformat(iso)
    return f"{_WEEKDAYS[d.weekday()]} {d.day} {_MONTHS[d.month - 1]} {d.year}"


def _duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    parts = ([_plural(h, "hour")] if h else []) + ([_plural(m, "minute")] if m else [])
    return " ".join(parts)


def _room_list(rooms: list, available_total: int) -> str:
    """'GLA.FT113 (free until 16:00), GLA.FT114 and 3 more rooms'"""
    parts = [r["room_name"] + (f" (free until {r['free_until']})" if r["free_until"] else "") for r in rooms]
    hidden = available_total - len(rooms)
    text = ", ".join(parts)
    return text + (f" and {_plural(hidden, 'more room')}" if hidden > 0 else "")


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
            f"Wider search allowed: {allowed}.")


def rooms_needs_next(first: dict) -> bool:
    """THE RULE (Python has the last word): widen only if we are short AND the student's preference allows it."""
    return first["count"] < settings.min_rooms and first["can_expand"]


# ---------------------------------------------------------------- the summary
def rooms_summary(facts: dict) -> str:
    first = facts["find_rooms_in_building"]
    second = _expansion(facts)
    name, code = first["building_name"], first["building_code"]
    lines = [f"Potentially available rooms on {_pretty_date(first['date'])}, from {first['start_time']} to "
             f"{first['end_time']} ({_duration(first['duration_minutes'])}), starting from {name} ({code})."]

    # 1) the student's own building
    if first["count"]:
        lines.append(f"{name} ({code}): {_plural(first['count'], 'room')}: "
                     f"{_room_list(first['rooms'], first['count'])}.")
    elif first["rooms_checked"] == 0:
        lines.append(f"{name} ({code}): no teaching rooms with timetable data for this period, so none could be checked.")
    else:
        lines.append(f"{name} ({code}): every room checked has a timetable event or booking in this period.")
    if first["rooms_without_data"] and first["rooms_checked"]:
        lines.append(f"{_plural(first['rooms_without_data'], 'room')} in {name} could not be checked "
                     "because there is no timetable data for them.")

    # 2) why and how the search was widened
    if second:
        found_here = first["count"]
        short = (f"Only {_plural(found_here, 'room')} {'was' if found_here == 1 else 'were'} found in {name}"
                 if found_here else f"No rooms were found in {name}")
        stages = second["stages_used"]
        campus_allowed = second["search_preference"] == "more_options"
        if second["no_nearby_data"] and "campus_wide" in stages:
            # e.g. GLA.CA / GLA.T: the proximity table has no rows for them, so we cannot rank by distance.
            lines.append(f"{short}, and no nearby buildings are recorded for it, so the search was expanded to "
                         "other buildings on campus (distances unknown).")
        elif second["no_nearby_data"]:
            lines.append(f"{short}, and no nearby buildings are recorded for it, so the search could not be "
                         "widened." + ("" if campus_allowed else " Try 'More options' to search the rest of campus."))
        else:
            where = ("nearby buildings and then other buildings on campus" if "campus_wide" in stages
                     else "nearby buildings")
            lines.append(f"{short}, so the search was expanded to {where}.")
        for hit in (s for s in second["searched"] if s["rooms_found"]):
            rooms = [r for r in second["rooms"] if r["building_code"] == hit["building_code"]]
            dist = f", {hit['distance_metres']:g} m away" if hit["distance_metres"] is not None else ""
            lines.append(f"{hit['building_name']} ({hit['building_code']}{dist}): "
                         f"{_plural(hit['rooms_found'], 'room')}: {_room_list(rooms, hit['rooms_found'])}.")

    # 3) the overall result
    total = total_rooms(facts)
    if total:
        if second and second["count"]:
            lines.append(f"In total, {_plural(total, 'room')} with no recorded timetable conflict.")
        lines.append(_caveat(total))
        if total < settings.min_rooms and not first["can_expand"]:
            lines.append("You could try the 'Closest buildings' or 'More options' search to find more rooms.")
    else:
        lines.append(f"No potentially available rooms were found in {'the permitted search area' if second else name}.")
        if not first["can_expand"]:
            lines.append("You could try the 'Closest buildings' or 'More options' search to look further.")

    if first.get("data_as_of"):
        d = dt.date.fromisoformat(first["data_as_of"])
        lines.append(f"Timetable data last updated {d.day} {_MONTHS[d.month - 1]} {d.year}; "
                     "bookings made since then are not included.")
    return "\n".join(lines)