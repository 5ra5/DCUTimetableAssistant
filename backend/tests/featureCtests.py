from datetime import datetime, timezone
import importlib
import pytest

class FakeCursor:

    def __init__(self, one_queue=None, all_queue=None):
        self.one_queue = one_queue or []
        self.all_queue = all_queue or []
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((" ".join(query.split()), params))

    def fetchone(self):
        return self.one_queue.pop(0) if self.one_queue else None

    def fetchall(self):
        return self.all_queue.pop(0) if self.all_queue else []
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

class FakeConnections:

    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        pass 

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


@pytest.fixture
def lecturers_module():
    return importlib.import_module("backend.app.tools.featureCtools")

def patch_db(monkeypath, module, cursor):
    monkeypath.setattr(module, "setup_connection", lambda: FakeConnections(cursor))

def test_01_normalisation(monkeypatch, lecturers_module):
    cleaned = lecturers_module.unicode_remover("Jáné Döe")
    assert "Jane" in cleaned and "Doe" in cleaned
    assert  "  " not in cleaned

@pytest.mark.parametrize("badinput", ["", "   ", None])
def test_02_resolve_candidates(monkeypatch, lecturers_module, badinput):
    cursor = FakeCursor()
    patch_db(monkeypatch, lecturers_module, cursor)
    result = lecturers_module.resolve_candidates(badinput)
    assert result["status"] == "error"
    assert cursor.queries == []

def test_03_resolve_candidates_succesS(monkeypatch, lecturers_module):
    cursor = FakeCursor(all_queue=[[{"id": 42, "full_name": "Grace Hopper", "redbrick_identifier": "GH42", "module_codes": "CS101"}]])
    patch_db(monkeypatch, lecturers_module, cursor)
    result = lecturers_module.resolve_candidates("42")
    assert result["status"] == "success"
    assert result["data"]["id"] == 42

def test_04_resolve_candidates_ambiguous(monkeypatch, lecturers_module):
    ambiguous_cursor = FakeCursor(
        all_queue=[
            [
                {"id": 1, "full_name": "John Doe", "redbrick_identifier": "JD1", "module_codes": None},
                {"id": 2, "full_name": "Jane Smith", "redbrick_identifier": "JD2", "module_codes": None},
            ]
        ]
    )
    patch_db(monkeypatch, lecturers_module, ambiguous_cursor)
    ambiguous_result = lecturers_module.resolve_candidates("John")
    assert ambiguous_result["status"] == "ambiguous"
    empty_cursor = FakeCursor(all_queue=[[]])
    patch_db(monkeypatch, lecturers_module, empty_cursor)
    error_result = lecturers_module.resolve_candidates("Nobody")
    assert error_result["status"] == "error"
    
def test_05_search_single_match(monkeypatch, lecturers_module):
    cursor = FakeCursor(all_queue=[[{"id": 1, "redbrick_identifier": "JD123", "full_name": "John Doe", "module_codes": "CS101"}]])
    patch_db(monkeypatch, lecturers_module, cursor)
    result = lecturers_module.search_lecturer("JD123")
    assert result["status"] == "success"
    assert result["data"]["redbrick_identifier"] == "JD123"

def test_06_search_ambiguous(monkeypatch, lecturers_module):
    cursor = FakeCursor(all_queue=[
        [{"id": 1, "redbrick_identifier": "JD123", "full_name": "John Doe", "module_codes": "CS101"},
         {"id": 2, "redbrick_identifier": "JD456", "full_name": "Jane Smith", "module_codes": "CS102"}]
    ])
    patch_db(monkeypatch, lecturers_module, cursor)
    ambiguous_result = lecturers_module.search_lecturer("JD")
    assert ambiguous_result["status"] == "ambiguous"


def test_07_get_lecturer_schedule(monkeypatch, lecturers_module):
    monkeypatch.setattr(
        lecturers_module,
        "resolve_candidates",
        lambda q: {"status": "success", "data": {"id": 1, "redbrick_identifier": "JD123", "full_name": "John Doe", "module_codes": ["CS101"]}},
    )
    cursor = FakeCursor(
        all_queue=[[{"staff_member": "John Doe", "module_name": "CS101", "room_name": "Room A", "start_time": "2026-06-01T10:00:00Z", "end_time": "2026-06-01T11:00:00Z"}]]
    )
    patch_db(monkeypatch, lecturers_module, cursor)
    result = lecturers_module.get_lecturer_schedule("JD123", "2024-06-01", "10:30")
    assert result["status"] == "success"
    assert result["data"]["module_name"] == "CS101"
    assert result["data"]["room_name"] == "Room A"

def test_08_find_next_lecturer(monkeypatch, lecturers_module):
    fixed_now = datetime(2026, 6, 1, 10, 30,tzinfo=timezone.utc)
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)
    monkeypatch.setattr(lecturers_module, "datetime", FixedDateTime)
    monkeypatch.setattr(
        lecturers_module,
        "resolve_candidates",
        lambda lecturer_id: {"status": "success", "data": {"id": 1, "redbrick_identifier": "JD123", "full_name": "John Doe", "module_codes": ["CS101"]}},
    )

    cursor = FakeCursor(
        all_queue=[[{"staff_member": "John Doe", "module_name": "CS101", "room_name": "Room A", "start_time": "2024-06-01T11:00:00Z", "end_time": "2024-06-01T12:00:00Z"}],
        [],
        ]
        
    )

    patch_db(monkeypatch, lecturers_module, cursor)
    result = lecturers_module.find_next_lecturer("JD123")
    assert result["status"] == "success"
    none_result = lecturers_module.find_next_lecturer("JD123", date="2024-06-01", time="12:00")
    assert none_result["status"] == "fail"

