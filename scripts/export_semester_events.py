#!/usr/bin/env python3
"""Export Redbrick autumn 2026 room timetables to SQLite seed CSVs.

Run from the personal project root:
    python3 scripts/export_semester_events.py --room GLA.C100-B
    python3 scripts/export_semester_events.py --limit 2
    python3 scripts/export_semester_events.py
    python3 scripts/export_semester_events.py --refresh

A successful full run writes:
    data/seed/timetable_events.csv
    data/seed/timetable_event_rooms.csv
    data/seed/room_sync_coverage.csv
    data/seed/unmatched_event_locations.csv

Raw API responses are cached in data/raw/room_events/<room_uuid>.json.
Unmatched locations are preserved in the report, not guessed or silently mapped.
"""

import argparse
import csv
import json
import os
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "database" / "dcu_timetable.db"
SEED_DIR = ROOT / "data" / "seed"
RAW_DIR = ROOT / "data" / "raw" / "room_events"
API_BASE = "https://timetable.redbrick.dcu.ie/api/v3"

# Proposed prototype snapshot dates; confirm with your team.
SEMESTER_START = "2026-09-01"
SEMESTER_END = "2026-12-20"

EVENT_COLUMNS = [
    "redbrick_uuid", "event_name", "module_name", "staff_member",
    "description", "event_type", "start_time", "end_time",
]
RELATIONSHIP_COLUMNS = ["event_uuid", "room_uuid"]
COVERAGE_COLUMNS = [
    "room_uuid", "period_start", "period_end", "last_successful_sync",
]
UNMATCHED_COLUMNS = ["event_uuid", "location_name", "source_room_uuid"]


def get_rooms():
    """Rooms in real buildings; excludes the local TEST building."""
    with sqlite3.connect(SOURCE_DB) as conn:
        return conn.execute(
            """
            SELECT r.redbrick_uuid, r.room_name
            FROM teaching_rooms AS r
            JOIN buildings AS b ON r.building_id = b.id
            WHERE b.building_code <> 'TEST'
              AND r.redbrick_uuid IS NOT NULL
            ORDER BY r.room_name
            """
        ).fetchall()


def get_room_lookup():
    """Map exact and combined-room component names to catalogue UUIDs.

    For example, 'GLA.X157 & X157-B' has aliases 'GLA.X157' and
    'GLA.X157-B'. Exact catalogue names take precedence over aliases.
    """
    with sqlite3.connect(SOURCE_DB) as conn:
        rows = conn.execute(
            """
            SELECT redbrick_uuid, room_name
            FROM teaching_rooms
            WHERE redbrick_uuid IS NOT NULL
            """
        ).fetchall()

    lookup = {room_name: room_uuid for room_uuid, room_name in rows}
    for room_uuid, room_name in rows:
        if " & " not in room_name:
            continue
        first = room_name.split(" & ", 1)[0]
        if "." not in first:
            continue
        campus_prefix = first.split(".", 1)[0] + "."
        for component in room_name.split(" & "):
            component = component.strip()
            if not component:
                continue
            alias = component if "." in component else campus_prefix + component
            lookup.setdefault(alias, room_uuid)
    return lookup


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def cache_path(room_uuid):
    return RAW_DIR / f"{room_uuid}.json"


