#!/usr/bin/env python3
"""Create/update data/timetable.db from the committed semester seed CSVs.

Usage:
    python3 scripts/init_db.py
    python3 scripts/init_db.py --demo

No network calls. The --demo option adds one clearly labelled fictional
identity candidate, NOT a new Redbrick lecturer or any timetable events.
"""

import argparse
import csv
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "timetable.db"
SCHEMA_PATH = ROOT / "backend" / "app" / "db" / "schema.sql"
SEED_DIR = ROOT / "data" / "seed"
DIRECTORY_SOURCE = "https://www.dcu.ie/computing/people"
DEMO_SOURCE = "demo://dcu-timetable-assistant/fictional-staff"

FILES = {
    "buildings": ("buildings.csv", ("building_code", "building_name", "campus")),
    "proximity": ("building_proximity.csv", ("building_a_code", "building_b_code", "distance_metres", "distance_source", "last_verified")),
    "programmes": ("programmes.csv", ("redbrick_name", "programme_code", "degree", "year", "redbrick_uuid")),
    "names": ("lecturer_names.csv", ("redbrick_identifier", "full_name", "first_name", "last_name", "verification_status", "verification_note")),
    "rooms": ("teaching_rooms.csv", ("redbrick_uuid", "room_name", "building_code", "last_refreshed")),
    "modules": ("modules.csv", ("redbrick_uuid", "module_code", "module_name")),
    "lecturers": ("lecturers.csv", ("redbrick_identifier", "last_refreshed")),
    "lecturer_modules": ("lecturer_modules.csv", ("redbrick_identifier", "module_uuid")),
    "events": ("timetable_events.csv", ("redbrick_uuid", "event_name", "module_name", "staff_member", "description", "event_type", "start_time", "end_time")),
    "event_rooms": ("timetable_event_rooms.csv", ("event_uuid", "room_uuid")),
    "coverage": ("room_sync_coverage.csv", ("room_uuid", "period_start", "period_end", "last_successful_sync")),
    "demo": ("demo_lecturer_ambiguity.csv", ("redbrick_identifier", "full_name", "first_name", "last_name", "verification_status", "verification_note")),
}


def read_csv(key):
    filename, required = FILES[key]
    path = SEED_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required seed file missing: {path}")
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames or []
        missing = set(required) - set(fields)
        if missing:
            raise ValueError(f"{filename}: missing columns {sorted(missing)}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError(f"{filename}: malformed row (too many fields)")
    return rows


def required(value, description):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"Missing {description}")
    return value


def optional(value):
    value = (value or "").strip()
    return value or None


def check_unique(rows, key, description):
    values = [required(row[key], f"{description}.{key}") for row in rows]
    if len(values) != len(set(values)):
        duplicates = [k for k, n in Counter(values).items() if n > 1]
        raise ValueError(f"Duplicate {description}.{key}: {duplicates[:5]}")


def validate_seeds(data):
    """Fail before editing the DB for missing links or invalid timetable data."""
    for key, column in (
        ("buildings", "building_code"), ("programmes", "redbrick_uuid"),
        ("rooms", "redbrick_uuid"), ("modules", "redbrick_uuid"),
        ("lecturers", "redbrick_identifier"), ("events", "redbrick_uuid"),
    ):
        check_unique(data[key], column, key)

    building_codes = {r["building_code"] for r in data["buildings"]}
    room_uuids = {r["redbrick_uuid"] for r in data["rooms"]}
    module_uuids = {r["redbrick_uuid"] for r in data["modules"]}
    lecturer_ids = {r["redbrick_identifier"] for r in data["lecturers"]}
    event_uuids = {r["redbrick_uuid"] for r in data["events"]}

    for r in data["proximity"]:
        if r["building_a_code"] not in building_codes or r["building_b_code"] not in building_codes:
            raise ValueError(f"Unknown building in proximity pair: {r}")
    for r in data["rooms"]:
        if r["building_code"] and r["building_code"] not in building_codes:
            raise ValueError(f"Unknown building in teaching_rooms.csv: {r}")
    for r in data["lecturer_modules"]:
        if r["redbrick_identifier"] not in lecturer_ids or r["module_uuid"] not in module_uuids:
            raise ValueError(f"Unknown lecturer or module in lecturer_modules.csv: {r}")
    for r in data["event_rooms"]:
        if r["event_uuid"] not in event_uuids or r["room_uuid"] not in room_uuids:
            raise ValueError(f"Unknown event or room in timetable_event_rooms.csv: {r}")
    for r in data["coverage"]:
        if r["room_uuid"] not in room_uuids:
            raise ValueError(f"Unknown room in room_sync_coverage.csv: {r}")
    for r in data["events"]:
        start, end = required(r["start_time"], "event start"), required(r["end_time"], "event end")
        try:
            if datetime.fromisoformat(end.replace("Z", "+00:00")) <= datetime.fromisoformat(start.replace("Z", "+00:00")):
                raise ValueError("End does not follow start")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid event times for {r['redbrick_uuid']}: {exc}") from exc
    for r in data["coverage"]:
        if not (required(r["period_start"], "coverage start") < required(r["period_end"], "coverage end")):
            raise ValueError(f"Invalid coverage period: {r}")
    for key, pairs in (
        ("lecturer_modules", [(r["redbrick_identifier"], r["module_uuid"]) for r in data["lecturer_modules"]]),
        ("event_rooms", [(r["event_uuid"], r["room_uuid"]) for r in data["event_rooms"]]),
        ("coverage", [(r["room_uuid"], r["period_start"], r["period_end"]) for r in data["coverage"]]),
    ):
        if len(pairs) != len(set(pairs)):
            raise ValueError(f"Duplicate relationships in {FILES[key][0]}")

    selected_rooms = {r["redbrick_uuid"] for r in data["rooms"] if r["building_code"]}
    covered_rooms = {r["room_uuid"] for r in data["coverage"]}
    if selected_rooms != covered_rooms:
        raise ValueError(
            f"Coverage mismatch: {len(selected_rooms)} rooms linked to buildings, "
            f"{len(covered_rooms)} covered; "
            f"missing {len(selected_rooms - covered_rooms)}, extra {len(covered_rooms - selected_rooms)}. "
            "Do not initialise an incomplete room-availability snapshot."
        )


