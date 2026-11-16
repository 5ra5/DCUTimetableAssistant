"""Tests for the Feature B tools (tools/rooms.py) against a tiny synthetic database. No Redbrick, no Ollama."""
import sqlite3

from backend.app.tools import rooms as rt
from .helpers import DAY, build_db

SLOT = (DAY, "14:00", 60)          # 14:00-15:00 local


def world(tmp_path, monkeypatch):
    """Build the test database and point the tools at it."""
    w = build_db(tmp_path / "test.db")
    monkeypatch.setattr(rt, "_db_path", lambda: tmp_path / "test.db")
    return w


def names(result):
    return [r["room_name"] for r in result["rooms"]]


def first(pref="same_building", slot=SLOT, building="GLA.FT"):
    return rt.find_rooms_in_building(building, *slot, pref)


# ------------------------------------------------------------------ time handling
def test_parse_slot_winter_is_same_as_utc():
    s = rt.parse_slot("2026-11-17", "14:00", 60)
    assert (s["start_utc"], s["end_utc"]) == ("2026-11-17T14:00:00Z", "2026-11-17T15:00:00Z")


def test_parse_slot_summer_converts_dublin_to_utc():
    # Irish Summer Time is UTC+1, so 14:00 local is 13:00Z
    s = rt.parse_slot("2026-07-14", "14:00", 60)
    assert s["start_utc"] == "2026-07-14T13:00:00Z"


def test_parse_slot_rejects_bad_input():
    bad = [("17-11-2026", "14:00", 60), ("2026-11-17", "2pm", 60), ("2026-11-17", "14:00", "abc"),
           ("2026-11-17", "14:00", 5), ("2026-11-17", "14:00", 999),
           ("2026-11-17", "06:00", 60),      # before search hours
           ("2026-11-17", "21:30", 60),      # finishes after search hours
           ("2026-11-17", "23:30", 60)]      # crosses midnight
    for args in bad:
        try:
            rt.parse_slot(*args)
        except rt.SlotError:
            continue
        raise AssertionError(f"should have been rejected: {args}")


# ------------------------------------------------------------------ availability rules
def test_empty_building_returns_covered_rooms_only(tmp_path, monkeypatch):
    world(tmp_path, monkeypatch)
    r = first()
    assert sorted(names(r)) == ["GLA.FT101", "GLA.FT102", "GLA.FT103"]
    assert r["count"] == 3
    # FT199 has no coverage: it must be reported as unchecked, NOT offered as free
    assert r["rooms_checked"] == 3 and r["rooms_without_data"] == 1


