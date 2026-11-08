
import pytest
import requests

from app.sync.redbrick_client import fetch_timetable_events
import app.sync.redbrick_client as redbrick_client


#test 1 -> correct URL, headers, date parameters and timeout
def test_request_arguments(monkeypatch):
    received = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return []

    def fake_get(url, headers, params, timeout):
        received["url"] = url
        received["headers"] = headers
        received["params"] = params
        received["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(redbrick_client.requests, "get", fake_get)

    fetch_timetable_events(
        "https://example.com/events",
        "2026-11-02T00:00:00Z",
        "2026-11-06T23:59:59Z"
    )

    assert received["url"] == "https://example.com/events"
    assert received["headers"] == {
        "accept": "*/*",
        "media-type": "application/json"
    }
    assert received["params"] == {
        "start": "2026-11-02T00:00:00Z",
        "end": "2026-11-06T23:59:59Z"
    }
    assert received["timeout"] == 15


#test 2 ->successful JSON response is returned unchanged
def test_successful_response(monkeypatch):
    events = [
        {
            "module_name": "Computer Science",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        }
    ]

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return events

    monkeypatch.setattr(
        redbrick_client.requests,
        "get",
        lambda url, headers, params, timeout: FakeResponse()
    )

    result = fetch_timetable_events("test-url", "start", "end")

    assert result == events


#test 3 -> empty API response
def test_empty_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return []

    monkeypatch.setattr(
        redbrick_client.requests,
        "get",
        lambda url, headers, params, timeout: FakeResponse()
    )

    result = fetch_timetable_events("test-url", "start", "end")

    assert result == []


#test 4 -> HTTP error responses are raised
def test_http_error(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            raise requests.exceptions.HTTPError("404 Not Found")

        def json(self):
            return []

    monkeypatch.setattr(
        redbrick_client.requests,
        "get",
        lambda url, headers, params, timeout: FakeResponse()
    )

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_timetable_events("test-url", "start", "end")


#test 5 -> connection errors are raised
def test_connection_error(monkeypatch):
    def fake_get(url, headers, params, timeout):
        raise requests.exceptions.ConnectionError("Cannot connect")

    monkeypatch.setattr(redbrick_client.requests, "get", fake_get)

    with pytest.raises(requests.exceptions.ConnectionError):
        fetch_timetable_events("test-url", "start", "end")


#test 6 -> request timeouts are raised
def test_timeout(monkeypatch):
    def fake_get(url, headers, params, timeout):
        raise requests.exceptions.Timeout("Request timed out")

    monkeypatch.setattr(redbrick_client.requests, "get", fake_get)

    with pytest.raises(requests.exceptions.Timeout):
        fetch_timetable_events("test-url", "start", "end")


#test 7 -> invalid JSON response raises an error
def test_invalid_json(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            raise requests.exceptions.JSONDecodeError(
                "Invalid JSON", "not-json", 0
            )

    monkeypatch.setattr(
        redbrick_client.requests,
        "get",
        lambda url, headers, params, timeout: FakeResponse()
    )

    with pytest.raises(requests.exceptions.JSONDecodeError):
        fetch_timetable_events("test-url", "start", "end")