def insert_directory_mapping(conn, row, source):
    identifier = required(row["redbrick_identifier"], "lecturer identifier")
    full_name = required(row["full_name"], "staff name")
    conn.execute(
        "INSERT OR IGNORE INTO lecturers(redbrick_identifier) VALUES (?)",
        (identifier,),
    )
    conn.execute(
        """INSERT INTO directory_staff(first_name, last_name, full_name, role, campus, source_url)
           SELECT ?, ?, ?, NULL, NULL, ?
           WHERE NOT EXISTS (
             SELECT 1 FROM directory_staff WHERE full_name = ? AND source_url = ?
           )""",
        (row["first_name"], row["last_name"], full_name, source, full_name, source),
    )
    lecturer_id = conn.execute(
        "SELECT id FROM lecturers WHERE redbrick_identifier = ?", (identifier,)
    ).fetchone()[0]
    staff_id = conn.execute(
        "SELECT id FROM directory_staff WHERE full_name = ? AND source_url = ?",
        (full_name, source),
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO lecturer_identity_mappings
           (lecturer_id, staff_id, verification_status, verification_note)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(staff_id, lecturer_id) DO UPDATE SET
             verification_status = excluded.verification_status,
             verification_note = excluded.verification_note""",
        (lecturer_id, staff_id, row["verification_status"], optional(row["verification_note"])),
    )


def import_data(conn, data, demo=False):
    for row in data["buildings"]:
        conn.execute(
            """INSERT INTO buildings(building_code, building_name, campus)
               VALUES (?, ?, ?)
               ON CONFLICT(building_code) DO UPDATE SET
                 building_name=excluded.building_name, campus=excluded.campus""",
            (row["building_code"], row["building_name"], row["campus"]),
        )
    building_ids = dict(conn.execute("SELECT building_code, id FROM buildings"))

    for row in data["proximity"]:
        conn.execute(
            """INSERT INTO building_proximity
               (building_a_id, building_b_id, distance_metres, distance_source, last_verified)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT DO UPDATE SET
                 distance_metres=excluded.distance_metres,
                 distance_source=excluded.distance_source,
                 last_verified=excluded.last_verified""",
            (building_ids[row["building_a_code"]], building_ids[row["building_b_code"]],
             float(row["distance_metres"]), row["distance_source"], row["last_verified"]),
        )

    for row in data["programmes"]:
        conn.execute(
            """INSERT INTO programmes(redbrick_name, programme_code, degree, year, redbrick_uuid)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(redbrick_uuid) DO UPDATE SET
                 redbrick_name=excluded.redbrick_name,
                 programme_code=excluded.programme_code,
                 degree=excluded.degree, year=excluded.year""",
            (row["redbrick_name"], optional(row["programme_code"]),
             optional(row["degree"]), int(row["year"]) if row["year"].strip() else None,
             row["redbrick_uuid"]),
        )

    for row in data["rooms"]:
        conn.execute(
            """INSERT INTO teaching_rooms(redbrick_uuid, room_name, building_id, last_refreshed)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(redbrick_uuid) DO UPDATE SET
                 room_name=excluded.room_name,
                 building_id=excluded.building_id,
                 last_refreshed=excluded.last_refreshed""",
            (row["redbrick_uuid"], row["room_name"],
             building_ids.get(row["building_code"]) if row["building_code"] else None,
             optional(row["last_refreshed"])),
        )

    for row in data["modules"]:
        conn.execute(
            """INSERT INTO modules(redbrick_uuid, module_code, module_name)
               VALUES (?, ?, ?)
               ON CONFLICT(redbrick_uuid) DO UPDATE SET
                 module_code=excluded.module_code, module_name=excluded.module_name""",
            (row["redbrick_uuid"], optional(row["module_code"]), row["module_name"]),
        )

    for row in data["lecturers"]:
        conn.execute(
            """INSERT INTO lecturers(redbrick_identifier, last_refreshed)
               VALUES (?, ?)
               ON CONFLICT(redbrick_identifier) DO UPDATE SET
                 last_refreshed=excluded.last_refreshed""",
            (row["redbrick_identifier"], optional(row["last_refreshed"])),
        )

    for row in data["names"]:
        insert_directory_mapping(conn, row, DIRECTORY_SOURCE)

    if demo:
        for row in data["demo"]:
            if row["verification_status"] != "demo":
                raise ValueError("Demo lecturer records must use verification_status=demo")
            if row["redbrick_identifier"] not in {r["redbrick_identifier"] for r in data["lecturers"]}:
                raise ValueError("Demo record references unknown Redbrick identifier")
            insert_directory_mapping(conn, row, DEMO_SOURCE)

    lecturer_ids = dict(conn.execute("SELECT redbrick_identifier, id FROM lecturers"))
    module_ids = dict(conn.execute("SELECT redbrick_uuid, id FROM modules"))
    for row in data["lecturer_modules"]:
        conn.execute(
            "INSERT OR IGNORE INTO lecturer_modules(lecturer_id, module_id) VALUES (?, ?)",
            (lecturer_ids[row["redbrick_identifier"]], module_ids[row["module_uuid"]]),
        )

    for row in data["events"]:
        conn.execute(
            """INSERT INTO timetable_events
               (redbrick_uuid, event_name, module_name, staff_member, description,
                event_type, start_time, end_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(redbrick_uuid) DO UPDATE SET
                 event_name=excluded.event_name,
                 module_name=excluded.module_name,
                 staff_member=excluded.staff_member,
                 description=excluded.description,
                 event_type=excluded.event_type,
                 start_time=excluded.start_time, end_time=excluded.end_time""",
            (row["redbrick_uuid"], optional(row["event_name"]),
             optional(row["module_name"]), optional(row["staff_member"]),
             optional(row["description"]), optional(row["event_type"]),
             row["start_time"], row["end_time"]),
        )

    event_ids = dict(conn.execute("SELECT redbrick_uuid, id FROM timetable_events"))
    room_ids = dict(conn.execute("SELECT redbrick_uuid, id FROM teaching_rooms"))
    for row in data["event_rooms"]:
        conn.execute(
            "INSERT OR IGNORE INTO timetable_event_rooms(event_id, room_id) VALUES (?, ?)",
            (event_ids[row["event_uuid"]], room_ids[row["room_uuid"]]),
        )

    for row in data["coverage"]:
        conn.execute(
            """INSERT INTO room_sync_coverage
               (room_id, period_start, period_end, last_successful_sync)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(room_id, period_start, period_end) DO UPDATE SET
                 last_successful_sync=excluded.last_successful_sync""",
            (room_ids[row["room_uuid"]], row["period_start"], row["period_end"],
             row["last_successful_sync"]),
        )


def initialise_database(demo=False):
    print("=== DCU DATABASE INITIALISATION ===")
    print("Mode:", "DEMO (includes fictional identity)" if demo else "NORMAL")
    keys = [k for k in FILES if k != "demo"] + (["demo"] if demo else [])
    data = {k: read_csv(k) for k in keys}
    validate_seeds(data)
    print("Seed CSV validation: passed")
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Missing schema: {SCHEMA_PATH}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        # executescript() commits implicitly. Seed writes below are then one
        # transaction, and roll back on error.
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        try:
            conn.execute("BEGIN")
            import_data(conn, data, demo=demo)
            foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if foreign_key_errors or integrity != "ok":
                raise RuntimeError(
                    f"DB validation failed: integrity={integrity}; FK violations={foreign_key_errors[:5]}"
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        print("\n=== DATABASE COUNTS ===")
        tables = (
            "buildings", "building_proximity", "programmes", "teaching_rooms",
            "modules", "lecturers", "lecturer_modules", "directory_staff",
            "lecturer_identity_mappings", "timetable_events", "timetable_event_rooms",
            "room_sync_coverage",
        )
        for table in tables:
            print(f"{table}: {conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]}")
        print("\nIntegrity check: ok")
        print("Foreign key violations: 0")
        print("Database saved to:", DB_PATH)
        print("Note: unmatched_event_locations.csv is an audit report, not a database table.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Include fictional staff clarification candidate")
    args = parser.parse_args()
    initialise_database(demo=args.demo)
