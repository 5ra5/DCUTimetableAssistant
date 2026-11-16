"""
Tests for Feature B through the real agent engine (agent/engine.py), with a FAKE language model.

The fake model lets us test every decision path without Ollama: the model skipping the tool, calling it with wrong
arguments, saying 'finish' when Python's rule says 'widen', suggesting a widening the student's preference forbids,
and writing good or bad notes. The database is the small synthetic one from helpers.py.
"""
from types import SimpleNamespace as NS

from backend.app.agent import client as llm
from backend.app.agent.engine import run_agent
from backend.app.agent.guards import unsupported_reason
from backend.app.tools import rooms as rt
from .helpers import DAY, build_db


def setup(tmp_path, monkeypatch, busy=("GLA.FT102", "GLA.FT103")):
    """Test DB where Polaris has exactly ONE free room at 14:00-15:00 (FT101), so the search must be widened."""
    w = build_db(tmp_path / "test.db")
    monkeypatch.setattr(rt, "_db_path", lambda: tmp_path / "test.db")
    for room in busy:
        w["add_event"](room, "14:00", "15:00")
    return w


def pinned(pref, building="GLA.FT"):
    return {"building_code": building, "date": DAY, "start_time": "14:00", "duration_minutes": 60,
            "search_preference": pref}


def ask(pref, building="GLA.FT"):
    return run_agent("feature_b_rooms", f"Find rooms in building {building}.", pinned(pref, building))


# ---------------------------------------------------------------- fake model
def tool_call(name, **args):
    return NS(function=NS(name=name, arguments=args))


class FakeModel:
    """Scripted stand-in for llm.chat. The engine makes three kinds of call and we tell them apart by arguments."""

    def __init__(self, calls=None, decision="broaden_search", note="3 rooms were found."):
        self.calls, self.decision, self.note = calls or [], decision, note

    def __call__(self, messages, tools=None, fmt=None, num_predict=80):
        if tools:                                   # tool turn: first time call the scripted tools, then stop
            made = [m for m in messages if m["role"] == "tool"]
            return NS(message=NS(tool_calls=None if made else self.calls, content=""))
        if fmt:                                     # branch decision (JSON)
            import json
            return NS(message=NS(content=json.dumps({"reason": "test", "action": self.decision}), tool_calls=None))
        return NS(message=NS(content=self.note, tool_calls=None))      # optional note


def model_down(*a, **k):
    raise ConnectionError("ollama is down")


