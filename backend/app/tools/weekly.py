"""
Agent-facing tools for Feature A (weekly analysis).

Teammate A's analysis functions (tools/featureAtools.py) take a whole list of events. A model cannot supply that,
and the functions have no docstrings, so the model could not use them directly. These thin tools take the two form
values (programme_uuid, week_start), load the week's events ONCE, convert the times to Dublin time, and call A's
functions unchanged. The model's arguments are pinned to the form values, as for every feature.

Events come live from Redbrick for now: the database holds room timetables, not programme timetables
(see docs/feature-A-integration.md). `load_week_events` is the only place to change when that is fixed.
"""
import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from ..sync.redbrick_client import fetch_timetable_events
from . import featureAtools as analysis

log = logging.getLogger(__name__)

REDBRICK_BASE = "https://timetable.redbrick.dcu.ie/api/v3/timetable"
DUBLIN = ZoneInfo("Europe/Dublin")
# the three tools of one request share one Redbrick call; repeats within 5 minutes reuse it
CACHE_SECONDS = 300

_cache: dict = {}
_lock = threading.Lock()


def events_url(programme_uuid: str) -> str:
    return f"{REDBRICK_BASE}/category/course/items/{programme_uuid}/events"


def week_window(week_start: str) -> tuple:
    """Monday 00:00 to Friday 23:59:59 as UTC strings, the same window /api/weeks hands the frontend."""
    friday = date.fromisoformat(week_start) + timedelta(days=4)
    return f"{week_start}T00:00:00Z", f"{friday.isoformat()}T23:59:59Z"


def clean_events(raw_events) -> tuple:
    """Keep only events with a valid start and end (end after start). Returns (events, skipped_count)."""
    usable, skipped = [], 0
    for event in raw_events:
        try:
            start = datetime.fromisoformat(event["start"])
            end = datetime.fromisoformat(event["end"])
            if end <= start:
                skipped += 1
                continue
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        extras = event.get("extras") or {}
        usable.append({
            # e.g. CSC1202[1] Prompt Engineering and LLM-Based Agents
            "module_name1": event.get("module_name"),
            # shorter readable name
            "module_name2": extras.get("summary_long"),
            # the room(s)
            "location": extras.get("location"),
            # e.g. "Lecture, On Campus"
            "long_description": extras.get("description"),
            "short_description": event.get("description"),
            # UTC, e.g. 2026-11-02T16:00:00Z
            "start": event.get("start"),
            "end": event.get("end"),
        })
    usable.sort(key=lambda e: e.get("start"))
    return usable, skipped


def to_dublin(events: list) -> list:
    """Rewrite start/end as Dublin local time (with offset). Redbrick sends UTC, so before the clocks go back on
    25 Oct 2026 a 10:00 class arrives as 09:00Z. A's functions format whatever clock the timestamp carries, so
    converting once here makes every time they print, and the weekday they group by, local."""
    out = []
    for event in events:
        event = dict(event)
        for key in ("start", "end"):
            moment = datetime.fromisoformat(event[key])
            if moment.tzinfo is None:                              # no offset given: Redbrick means UTC
                moment = moment.replace(tzinfo=timezone.utc)
            event[key] = moment.astimezone(DUBLIN).isoformat()
        out.append(event)
    return out


def load_week_events(programme_uuid: str, week_start: str) -> list:
    """The programme's events for that week, cleaned, in Dublin time. Raises requests.RequestException if Redbrick fails."""
    key = (programme_uuid, week_start)
    with _lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
    start, end = week_window(week_start)
    events, skipped = clean_events(fetch_timetable_events(
        events_url(programme_uuid), start, end))
    if skipped:
        log.warning("Skipped %d invalid events for %s, week %s",
                    skipped, programme_uuid, week_start)
    events = to_dublin(events)
    with _lock:
        _cache[key] = (time.monotonic(), events)
    return events


def _events_or_error(programme_uuid: str, week_start: str):
    try:
        return load_week_events(programme_uuid, week_start), None
    except requests.RequestException as e:
        log.warning("Redbrick request failed: %s", e)
        return None, {"error": "timetable_unavailable"}
    except ValueError:
        return None, {"error": "invalid_week"}


# ---------------------------------------------------------------- the tools the model sees
def weekly_daily_breakdown(programme_uuid: str, week_start: str) -> dict:
    """For each weekday, count the classes by type (lecture, lab, tutorial) and give the total scheduled hours and
    the first and last class times (Dublin time).

    Args:
        programme_uuid: Programme id from the form, e.g. 0b5f2026-989f-0035-5e70-b86354e625a8
        week_start: Monday of the week as YYYY-MM-DD, e.g. 2026-11-02
    """
    events, error = _events_or_error(programme_uuid, week_start)
    return error or analysis.get_daily_breakdown(events)


def weekly_class_patterns(programme_uuid: str, week_start: str) -> dict:
    """Find the busiest and lightest days, days without classes, the earliest start and latest finish, and the most
    common class type of the week.

    Args:
        programme_uuid: Programme id from the form, e.g. 0b5f2026-989f-0035-5e70-b86354e625a8
        week_start: Monday of the week as YYYY-MM-DD, e.g. 2026-11-02
    """
    events, error = _events_or_error(programme_uuid, week_start)
    return error or analysis.analyse_class_patterns(events)


def weekly_free_gaps(programme_uuid: str, week_start: str) -> dict:
    """Find the gaps between classes on each weekday and the longest gap of the week.

    Args:
        programme_uuid: Programme id from the form, e.g. 0b5f2026-989f-0035-5e70-b86354e625a8
        week_start: Monday of the week as YYYY-MM-DD, e.g. 2026-11-02
    """
    events, error = _events_or_error(programme_uuid, week_start)
    return error or analysis.analyse_free_gaps(events)
