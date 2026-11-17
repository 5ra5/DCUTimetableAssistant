"""
Feature B (AI Room Locator): the tools the agent can call, plus the database helpers they share.

WHAT THIS FILE DOES
    Given a building, a date, a start time, a duration and a search preference, it finds teaching rooms
    that have NO recorded timetable event or booking during that time ("potentially available" rooms).

    Two tools are exposed to the agent (see features/features.py for how they are wired together):
        find_rooms_in_building  - step 1+2: rooms in the student's preferred building (always runs first)
        find_rooms_nearby       - step 4+5: nearby buildings, then the rest of campus (only when needed)

WHY THERE ARE NO REDBRICK API CALLS HERE
    The brief asks us to limit API calls and use the database for room event data. The database already holds
    the whole semester snapshot (timetable_events + timetable_event_rooms, 1 Sep - 20 Dec 2026) and a record of
    which rooms were successfully imported (room_sync_coverage). So every search is answered with a few local
    SQLite queries: fast, repeatable, and zero load on Redbrick. The price is that results are only as fresh as
    the last export, which is why every result carries `data_as_of` and the summary says so.

HOW "AVAILABLE" IS DECIDED  (docs/Database_README.md, "Using the database in the application")
    A room is recommended only if BOTH are true:
        1. COVERAGE : room_sync_coverage shows its timetable was imported for the requested period.
                      A room with no coverage is NOT treated as free - we simply have no data for it.
        2. NO CLASH : no event linked to the room overlaps the requested time.
    Even then the room is only "potentially available": it may be locked, or booked outside Redbrick.

TIMES
    Students think in Irish local time; the database stores UTC ("2026-11-17T14:00:00Z"). We convert the
    student's local time to UTC once (parse_slot) and compare UTC strings. All stored timestamps have exactly the
    same 20-character format, so plain string comparison orders them correctly (checked against the seed data).
"""
import datetime as dt
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from zoneinfo import ZoneInfo

from ..config import settings

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------------------------------
# Tunable rules. They live here (not in config.py) so Feature B does not touch shared settings.
# `settings.min_rooms` (default 2, from config.py) is the "at least two rooms" target from the brief.
# --------------------------------------------------------------------------------------------------------------
DUBLIN = ZoneInfo("Europe/Dublin")
UTC = dt.timezone.utc
DB_TIME_FORMAT = settings.db_time_format         # how timetable_events stores start_time / end_time

# ASSUMPTION: we only search within these local hours. The database has no building opening hours, and a room
# with "no events" at 03:00 is not a useful recommendation. Change them here if the team prefers other hours.
SEARCH_DAY_START = dt.time(8, 0)
SEARCH_DAY_END = dt.time(22, 0)
MIN_DURATION_MINUTES = settings.min_room_duration_minutes  # 30
MAX_DURATION_MINUTES = settings.max_room_duration_minutes  # 240

# ASSUMPTION: "nearby" means within this many metres (building_proximity.distance_metres, which are map
# estimates). 300 m is roughly a 4 minute walk. "Closest buildings" never goes further than this;
# "More options" may.
NEARBY_MAX_METRES = settings.max_search_metres  # 200

# We list at most this many rooms per building so the answer stays readable. The TRUE number of free rooms is
# still reported (`count`) and used for the "at least two rooms" rule.
MAX_ROOMS_PER_BUILDING = settings.max_rooms_per_building  # 6

# Event types that do NOT occupy a room. Everything else (lectures, tutorials, exams, active/provisional
# bookings, even "Synchronous (Online, live)" events that are linked to a room) blocks it, because the brief says
# to check ALL relevant events and bookings. Only a cancelled booking is safe to ignore.
NON_BLOCKING_EVENT_TYPES = ("WRB-CANCELLED",)
# Built from the constant above (never from user input), so it is safe to put in SQL text.
_NON_BLOCKING_SQL = ", ".join("'" + t + "'" for t in NON_BLOCKING_EVENT_TYPES)

