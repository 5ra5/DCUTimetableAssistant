"""
Test helpers for Feature B: builds a tiny, predictable timetable database so tests never depend on the real seed
data (which changes whenever the team re-exports it).

The world (all searches use Tuesday 2026-11-17, Dublin time = UTC in November):

    Building   code     rooms (covered unless noted)
    Polaris    GLA.FT   FT101 FT102 FT103, FT199 (NO coverage)
    Stokes     GLA.S    S101 S102
    Marconi    GLA.N    N101
    Lonsdale   GLA.X    X101                 (500 m from Polaris: beyond the 300 m "nearby" limit)
    Larkin     GLA.T    T01                  (NO proximity rows, like the real GLA.T / GLA.CA)
    Library    GLA.Y    (no rooms at all)

    Distances: FT-S 52 m, FT-N 91 m, S-N 120 m, FT-X 500 m, S-X 400 m, N-X 280 m
"""
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[2] / "app" / "db" / "schema.sql"
DAY = "2026-11-17"


def build_db(path) -> dict:
    """Create the database file at `path` and return {"events": add_event function, "ids": {...}}."""
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text())
    cur = conn.cursor()

    buildings = {}
    for code, name in [("GLA.FT", "Polaris"), ("GLA.S", "Stokes"), ("GLA.N", "Marconi Building"),
                       ("GLA.X", "Lonsdale"), ("GLA.T", "Larkin Lecture Theatre"), ("GLA.Y", "Library")]:
        cur.execute("INSERT INTO buildings (building_code, building_name, campus) VALUES (?,?,'Glasnevin')",
                    (code, name))
        buildings[code] = cur.lastrowid

    rooms = {}
    layout = {"GLA.FT": ["GLA.FT101", "GLA.FT102", "GLA.FT103", "GLA.FT199"], "GLA.S": ["GLA.S101", "GLA.S102"],
              "GLA.N": ["GLA.N101"], "GLA.X": ["GLA.X101"], "GLA.T": ["GLA.T01"]}
    for code, names in layout.items():
        for name in names:
            cur.execute("INSERT INTO teaching_rooms (redbrick_uuid, room_name, building_id) VALUES (?,?,?)",
                        ("uuid-" + name, name, buildings[code]))
            rooms[name] = cur.lastrowid
            if name != "GLA.FT199":     # FT199 was never imported -> no coverage row
                cur.execute("INSERT INTO room_sync_coverage VALUES (?, '2026-09-01', '2026-12-20', "
                            "'2026-11-12T14:00:00+00:00')", (rooms[name],))

    for a, b, metres in [("GLA.FT", "GLA.S", 52), ("GLA.FT", "GLA.N", 91), ("GLA.S", "GLA.N", 120),
                         ("GLA.FT", "GLA.X", 500), ("GLA.S", "GLA.X", 400), ("GLA.N", "GLA.X", 280)]:
        cur.execute("INSERT INTO building_proximity (building_a_id, building_b_id, distance_metres) VALUES (?,?,?)",
                    (buildings[a], buildings[b], metres))
    conn.commit()

    counter = {"n": 0}

    def add_event(room_names, start, end, event_type="Lecture", day=DAY):
        """Add an event using LOCAL HH:MM times (November: Dublin == UTC). `room_names` may list several rooms."""
        counter["n"] += 1
        cur.execute("INSERT INTO timetable_events (redbrick_uuid, event_name, event_type, start_time, end_time) "
                    "VALUES (?,?,?,?,?)",
                    (f"ev-{counter['n']}", "test event", event_type, f"{day}T{start}:00Z", f"{day}T{end}:00Z"))
        event_id = cur.lastrowid            # the id SQLite just gave this event
        for name in ([room_names] if isinstance(room_names, str) else room_names):
            cur.execute("INSERT INTO timetable_event_rooms VALUES (?,?)", (event_id, rooms[name]))
        conn.commit()

    return {"add_event": add_event, "conn": conn, "rooms": rooms, "buildings": buildings}