def fetch_room_events(room_uuid):
    params = urllib.parse.urlencode(
        {"start": SEMESTER_START, "end": SEMESTER_END}
    )
    url = (
        f"{API_BASE}/timetable/category/location/items/"
        f"{urllib.parse.quote(room_uuid, safe='')}/events?{params}"
    )
    request = urllib.request.Request(
        url,
        headers={
            "media-type": "application/json",
            "User-Agent": "DCU-Timetable-Assistant/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        events = json.load(response)
    if not isinstance(events, list):
        raise ValueError("Redbrick returned a response that is not an array")
    return events


def save_raw_events(room_uuid, events, fetched_at):
    """Save a metadata-aware cache atomically after a successful request."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(room_uuid)
    temporary = path.with_suffix(".json.tmp")
    payload = {
        "room_uuid": room_uuid,
        "period_start": SEMESTER_START,
        "period_end": SEMESTER_END,
        "fetched_at": fetched_at,
        "events": events,
    }
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    os.replace(temporary, path)


def load_raw_events(room_uuid):
    """Return (events, fetched_at) or None for missing/incompatible cache."""
    path = cache_path(room_uuid)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        print("  Old cache has no metadata; downloading a fresh copy")
        return None
    if (
        payload.get("room_uuid") != room_uuid
        or payload.get("period_start") != SEMESTER_START
        or payload.get("period_end") != SEMESTER_END
    ):
        print("  Cache has a different room or date range; downloading again")
        return None
    events = payload.get("events")
    fetched_at = payload.get("fetched_at")
    if not isinstance(events, list) or not isinstance(fetched_at, str) or not fetched_at:
        raise ValueError(f"Invalid cached data for {room_uuid}")
    return events, fetched_at


def get_events_for_room(room_uuid, refresh=False):
    if not refresh:
        cached = load_raw_events(room_uuid)
        if cached is not None:
            events, fetched_at = cached
            return events, fetched_at, "cache"

    events = fetch_room_events(room_uuid)
    fetched_at = utc_now()
    save_raw_events(room_uuid, events, fetched_at)
    return events, fetched_at, "api"


def location_to_room_name(location):
    """Convert Redbrick location pieces to e.g. 'GLA.C100-B'."""
    return (
        f"{location.get('campus') or ''}."
        f"{location.get('building') or ''}"
        f"{location.get('floor') or ''}"
        f"{location.get('room') or ''}"
    )


def export_csv(filename, columns, rows):
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    output = SEED_DIR / filename
    temporary = SEED_DIR / f"{filename}.tmp"
    with temporary.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, output)
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Export Redbrick room timetable events to seed CSVs"
    )
    parser.add_argument("--limit", type=int, help="Only process the first N rooms")
    parser.add_argument("--room", help="Process one linked room, e.g. GLA.C100-B")
    parser.add_argument(
        "--refresh", action="store_true", help="Ignore cached data and call Redbrick"
    )
    args = parser.parse_args()

    if args.room and args.limit is not None:
        parser.error("Choose --room or --limit, not both")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if not SOURCE_DB.is_file():
        parser.error(f"Source database not found: {SOURCE_DB}")

    all_rooms = get_rooms()
    if args.room:
        rooms = [(uuid, name) for uuid, name in all_rooms if name == args.room]
        if not rooms:
            parser.error(f"Room not found among linked rooms: {args.room}")
    elif args.limit is not None:
        rooms = all_rooms[:args.limit]
    else:
        rooms = all_rooms

    room_lookup = get_room_lookup()
    events_by_uuid = {}
    event_room_pairs = set()
    coverage_rows = []
    unmatched_locations = Counter()
    unmatched_location_rows = set()
    failures = []
    invalid_events = []

    print(f"Available linked rooms: {len(all_rooms)}")
    print(f"Rooms selected: {len(rooms)}")
    print(f"Semester: {SEMESTER_START} to {SEMESTER_END}")

    for index, (room_uuid, room_name) in enumerate(rooms, start=1):
        print(f"[{index}/{len(rooms)}] Processing {room_name}...")
        try:
            events, fetched_at, source = get_events_for_room(
                room_uuid, refresh=args.refresh
            )
        except Exception as error:
            print(f"  FAILED: {error}")
            failures.append((room_name, str(error)))
            continue

        print(f"  {len(events)} events loaded from {source}")
        for event in events:
            if not isinstance(event, dict):
                invalid_events.append((room_name, "Event is not a JSON object"))
                continue

            event_uuid = event.get("identity")
            start = event.get("start")
            end = event.get("end")
            if not all(isinstance(value, str) and value for value in (event_uuid, start, end)):
                invalid_events.append((room_name, "Missing event identity/start/end"))
                continue

            locations = event.get("locations") or []
            if not isinstance(locations, list) or any(
                not isinstance(location, dict) for location in locations
            ):
                invalid_events.append((room_name, f"Malformed locations in {event_uuid}"))
                continue

            row = {
                "redbrick_uuid": event_uuid,
                "event_name": event.get("name"),
                "module_name": event.get("module_name"),
                "staff_member": event.get("staff_member"),
                "description": event.get("description"),
                "event_type": event.get("event_type"),
                "start_time": start,
                "end_time": end,
            }
            # Same event may occur in multiple requested room responses.
            # Conflicting timestamps for one event UUID need review.
            existing = events_by_uuid.get(event_uuid)
            if existing and (
                existing["start_time"] != start or existing["end_time"] != end
            ):
                invalid_events.append((room_name, f"Conflicting times for {event_uuid}"))
                continue
            events_by_uuid[event_uuid] = row

            # The request itself establishes this source-room association.
            event_room_pairs.add((event_uuid, room_uuid))
            for location in locations:
                name = location_to_room_name(location)
                matched_uuid = room_lookup.get(name)
                if matched_uuid:
                    event_room_pairs.add((event_uuid, matched_uuid))
                else:
                    unmatched_locations[name] += 1
                    unmatched_location_rows.add((event_uuid, name, room_uuid))

        coverage_rows.append(
            {
                "room_uuid": room_uuid,
                "period_start": SEMESTER_START,
                "period_end": SEMESTER_END,
                "last_successful_sync": fetched_at,
            }
        )
        if source == "api":
            time.sleep(0.2)

    # Unmatched locations are reported, not treated as missing requested rooms.
    if failures or invalid_events:
        print("\n=== EXPORT NEEDS REVIEW ===")
        print(f"Failed room requests: {len(failures)}")
        print(f"Invalid events: {len(invalid_events)}")
        print(f"Unmatched location names: {len(unmatched_locations)}")
        for name, error in failures[:10]:
            print(f"  Failed {name}: {error}")
        for name, error in invalid_events[:10]:
            print(f"  Invalid {name}: {error}")
        print("Existing seed CSVs were left unchanged.")
        print("Successful raw JSON caches have been preserved.")
        raise SystemExit(1)

    event_rows = [events_by_uuid[key] for key in sorted(events_by_uuid)]
    relationship_rows = [
        {"event_uuid": event_uuid, "room_uuid": room_uuid}
        for event_uuid, room_uuid in sorted(event_room_pairs)
    ]
    unmatched_rows = [
        {
            "event_uuid": event_uuid,
            "location_name": location_name,
            "source_room_uuid": source_room_uuid,
        }
        for event_uuid, location_name, source_room_uuid
        in sorted(unmatched_location_rows)
    ]

    events_path = export_csv("timetable_events.csv", EVENT_COLUMNS, event_rows)
    links_path = export_csv(
        "timetable_event_rooms.csv", RELATIONSHIP_COLUMNS, relationship_rows
    )
    coverage_path = export_csv(
        "room_sync_coverage.csv", COVERAGE_COLUMNS, coverage_rows
    )
    unmatched_path = export_csv(
        "unmatched_event_locations.csv", UNMATCHED_COLUMNS, unmatched_rows
    )

    print("\n=== EXPORT COMPLETE ===")
    print(f"Unique events: {len(event_rows)}")
    print(f"Event-room relationships: {len(relationship_rows)}")
    print(f"Rooms successfully checked: {len(coverage_rows)}")
    print(f"Failed room requests: {len(failures)}")
    print(f"Invalid events: {len(invalid_events)}")
    print(f"Unique unmatched locations: {len(unmatched_locations)}")
    print(f"Unmatched location references: {len(unmatched_rows)}")
    if unmatched_locations:
        print("Unmatched locations (not available for Feature B recommendations):")
        for name, count in unmatched_locations.most_common():
            print(f"  {name}: {count} occurrence(s)")
    print("\nCSV files created:")
    for path in (events_path, links_path, coverage_path, unmatched_path):
        print(f"  {path}")


if __name__ == "__main__":
    main()