# What each search preference allows. The Python tools enforce this, so a model that suggests widening the search
# for a "same building" student cannot actually widen it.
PREFERENCES = {
    "same_building": {"label": "Same building only", "nearby": False, "campus": False},
    "closest_buildings": {"label": "Closest buildings", "nearby": True, "campus": False},
    "more_options": {"label": "More options (anywhere on campus)", "nearby": True, "campus": True},
}


# --------------------------------------------------------------------------------------------------------------
# Time handling
# --------------------------------------------------------------------------------------------------------------
class SlotError(ValueError):
    """The requested date/time/duration is not acceptable. The message is safe to show to a student."""


def _utc_text(moment: dt.datetime) -> str:
    """An aware datetime -> the database's UTC text format."""
    return moment.astimezone(UTC).strftime(DB_TIME_FORMAT)


def parse_slot(date_text: str, start_time: str, duration_minutes) -> dict:
    """Turn the student's local date/time/duration into everything the SQL needs. Raises SlotError if invalid.

    Returns e.g. for 2026-11-17, 14:00, 60:
        {"date": "2026-11-17", "start_time": "14:00", "end_time": "15:00", "duration_minutes": 60,
         "start_utc": "2026-11-17T14:00:00Z", "end_utc": "2026-11-17T15:00:00Z",
         "day_end_utc": "2026-11-18T00:00:00Z"}      # day_end_utc = local midnight, used for 'free until'
    In summer, Dublin is UTC+1, so 14:00 local becomes 13:00Z - that is why we convert instead of assuming.
    """
    try:
        day = dt.date.fromisoformat(date_text)
    except (TypeError, ValueError):
        raise SlotError("The date must look like 2026-11-17.") from None
    try:
        start_clock = dt.datetime.strptime(start_time, "%H:%M").time()
    except (TypeError, ValueError):
        raise SlotError("The start time must look like 14:00 (24-hour clock).") from None
    try:
        minutes = int(duration_minutes)
    except (TypeError, ValueError):
        raise SlotError("The duration must be a whole number of minutes.") from None
    if not MIN_DURATION_MINUTES <= minutes <= MAX_DURATION_MINUTES:
        raise SlotError(
            f"The duration must be between {MIN_DURATION_MINUTES} and {MAX_DURATION_MINUTES} minutes.")

    # Attaching the Dublin zone to the *local* wall-clock time is what makes the later UTC conversion correct.
    start_local = dt.datetime.combine(day, start_clock, tzinfo=DUBLIN)
    end_local = start_local + dt.timedelta(minutes=minutes)      # wall-clock arithmetic in Dublin time
    if end_local.date() != day:
        raise SlotError("The booking must finish on the same day it starts.")
    if start_clock < SEARCH_DAY_START or end_local.time() > SEARCH_DAY_END:
        raise SlotError(
            f"Searches must fall between {SEARCH_DAY_START:%H:%M} and {SEARCH_DAY_END:%H:%M}.")

    next_midnight = dt.datetime.combine(day + dt.timedelta(days=1), dt.time(0, 0), tzinfo=DUBLIN)
    return {
        "date": day.isoformat(),
        "start_time": start_local.strftime("%H:%M"),
        "end_time": end_local.strftime("%H:%M"),
        "duration_minutes": minutes,
        "start_utc": _utc_text(start_local),
        "end_utc": _utc_text(end_local),
        "day_end_utc": _utc_text(next_midnight),
    }


def _utc_to_local_hhmm(utc_text: str) -> str:
    """'2026-11-17T16:00:00Z' -> '16:00' in Dublin time (what the student sees)."""
    moment = dt.datetime.strptime(utc_text, DB_TIME_FORMAT).replace(tzinfo=UTC)
    return moment.astimezone(DUBLIN).strftime("%H:%M")


# --------------------------------------------------------------------------------------------------------------
# Database access (read-only)
# --------------------------------------------------------------------------------------------------------------
def _db_path() -> Path:
    """Where the SQLite file is. A function (not a constant) so tests can point it at a temporary database."""
    return Path(settings.db_path)


