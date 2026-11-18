"""
Feature B (AI Room Locator) endpoints.

    GET  /api/rooms/options  - what the search form needs: supported buildings, preferences, durations, date range
    POST /api/rooms/search   - run the search; returns the shared AgentResult shape

Rule from api/README.md: check every input BEFORE calling any tool or model.
    422 = bad input (wrong shape, time outside search hours, date outside the imported timetable)
    404 = unknown / unsupported building
    503 = the timetable database could not be opened
"""
import sqlite3
from contextlib import closing

from fastapi import APIRouter, HTTPException

from ..agent.engine import run_agent
from ..schema import AgentResult, RoomSearchRequest
from ..tools import rooms as room_tools
from ..config import settings

router = APIRouter(tags=["rooms"])

# Durations offered on the form. The API itself accepts any 15-240 minutes (see RoomSearchRequest).
MAX_DURATION = settings.max_room_duration_minutes
DURATION_CHOICES = list(range(30, MAX_DURATION + 1, 30)) # Allows for the MAX_DURATION variable to be defined in .env and not a hardcoded value


def _db_error(e: sqlite3.Error):
    # Database problems are the server's fault, not the student's: 503 rather than a crash
    raise HTTPException(status_code=503, detail="The timetable database is not available.") from e


@router.get("/rooms/options")
def room_options():
    # Everything the search form needs, so the frontend never hard-codes building lists
    try:
        with closing(room_tools._connect()) as conn:
            buildings = room_tools.list_supported_buildings(conn)
            dates = room_tools.date_range(conn)
            as_of = room_tools.data_as_of(conn) # Considering removing this
    except sqlite3.Error as e:
        _db_error(e)
    return {
        "buildings": [{"code": b["code"], "name": b["name"], "room_count": b["room_count"]} for b in buildings],
        "search_preferences": [{"value": k, "label": v["label"]} for k, v in room_tools.PREFERENCES.items()],
        "durations_minutes": DURATION_CHOICES,
        "date_min": dates[0] if dates else None,
        "date_max": dates[1] if dates else None,
        "earliest_start": room_tools.SEARCH_DAY_START.strftime("%H:%M"),
        "latest_finish": room_tools.SEARCH_DAY_END.strftime("%H:%M"),
        "data_as_of": as_of, # Considering removing this
    }


@router.post("/rooms/search", response_model=AgentResult)
def search_rooms(request: RoomSearchRequest):
    # Validate BEFORE any tool or model work
    try:
        slot = room_tools.parse_slot(request.date, request.start_time, request.duration_minutes)
    except room_tools.SlotError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    try:
        with closing(room_tools._connect()) as conn:
            supported = {b["code"] for b in room_tools.list_supported_buildings(conn)}
            covered = room_tools.slot_is_covered(conn, slot)
            dates = room_tools.date_range(conn)
    except sqlite3.Error as e:
        _db_error(e)
    if request.building_code not in supported:
        raise HTTPException(status_code=404, detail="Building not found or has no searchable rooms "
                                                    "(see GET /api/rooms/options)")
    if not covered:
        span = f" Available dates: {dates[0]} to {dates[1]}." if dates else ""
        raise HTTPException(status_code=422, detail="No timetable data covers that date." + span)

    # Hand over to the agent
    # PINNED values are trusted form values: whatever arguments the model writes in a tool call, the tools get
    # these. The keys must match the tools' parameter names (tools/rooms.py).
    pinned = {
        "building_code": request.building_code,
        "date": request.date,
        "start_time": request.start_time,
        "duration_minutes": request.duration_minutes,
        "search_preference": request.search_preference,
    }
    # The message is what the model reads. It uses the building CODE, not its name, on purpose: agent/guards.py
    # refuses any text containing words like "extension", and two real buildings are called "... Extension".
    message = (f"Find rooms in building {request.building_code} on {request.date} starting at "
               f"{request.start_time} for {request.duration_minutes} minutes. "
               f"Search preference: {request.search_preference}.")
    return run_agent("feature_b_rooms", message, pinned)