# ---------------------------------------------------------------- Python carries on without the model
def test_works_with_model_down_and_widens(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", model_down)
    r = ask("closest_buildings")
    assert r.status == "ok" and r.ai_note is None and r.trace["llm_ok"] is False
    assert r.trace["tool_sources"] == {"find_rooms_in_building": "python", "find_rooms_nearby": "python"}
    assert r.facts["find_rooms_in_building"]["count"] == 1
    assert "Potentially available" in r.summary and "expanded to nearby buildings" in r.summary
    assert "Only 1 room was found in Polaris" in r.summary and "GLA.S101" in r.summary
    assert "does not guarantee" in r.summary             # never claims a room is guaranteed free


def test_same_building_does_not_widen(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", model_down)
    r = ask("same_building")
    assert "find_rooms_nearby" not in r.facts and r.status == "ok"
    assert "expanded" not in r.summary


def test_enough_rooms_means_no_widening(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, busy=())
    monkeypatch.setattr(llm, "chat", model_down)
    assert "find_rooms_nearby" not in ask("more_options").facts


def test_no_rooms_gives_status_none_and_a_hint(tmp_path, monkeypatch):
    w = setup(tmp_path, monkeypatch)
    for room in ("GLA.FT101", "GLA.S101", "GLA.S102", "GLA.N101"):
        w["add_event"](room, "14:00", "15:00")
    monkeypatch.setattr(llm, "chat", model_down)
    r = ask("same_building")
    assert r.status == "none" and "No potentially available rooms were found in Polaris" in r.summary
    assert "Closest buildings" in r.summary                       # tells the student how to look further
    r = ask("closest_buildings")
    assert r.status == "none" and "permitted search area" in r.summary


def test_tool_error_becomes_status_none(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", model_down)
    r = ask("same_building", building="GLA.ZZ")
    assert r.status == "none" and "unknown_building" in r.summary


# ---------------------------------------------------------------- the model takes part
def test_pinned_values_beat_wrong_model_arguments(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    wrong = tool_call("find_rooms_in_building", building_code="GLA.X", date="2030-01-01", start_time="03:00",
                      duration_minutes=5, search_preference="more_options")
    monkeypatch.setattr(llm, "chat", FakeModel(calls=[wrong]))
    r = ask("closest_buildings")
    assert r.facts["find_rooms_in_building"]["building_code"] == "GLA.FT"       # the form value won
    assert r.facts["find_rooms_in_building"]["date"] == DAY
    assert r.trace["tool_sources"]["find_rooms_in_building"] == "model"
    assert any(e.startswith("argument_overridden:find_rooms_in_building.building_code") for e in r.trace["errors"])


def test_model_finish_is_overridden_when_rule_says_widen(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", FakeModel(
        calls=[tool_call("find_rooms_in_building", **pinned("closest_buildings"))], decision="finish"))
    r = ask("closest_buildings")
    assert "find_rooms_nearby" in r.facts and r.trace["tool_sources"]["find_rooms_nearby"] == "python"
    assert any(e.startswith("wrong_decision") for e in r.trace["errors"])


def test_model_agreeing_to_widen_is_recorded(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", FakeModel(
        calls=[tool_call("find_rooms_in_building", **pinned("closest_buildings"))], decision="broaden_search"))
    r = ask("closest_buildings")
    assert r.trace["tool_sources"]["find_rooms_nearby"] == "model_decision" and r.trace["decision"]["agreed"]


def test_model_cannot_widen_a_same_building_search(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", FakeModel(
        calls=[tool_call("find_rooms_in_building", **pinned("same_building"))], decision="broaden_search"))
    r = ask("same_building")
    # the engine ran the tool because the model asked, but the TOOL refused to add rooms
    assert r.facts["find_rooms_nearby"]["skipped"] == "same_building_only"
    assert r.facts["find_rooms_nearby"]["count"] == 0
    assert "expanded" not in r.summary and "GLA.S101" not in r.summary


def test_model_skipping_the_required_tool_is_fixed_by_python(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, busy=())
    monkeypatch.setattr(llm, "chat", FakeModel(calls=[]))             # the model calls no tool at all
    r = ask("same_building")
    assert r.facts["find_rooms_in_building"]["count"] == 3
    assert "python_ran:find_rooms_in_building" in r.trace["errors"]


def test_model_calling_the_optional_tool_first_is_ignored(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, busy=())
    monkeypatch.setattr(llm, "chat", FakeModel(calls=[tool_call("find_rooms_nearby", **pinned("more_options"))]))
    r = ask("more_options")
    assert "ignored_tool_call:find_rooms_nearby" in r.trace["errors"]
    assert r.facts["find_rooms_in_building"]["count"] == 3


def test_good_note_is_kept_and_wrong_note_is_rejected(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, busy=())                              # 3 rooms in Polaris
    monkeypatch.setattr(llm, "chat", FakeModel(note="3 rooms were found."))
    assert ask("same_building").ai_note == "3 rooms were found."
    monkeypatch.setattr(llm, "chat", FakeModel(note="7 rooms were found."))
    r = ask("same_building")
    assert r.ai_note is None and r.trace["note_rejected"]["reason"].startswith("unsupported_quantity")
    monkeypatch.setattr(llm, "chat", FakeModel(note="Rooms were found for you for free."))
    assert ask("same_building").trace["note_rejected"]["reason"] == "for_free"


def test_no_note_requested_when_nothing_found(tmp_path, monkeypatch):
    w = setup(tmp_path, monkeypatch)
    for room in ("GLA.FT101",):
        w["add_event"](room, "14:00", "15:00")
    monkeypatch.setattr(llm, "chat", FakeModel(note="3 rooms were found."))
    assert ask("same_building").ai_note is None


# ---------------------------------------------------------------- guard interaction
def test_every_real_building_code_passes_the_guard():
    """agent/guards.py refuses text containing words like 'extension'. Two real buildings contain it in their
    NAME, which is why the API message uses building CODES. This protects that decision."""
    assert unsupported_reason("Find rooms in Henry Grattan Extension") == "extension"     # why we avoid names
    for code in ("GLA.A", "GLA.C", "GLA.CA", "GLA.FT", "GLA.H", "GLA.L", "GLA.N", "GLA.Q", "GLA.S", "GLA.SA",
                 "GLA.T", "GLA.X"):
        message = (f"Find rooms in building {code} on 2026-11-17 starting at 14:00 for 60 minutes. "
                   "Search preference: closest_buildings.")
        assert unsupported_reason(message) is None, code


# ---------------------------------------------------------------- wording of the summary
def test_single_room_uses_singular_grammar_and_hints_at_wider_search(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", model_down)
    s = ask("same_building").summary
    assert "This room has no recorded timetable events" in s and "it is empty, unlocked" in s
    assert "More options" in s                                     # tells the student how to look further


def test_building_with_no_nearby_data_is_explained(tmp_path, monkeypatch):
    w = setup(tmp_path, monkeypatch)
    w["add_event"]("GLA.T01", "14:00", "15:00")                    # Larkin's only room is busy
    monkeypatch.setattr(llm, "chat", model_down)
    s = ask("closest_buildings", building="GLA.T").summary
    assert "no nearby buildings are recorded for it" in s and "Try 'More options'" in s
    s = ask("more_options", building="GLA.T").summary
    assert "expanded to other buildings on campus (distances unknown)" in s


def test_summary_lists_distance_of_nearby_buildings(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(llm, "chat", model_down)
    s = ask("closest_buildings").summary
    assert "Stokes (GLA.S, 52 m away)" in s and "In total, 3 rooms" in s