def _connect() -> sqlite3.Connection:
    """Open the timetable database READ-ONLY. Feature B only ever reads: a bug here can never corrupt the
    shared data that Features A and C also rely on. Raises sqlite3.Error if the file is missing."""
    path = _db_path()
    if not path.is_file():
        raise sqlite3.OperationalError(f"database not found: {path} (run python3 scripts/init_db.py)")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row        # lets us read columns by name
    return conn


def list_supported_buildings(conn: sqlite3.Connection) -> list:
    """Buildings that can actually be searched: they have at least one teaching room whose timetable was
    imported (room_sync_coverage). This is the list the search form offers, and the pool for 'campus-wide'.
    Returns [{"id", "code", "name", "campus", "room_count"}], sorted by name."""
    rows = conn.execute(
        """SELECT b.id, b.building_code AS code, b.building_name AS name, b.campus,
                  COUNT(DISTINCT r.id) AS room_count
           FROM buildings b
           JOIN teaching_rooms r ON r.building_id = b.id
           JOIN room_sync_coverage c ON c.room_id = r.id
           GROUP BY b.id
           ORDER BY b.building_name""").fetchall()
    return [dict(r) for r in rows]


def _get_building(conn: sqlite3.Connection, code: str):
    return conn.execute(
        "SELECT id, building_code AS code, building_name AS name, campus FROM buildings WHERE building_code = ?",
        (code,)).fetchone()


def slot_is_covered(conn: sqlite3.Connection, slot: dict) -> bool:
    """True if at least one imported room timetable covers the WHOLE requested slot.

    room_sync_coverage stores whole dates ('2026-09-01' to '2026-12-20'). We treat period_end as EXCLUSIVE
    (covered up to 00:00 UTC on that date) because we cannot prove the export included events on that final day.
    Being cautious here only means a search on 20 Dec itself is refused as 'no data'."""
    row = conn.execute(
        """SELECT 1 FROM room_sync_coverage
           WHERE period_start || 'T00:00:00Z' <= :start AND period_end || 'T00:00:00Z' >= :end LIMIT 1""",
        {"start": slot["start_utc"], "end": slot["end_utc"]}).fetchone()
    return row is not None


def date_range(conn: sqlite3.Connection):
    """(first_date, last_date) a student may search, as 'YYYY-MM-DD' strings; None if there is no coverage at all.
    last_date is the day BEFORE period_end because period_end is treated as exclusive (see slot_is_covered)."""
    row = conn.execute("SELECT MIN(period_start) AS lo, MAX(period_end) AS hi FROM room_sync_coverage").fetchone()
    if row is None or row["lo"] is None:
        return None
    last = dt.date.fromisoformat(row["hi"]) - dt.timedelta(days=1)
    return row["lo"], last.isoformat()


def data_as_of(conn: sqlite3.Connection):
    """Date of the OLDEST successful room import ('2026-11-12'). The snapshot is only as fresh as its oldest
    room, so we report that one. This is shown to the student because new bookings appear in Redbrick after it."""
    row = conn.execute("SELECT MIN(last_successful_sync) AS t FROM room_sync_coverage").fetchone()
    return row["t"][:10] if row and row["t"] else None


def _neighbours(conn: sqlite3.Connection, building_id: int) -> list:
    """Buildings with a recorded walking distance to `building_id`, nearest first.
    building_proximity stores each pair once, in either order, so we look at both columns."""
    rows = conn.execute(
        """SELECT b.id, b.building_code AS code, b.building_name AS name, p.distance_metres
           FROM building_proximity p
           JOIN buildings b ON b.id = CASE WHEN p.building_a_id = :id THEN p.building_b_id
                                           ELSE p.building_a_id END
           WHERE p.building_a_id = :id OR p.building_b_id = :id
           ORDER BY p.distance_metres, b.building_code""",
        {"id": building_id}).fetchall()
    return [dict(r) for r in rows]