def test_overlapping_events_exclude_room(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    add = w["add_event"]
    add("GLA.FT101", "13:00", "14:30")      # overlaps the start
    add("GLA.FT102", "14:30", "16:00")      # overlaps the end
    add("GLA.FT103", "13:00", "16:00")      # swallows the whole slot
    assert first()["count"] == 0


def test_back_to_back_events_do_not_block(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    w["add_event"]("GLA.FT101", "13:00", "14:00")    # ends exactly when the slot starts
    w["add_event"]("GLA.FT102", "15:00", "16:00")    # starts exactly when the slot ends
    assert "GLA.FT101" in names(first()) and "GLA.FT102" in names(first())


def test_event_inside_slot_blocks(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    w["add_event"]("GLA.FT101", "14:15", "14:45")
    assert "GLA.FT101" not in names(first())


def test_other_days_do_not_block(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    w["add_event"]("GLA.FT101", "13:00", "16:00", day="2026-11-18")
    assert "GLA.FT101" in names(first())


def test_event_in_several_rooms_blocks_all_of_them(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    w["add_event"](["GLA.FT101", "GLA.FT102"], "14:00", "15:00")
    assert names(first()) == ["GLA.FT103"]


def test_cancelled_booking_does_not_block_but_others_do(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    w["add_event"]("GLA.FT101", "14:00", "15:00", "WRB-CANCELLED")
    w["add_event"]("GLA.FT102", "14:00", "15:00", "WRB-PROVISIONAL")
    w["add_event"]("GLA.FT103", "14:00", "15:00", "Exam")
    assert names(first()) == ["GLA.FT101"]


def test_event_with_missing_type_still_blocks(tmp_path, monkeypatch):
    # Regression test: `NULL NOT IN (...)` is not true in SQL, which would silently hide this clash.
    w = world(tmp_path, monkeypatch)
    w["add_event"]("GLA.FT101", "14:00", "15:00", None)
    assert "GLA.FT101" not in names(first())


def test_free_until_and_ordering(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    w["add_event"]("GLA.FT101", "15:00", "16:00")    # free until 15:00
    w["add_event"]("GLA.FT102", "17:00", "18:00")    # free until 17:00
    r = first()                                       # FT103 has nothing later
    assert names(r) == ["GLA.FT103", "GLA.FT102", "GLA.FT101"]
    assert [x["free_until"] for x in r["rooms"]] == [None, "17:00", "15:00"]


def test_cap_on_listed_rooms_but_true_count_reported(tmp_path, monkeypatch):
    world(tmp_path, monkeypatch)
    monkeypatch.setattr(rt, "MAX_ROOMS_PER_BUILDING", 2)
    r = first()
    assert len(r["rooms"]) == 2 and r["count"] == 3


# ------------------------------------------------------------------ error handling
def test_errors_are_returned_as_data(tmp_path, monkeypatch):
    world(tmp_path, monkeypatch)
    assert rt.find_rooms_in_building("GLA.ZZ", *SLOT, "same_building") == {"error": "unknown_building"}
    assert first("nonsense")["error"] == "invalid_search_preference"
    assert first(slot=(DAY, "03:00", 60))["error"] == "invalid_time_slot"
    # outside the imported semester: must NOT claim 'no rooms free'
    assert first(slot=("2027-03-01", "14:00", 60)) == {"error": "outside_timetable_data"}
    assert first(slot=("2026-12-20", "14:00", 60)) == {"error": "outside_timetable_data"}


def test_missing_database_is_a_clean_error(tmp_path, monkeypatch):
    monkeypatch.setattr(rt, "_db_path", lambda: tmp_path / "nope.db")
    assert first() == {"error": "database_unavailable"}


def test_connection_is_read_only(tmp_path, monkeypatch):
    world(tmp_path, monkeypatch)
    conn = rt._connect()
    try:
        conn.execute("DELETE FROM buildings")
        raise AssertionError("write should have failed")
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()


def test_supported_buildings_and_range(tmp_path, monkeypatch):
    world(tmp_path, monkeypatch)
    conn = rt._connect()
    codes = [b["code"] for b in rt.list_supported_buildings(conn)]
    assert "GLA.Y" not in codes and "GLA.FT" in codes          # library has no rooms
    assert rt.date_range(conn) == ("2026-09-01", "2026-12-19")
    assert rt.data_as_of(conn) == "2026-11-12"
    conn.close()


# ------------------------------------------------------------------ widening the search
def nearby(pref, slot=SLOT, building="GLA.FT"):
    return rt.find_rooms_nearby(building, *slot, pref)


def block_polaris_except_one(w):
    for room in ("GLA.FT102", "GLA.FT103"):
        w["add_event"](room, "14:00", "15:00")


def test_same_building_never_widens(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    block_polaris_except_one(w)
    r = nearby("same_building")
    assert r["skipped"] == "same_building_only" and r["rooms"] == [] and r["count"] == 0


def test_not_needed_when_enough_rooms(tmp_path, monkeypatch):
    world(tmp_path, monkeypatch)
    assert nearby("more_options")["skipped"] == "not_needed"


def test_closest_buildings_expands_nearest_first_and_stops_when_enough(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    block_polaris_except_one(w)                    # Polaris has 1 free room -> need 1 more
    r = nearby("closest_buildings")
    assert r["preferred_building_count"] == 1
    assert [s["building_code"] for s in r["searched"]] == ["GLA.S"]     # Stokes (52 m) is nearest and is enough
    assert r["stages_used"] == ["nearby"] and r["total_count"] == 3 and not r["exhausted"]
    assert all(x["distance_metres"] == 52 for x in r["rooms"])


def test_closest_buildings_never_passes_the_nearby_limit(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    block_polaris_except_one(w)
    for room in ("GLA.S101", "GLA.S102", "GLA.N101"):     # everything within 300 m of Polaris is busy
        w["add_event"](room, "14:00", "15:00")
    r = nearby("closest_buildings")
    assert [s["building_code"] for s in r["searched"]] == ["GLA.S", "GLA.N"]    # X101 (500 m) is NOT searched
    assert r["total_count"] == 1 and r["exhausted"] is True


def test_more_options_goes_campus_wide_in_distance_order(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    block_polaris_except_one(w)
    for room in ("GLA.S101", "GLA.S102", "GLA.N101"):
        w["add_event"](room, "14:00", "15:00")
    r = nearby("more_options")
    # nearby stage: S, N (nothing free). campus stage: X (500 m, known) before T (no distance recorded)
    assert [(s["building_code"], s["stage"]) for s in r["searched"]] == [
        ("GLA.S", "nearby"), ("GLA.N", "nearby"), ("GLA.X", "campus_wide")]
    assert r["stages_used"] == ["nearby", "campus_wide"] and r["total_count"] == 2


def test_unknown_distance_buildings_come_last_and_have_no_distance(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    block_polaris_except_one(w)
    for room in ("GLA.S101", "GLA.S102", "GLA.N101", "GLA.X101"):
        w["add_event"](room, "14:00", "15:00")
    r = nearby("more_options")
    assert r["searched"][-1]["building_code"] == "GLA.T" and r["searched"][-1]["distance_metres"] is None
    assert r["total_count"] == 2


def test_building_without_proximity_data_flags_it(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    # Larkin has a single room, so it is always short of 2
    r = nearby("closest_buildings", building="GLA.T")
    assert r["no_nearby_data"] is True and r["searched"] == [] and r["exhausted"] is True
    r = nearby("more_options", building="GLA.T")
    assert r["stages_used"] == ["campus_wide"] and r["total_count"] >= 2


def test_preferred_building_is_never_searched_twice(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    block_polaris_except_one(w)
    r = nearby("more_options")
    assert all(s["building_code"] != "GLA.FT" for s in r["searched"])


def test_zero_rooms_anywhere(tmp_path, monkeypatch):
    w = world(tmp_path, monkeypatch)
    for room in ("GLA.FT101", "GLA.FT102", "GLA.FT103", "GLA.S101", "GLA.S102", "GLA.N101", "GLA.X101", "GLA.T01"):
        w["add_event"](room, "14:00", "15:00")
    r = nearby("more_options")
    assert r["total_count"] == 0 and r["exhausted"] is True


def test_tool_makes_no_network_calls(tmp_path, monkeypatch):
    """The brief: use the database, not the API. Any attempt to open a socket during a search fails the test."""
    import socket
    world(tmp_path, monkeypatch)

    def no_network(*a, **k):
        raise AssertionError("Feature B must not use the network")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    assert first()["count"] == 3
    assert nearby("more_options")["skipped"] == "not_needed"