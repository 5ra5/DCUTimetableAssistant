from app.api.weekly_calendar import get_weekly_timetable
import app.api.weekly_calendar as weekly_calendar


#test 1 -> missing start time
def test_missing_start(monkeypatch):
    events = [
        {
            "module_name": "Valid Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "Invalid Lecture",
            "end": "2026-11-02T11:00:00Z"
        }
    ]

    #monkeypatch is creating a response for the API class that 
    #weekly_events = fetch_timetable_events(url, start, end) 
    #makes in the function get_weekly_timetable
    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert len(result["events"]) == 1
    assert result["events"][0]["module_name1"] == "Valid Lecture"
    assert result["skipped_events"] == 1


#test 2 -> missing end time
def test_missing_end(monkeypatch):
    events = [
        {
            "module_name": "Valid Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "Invalid Lecture",
            "start": "2026-11-02T10:00:00Z"
        }
    ]

    #monkeypatch is creating a response for the API class that 
    #weekly_events = fetch_timetable_events(url, start, end) 
    #makes in the function get_weekly_timetable
    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert len(result["events"]) == 1
    assert result["events"][0]["module_name1"] == "Valid Lecture"
    assert result["skipped_events"] == 1


#test 3 -> Invalid timestamp
def test_invalid_timestamp(monkeypatch):
    events = [
        {
            "module_name": "Valid Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "Invalid Lecture",
            "start": "unknown",
            "end": "2026-11-02T11:00:00Z"
        }
    ]

    #monkeypatch is creating a response for the API class that 
    #weekly_events = fetch_timetable_events(url, start, end) 
    #makes in the function get_weekly_timetable
    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert len(result["events"]) == 1
    assert result["events"][0]["module_name1"] == "Valid Lecture"
    assert result["skipped_events"] == 1


#test 4-> end time before or equal to start time
def test_invalid_time_order(monkeypatch):
    events = [
        {
            "module_name": "Valid Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "End Before Start",
            "start": "2026-11-02T12:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "End Equals Start",
            "start": "2026-11-02T11:00:00Z",
            "end": "2026-11-02T11:00:00Z"
        }
    ]

    #monkeypatch is creating a response for the API class that 
    #weekly_events = fetch_timetable_events(url, start, end) 
    #makes in the function get_weekly_timetable
    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert len(result["events"]) == 1
    assert result["events"][0]["module_name1"] == "Valid Lecture"
    assert result["skipped_events"] == 2



#test 5-> all events are invalid
def test_all_events_invalid(monkeypatch):
    events = [
        {
            "module_name": "Invalid Lecture",
            "start": "unknown",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "Invalid Lab",
            "start": "2026-11-02T11:00:00Z"
        }
    ]

    #monkeypatch is creating a response for the API class that 
    #weekly_events = fetch_timetable_events(url, start, end) 
    #makes in the function get_weekly_timetable
    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert result["events"] == []
    assert result["skipped_events"] == 2


#test 6-> all events are valid
def test_all_events_valid(monkeypatch):
    events = [
        {
            "module_name": "Morning Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "Afternoon Lab",
            "start": "2026-11-02T14:00:00Z",
            "end": "2026-11-02T16:00:00Z"
        }
    ]
    
    #monkeypatch is creating a response for the API class that 
    #weekly_events = fetch_timetable_events(url, start, end) 
    #makes in the function get_weekly_timetable
    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert len(result["events"]) == 2
    assert result["events"][0]["module_name1"] == "Morning Lecture"
    assert result["events"][1]["module_name1"] == "Afternoon Lab"
    assert result["skipped_events"] == 0


#test 7-> events must be sorted by start time
def test_events_sorted_by_start(monkeypatch):
    events = [
        {
            "module_name": "Afternoon Lecture",
            "start": "2026-11-02T14:00:00Z",
            "end": "2026-11-02T15:00:00Z"
        },
        {
            "module_name": "Morning Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "module_name": "Midday Lab",
            "start": "2026-11-02T12:00:00Z",
            "end": "2026-11-02T13:00:00Z"
        }
    ]

    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert [event["module_name1"] for event in result["events"]] == [
        "Morning Lecture",
        "Midday Lab",
        "Afternoon Lecture"
    ]
    assert result["skipped_events"] == 0


#test 8-> all seven required fields are extracted correctly
def test_event_fields(monkeypatch):
    events = [
        {
            "module_name": "CSC1202 Prompt Engineering",
            "description": "Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T11:00:00Z",
            "extras": {
                "summary_long": "Prompt Engineering",
                "location": "GLA.CG01",
                "description": "Lecture, On Campus"
            },
            "unnecessary_field": "Should not appear"
        }
    ]

    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert result["events"] == [
        {
            "module_name1": "CSC1202 Prompt Engineering",
            "module_name2": "Prompt Engineering",
            "location": "GLA.CG01",
            "long_description": "Lecture, On Campus",
            "short_description": "Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T11:00:00Z"
        }
    ]
    assert result["skipped_events"] == 0


#test 9-> Empty response from Redbrick
def test_empty_response(monkeypatch):
    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: []
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert result == {
        "events": [],
        "skipped_events": 0
    }


#test 10 -> correct API URL, programme and date range
def test_api_arguments(monkeypatch):
    received = {}

    def fake_fetch(url, start, end):
        received["url"] = url
        received["start"] = start
        received["end"] = end
        return []

    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        fake_fetch
    )

    get_weekly_timetable(
        "my-programme-uuid",
        "2026-11-02T00:00:00Z",
        "2026-11-06T23:59:59Z"
    )

    assert received["url"] == (
        "https://timetable.redbrick.dcu.ie/api/v3/timetable/"
        "category/course/items/my-programme-uuid/events"
    )
    assert received["start"] == "2026-11-02T00:00:00Z"
    assert received["end"] == "2026-11-06T23:59:59Z"


#test 11 -> missing optional information should not reject an event
def test_missing_optional_fields(monkeypatch):
    events = [
        {
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z",
            "extras": None
        }
    ]

    monkeypatch.setattr(
        weekly_calendar,
        "fetch_timetable_events",
        lambda url, start, end: events
    )

    result = get_weekly_timetable("test-uuid", "2026-11-02", "2026-11-06")

    assert result["events"] == [
        {
            "module_name1": None,
            "module_name2": None,
            "location": None,
            "long_description": None,
            "short_description": None,
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        }
    ]
    assert result["skipped_events"] == 0