# The heart of the feature: ONE query finds every free room in a building.
#   - rooms must be in the building AND have coverage for the slot (EXISTS ... room_sync_coverage)
#   - NOT EXISTS an overlapping event. Two intervals overlap when each starts before the other ends:
#         event.start < slot.end  AND  event.end > slot.start
#     Strict '<' / '>' mean a class that ENDS exactly when the slot starts (back-to-back) is not a clash.
#   - COALESCE(event_type, '') so an event with a missing type still BLOCKS the room. Without it,
#     `NULL NOT IN (...)` is NULL (not true) and the clash would silently disappear.
#   - next_event: the start of the room's next event later that day, for "free until HH:MM".
_FREE_ROOMS_SQL = f"""
SELECT r.id, r.room_name,
       (SELECT MIN(e2.start_time)
          FROM timetable_event_rooms er2
          JOIN timetable_events e2 ON e2.id = er2.event_id
         WHERE er2.room_id = r.id
           AND e2.start_time >= :end AND e2.start_time < :day_end
           AND COALESCE(e2.event_type, '') NOT IN ({_NON_BLOCKING_SQL})) AS next_event
FROM teaching_rooms r
WHERE r.building_id = :building_id
  AND EXISTS (SELECT 1 FROM room_sync_coverage c
               WHERE c.room_id = r.id
                 AND c.period_start || 'T00:00:00Z' <= :start
                 AND c.period_end   || 'T00:00:00Z' >= :end)
  AND NOT EXISTS (SELECT 1
                    FROM timetable_event_rooms er
                    JOIN timetable_events e ON e.id = er.event_id
                   WHERE er.room_id = r.id
                     AND e.start_time < :end AND e.end_time > :start
                     AND COALESCE(e.event_type, '') NOT IN ({_NON_BLOCKING_SQL}))
"""


def _search_building(conn: sqlite3.Connection, building, slot: dict, distance, stage: str) -> dict:
    """Free rooms in ONE building for the slot. `stage` is 'preferred', 'nearby' or 'campus_wide'.

    Returns {"building_code", "building_name", "distance_metres", "stage", "available_total", "rooms",
             "rooms_checked", "rooms_without_data"} where `rooms` is capped at MAX_ROOMS_PER_BUILDING and
    `available_total` is the real number of free rooms."""
    params = {"building_id": building["id"], "start": slot["start_utc"], "end": slot["end_utc"],
              "day_end": slot["day_end_utc"]}
    free = conn.execute(_FREE_ROOMS_SQL, params).fetchall()

    # Order: rooms that stay free longest first (no later event = best), then by name. Python's sort is stable,
    # so sorting by name first and by "free until" second keeps names alphabetical inside each group.
    free = sorted(free, key=lambda r: r["room_name"])
    free.sort(key=lambda r: r["next_event"] or "9999", reverse=True)

    # Transparency numbers: how many of the building's rooms could we actually check?
    total_rooms = conn.execute(
        "SELECT COUNT(*) FROM teaching_rooms WHERE building_id = ?", (building["id"],)).fetchone()[0]
    checked = conn.execute(
        """SELECT COUNT(*) FROM teaching_rooms r
            WHERE r.building_id = ?
              AND EXISTS (SELECT 1 FROM room_sync_coverage c
                           WHERE c.room_id = r.id
                             AND c.period_start || 'T00:00:00Z' <= ? AND c.period_end || 'T00:00:00Z' >= ?)""",
        (building["id"], slot["start_utc"], slot["end_utc"])).fetchone()[0]

    rooms = [{
        "room_name": r["room_name"],
        "building_code": building["code"],
        "building_name": building["name"],
        "distance_metres": distance,                          # None = the student's own building / unknown
        "free_until": _utc_to_local_hhmm(r["next_event"]) if r["next_event"] else None,
        "stage": stage,
    } for r in free[:MAX_ROOMS_PER_BUILDING]]
    return {"building_code": building["code"], "building_name": building["name"], "distance_metres": distance,
            "stage": stage, "available_total": len(free), "rooms": rooms,
            "rooms_checked": checked, "rooms_without_data": total_rooms - checked}


