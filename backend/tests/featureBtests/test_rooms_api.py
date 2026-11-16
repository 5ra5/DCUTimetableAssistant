"""
Tests for the Feature B endpoints (api/rooms.py), calling the route functions directly with a fake agent.
They check the input rules (404 / 422 / 503) and what gets passed to the agent. Pydantic's own 422s for malformed
JSON (e.g. a bad date format) come from schema.py and are covered by FastAPI itself.
"""
from types import SimpleNamespace as NS

from backend.app.api import rooms as api
from backend.app.tools import rooms as rt
from .helpers import DAY, build_db


def request(**over):
    base = dict(building_code="GLA.FT", date=DAY, start_time="14:00", duration_minutes=60,
                search_preference="closest_buildings")
    return NS(**{**base, **over})


def setup(tmp_path, monkeypatch):
    build_db(tmp_path / "test.db")
    monkeypatch.setattr(rt, "_db_path", lambda: tmp_path / "test.db")
    sent = {}
    monkeypatch.setattr(api, "run_agent", lambda feature, message, pinned: sent.update(
        feature=feature, message=message, pinned=pinned) or "agent-result")
    return sent


def status_of(fn, *args):
    try:
        fn(*args)
    except api.HTTPException as e:
        return e.status_code, e.detail
    return 200, None


def test_options_lists_only_searchable_buildings(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    o = api.room_options()
    codes = [b["code"] for b in o["buildings"]]
    assert "GLA.FT" in codes and "GLA.Y" not in codes             # the library has no teaching rooms
    assert [p["value"] for p in o["search_preferences"]] == ["same_building", "closest_buildings", "more_options"]
    assert (o["date_min"], o["date_max"]) == ("2026-09-01", "2026-12-19")
    assert o["earliest_start"] == "08:00" and o["latest_finish"] == "22:00" and o["data_as_of"] == "2026-11-12"


def test_valid_search_pins_the_form_values_and_calls_the_agent(tmp_path, monkeypatch):
    sent = setup(tmp_path, monkeypatch)
    assert api.search_rooms(request()) == "agent-result"
    assert sent["feature"] == "feature_b_rooms"
    assert sent["pinned"] == {"building_code": "GLA.FT", "date": DAY, "start_time": "14:00",
                              "duration_minutes": 60, "search_preference": "closest_buildings"}
    assert "GLA.FT" in sent["message"]


def test_unknown_or_unsearchable_building_is_404(tmp_path, monkeypatch):
    sent = setup(tmp_path, monkeypatch)
    assert status_of(api.search_rooms, request(building_code="GLA.ZZ"))[0] == 404
    assert status_of(api.search_rooms, request(building_code="GLA.Y"))[0] == 404     # exists, but no rooms
    assert sent == {}                                              # the agent was never called


def test_bad_time_or_date_is_422_before_the_agent_runs(tmp_path, monkeypatch):
    sent = setup(tmp_path, monkeypatch)
    for over in ({"start_time": "05:00"}, {"start_time": "21:30"}, {"start_time": "23:00", "duration_minutes": 120},
                 {"date": "2027-03-01"}, {"date": "2026-12-20"}):
        assert status_of(api.search_rooms, request(**over))[0] == 422, over
    assert sent == {}


def test_date_error_tells_the_student_the_available_range(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    code, detail = status_of(api.search_rooms, request(date="2027-03-01"))
    assert code == 422 and "2026-09-01" in detail and "2026-12-19" in detail


def test_missing_database_is_503(tmp_path, monkeypatch):
    monkeypatch.setattr(rt, "_db_path", lambda: tmp_path / "missing.db")
    assert status_of(api.search_rooms, request())[0] == 503
    assert status_of(api.room_options)[0] == 503