# --------------------------------------------------------------------------------------------------------------
# Shared input checking for both tools
# --------------------------------------------------------------------------------------------------------------
def _prepare(conn, building_code, date_text, start_time, duration_minutes, search_preference):
    """Validate the form values. Returns (slot, preference_rules, building_row, None) or (None, None, None, error).
    Errors are returned as data ({"error": "..."}), which is how the engine expects tools to report problems."""
    pref = PREFERENCES.get(search_preference)
    if pref is None:
        return None, None, None, {"error": "invalid_search_preference"}
    try:
        slot = parse_slot(date_text, start_time, duration_minutes)
    except SlotError as e:
        return None, None, None, {"error": "invalid_time_slot", "detail": str(e)}
    building = _get_building(conn, building_code)
    if building is None:
        return None, None, None, {"error": "unknown_building"}
    if not slot_is_covered(conn, slot):
        # Never answer "no rooms free" when the truth is "we have no data for that date".
        return None, None, None, {"error": "outside_timetable_data"}
    return slot, pref, building, None


def _tool_wrapper(func, *args):
    """Run a tool body with a database connection and turn database failures into an error result, so a
    missing/locked database gives a clean 'could not complete' answer instead of a crashed request."""
    try:
        with closing(_connect()) as conn:
            return func(conn, *args)
    except sqlite3.Error as e:
        log.warning("Room search database error: %s", e)
        return {"error": "database_unavailable"}


# --------------------------------------------------------------------------------------------------------------
# AGENT TOOL 1: the student's own building
# --------------------------------------------------------------------------------------------------------------
def _in_building(conn, building_code, date_text, start_time, duration_minutes, search_preference) -> dict:
    slot, pref, building, error = _prepare(
        conn, building_code, date_text, start_time, duration_minutes, search_preference)
    if error:
        return error
    found = _search_building(conn, building, slot, None, "preferred")
    return {
        "building_code": building["code"],
        "building_name": building["name"],
        "date": slot["date"],
        "start_time": slot["start_time"],
        "end_time": slot["end_time"],
        "duration_minutes": slot["duration_minutes"],
        "search_preference": search_preference,
        # The Branch rule in features.py only receives THIS dict, so the facts it needs are put in here:
        "count": found["available_total"],               # real number of free rooms (not capped)
        "can_expand": bool(pref["nearby"]),              # does the student's preference allow a wider search?
        "rooms": found["rooms"],                         # up to MAX_ROOMS_PER_BUILDING, best first
        "rooms_checked": found["rooms_checked"],         # rooms in the building we had timetable data for
        "rooms_without_data": found["rooms_without_data"],
        "data_as_of": data_as_of(conn),
    }


def find_rooms_in_building(building_code: str, date: str, start_time: str, duration_minutes: int,
                           search_preference: str) -> dict:
    """Find teaching rooms in ONE building that have no timetable event or booking during the requested time.
    Always call this first, for the building the student asked for.

    Args:
        building_code: Building code, e.g. GLA.FT.
        date: Date as YYYY-MM-DD, e.g. 2026-11-17.
        start_time: Start time as HH:MM on the 24-hour clock, Dublin time, e.g. 14:00.
        duration_minutes: How long the room is needed, in minutes, e.g. 60.
        search_preference: One of same_building, closest_buildings or more_options.
    """
    return _tool_wrapper(_in_building, building_code, date, start_time, duration_minutes, search_preference)


# --------------------------------------------------------------------------------------------------------------
# AGENT TOOL 2: widen the search (nearby buildings first, then the rest of campus)
# --------------------------------------------------------------------------------------------------------------
def _nearby(conn, building_code, date_text, start_time, duration_minutes, search_preference) -> dict:
    slot, pref, building, error = _prepare(
        conn, building_code, date_text, start_time, duration_minutes, search_preference)
    if error:
        return error

    # The engine runs this tool with only the form values (it cannot pass in tool 1's result), so we re-count the
    # preferred building here. That is one cheap local query - no API call - and keeps the tool self-contained.
    preferred = _search_building(conn, building, slot, None, "preferred")
    total = preferred["available_total"]
    minimum = settings.min_rooms

    result = {
        "building_code": building["code"], "building_name": building["name"],
        "date": slot["date"], "start_time": slot["start_time"], "end_time": slot["end_time"],
        "search_preference": search_preference,
        "rooms": [], "count": 0,                       # rooms found by THIS tool (extra to the preferred building)
        "preferred_building_count": total, "total_count": total,
        "searched": [],                                # every building looked at, with how many rooms it gave
        "stages_used": [], "skipped": None, "exhausted": False, "no_nearby_data": False,
    }

    # Guard rails. The engine lets a model suggestion trigger this tool even when Python's rule says no, so the
    # tool itself refuses to widen the search when that would break the student's preference or is pointless.
    if not pref["nearby"]:
        result["skipped"] = "same_building_only"
        return result
    if total >= minimum:
        result["skipped"] = "not_needed"
        return result

    supported = {b["id"]: b for b in list_supported_buildings(conn)}   # only buildings we hold timetable data for
    supported.pop(building["id"], None)                                # the preferred building is already done
    neighbours = [n for n in _neighbours(conn, building["id"]) if n["id"] in supported]
    close = [n for n in neighbours if n["distance_metres"] <= NEARBY_MAX_METRES]
    result["no_nearby_data"] = not close

    def visit(candidate, distance, stage):
        """Search one more building and fold its rooms into the result. Returns the running total."""
        found = _search_building(conn, candidate, slot, distance, stage)
        result["rooms"].extend(found["rooms"])
        result["count"] += found["available_total"]
        result["searched"].append({
            "building_code": found["building_code"], "building_name": found["building_name"],
            "distance_metres": distance, "stage": stage, "rooms_found": found["available_total"]})
        if stage not in result["stages_used"]:
            result["stages_used"].append(stage)
        return total + result["count"]

    # Stage 1 - nearby buildings, nearest first. Stop as soon as we have enough ("stops when enough are found").
    for n in close:
        if total + result["count"] >= minimum:
            break
        visit(n, n["distance_metres"], "nearby")

    # Stage 2 - the rest of campus, only if the student chose "More options" and we are still short.
    if total + result["count"] < minimum and pref["campus"]:
        searched_ids = {n["id"] for n in close}
        # Known-distance buildings beyond the nearby limit come first (nearest first); buildings with no
        # recorded distance come last, in name order. We never invent a distance for them.
        far = [n for n in neighbours if n["id"] not in searched_ids]
        unknown = sorted((b for i, b in supported.items() if i not in {n["id"] for n in neighbours}),
                         key=lambda b: b["name"])
        for candidate, distance in [(n, n["distance_metres"]) for n in far] + [(b, None) for b in unknown]:
            if total + result["count"] >= minimum:
                break
            visit(candidate, distance, "campus_wide")

    result["total_count"] = total + result["count"]
    result["exhausted"] = result["total_count"] < minimum    # searched everything permitted and still short
    return result


def find_rooms_nearby(building_code: str, date: str, start_time: str, duration_minutes: int,
                      search_preference: str) -> dict:
    """Widen the room search to nearby buildings, and then other buildings on campus if the student allows it.
    Only needed when find_rooms_in_building found fewer than two rooms.

    Args:
        building_code: The student's preferred building code, e.g. GLA.FT.
        date: Date as YYYY-MM-DD, e.g. 2026-11-17.
        start_time: Start time as HH:MM on the 24-hour clock, Dublin time, e.g. 14:00.
        duration_minutes: How long the room is needed, in minutes, e.g. 60.
        search_preference: One of same_building, closest_buildings or more_options.
    """
    return _tool_wrapper(_nearby, building_code, date, start_time, duration_minutes, search_preference)