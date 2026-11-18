# Lecturer Endpoints

Feature C provides lecturer search and schedule lookup through the FastAPI application. The API routes are mounted at `/api/lecturers`.

These endpoints accept JSON request bodies. They have no URL query parameters.

## Search lecturers

**Method:** `POST`

**Path:** `/api/lecturers/search`

**Request body**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `lecturer_name` | string | Yes | Lecturer name or Redbrick identifier to search for. |

The search is case-insensitive and matches both the Redbrick identifier and mapped staff full name. The result may contain one lecturer or a list of candidates.

**Request**

```json
{
  "lecturer_name": "McKenna"
}
```

**Response**

```json
{
  "status": "ok",
  "summary": "Found exact matching lecturer: McKenna J",
  "ai_note": null,
  "facts": {
    "search_lecturer": {
      "status": "success",
      "data": {
        "id": 21,
        "redbrick_identifier": "McKenna J",
        "full_name": "John McKenna",
        "modules": "Advanced Programming, Problem-solving,Creativity & Critical Thinking"
      }
    }
  },
  "trace": {
    "llm_ok": true,
    "tool_sources": {
      "search_lecturer": "model"
    },
    "decision": null,
    "errors": [],
    "timings": {
      "tool_turn": 0.01
    },
    "tool_turns": 1,
    "tool_calls": [
      [
        "search_lecturer"
      ]
    ],
    "seconds": 0.02
  },
  "options": null
}
```

## Check lecturer schedule

**Method:** `POST`

**Path:** `/api/lecturers/schedule`

**Request body**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `lecturer_name` | string | Yes | Numeric lecturer database ID returned by the search result. |
| `date` | string | Yes | Schedule date in `YYYY-MM-DD` format. |
| `time` | string | Yes | Schedule time in 24-hour `HH:MM` format. |

The `date` and `time` values are combined into a UTC timetable lookup value. If no class is active at the requested time, the endpoint searches for the next upcoming class for one of the lecturer's registered modules.

**Request**

```json
{
  "lecturer_name": "21",
  "date": "2026-11-25",
  "time": "14:00"
}
```

**Response**

```json
{
  "status": "ok",
  "summary": "Found class: CSC1026[1] Advanced Programming in room GLA.XG14 at 2026-11-25T14:00:00Z.",
  "ai_note": null,
  "facts": {
    "get_lecturer_schedule": {
      "status": "success",
      "data": {
        "room_name": "GLA.XG14",
        "staff_member": "McKenna J",
        "start_time": "2026-11-25T14:00:00Z",
        "end_time": "2026-11-25T17:00:00Z",
        "module_name": "CSC1026[1] Advanced Programming"
      }
    }
  },
  "trace": {
    "llm_ok": true,
    "tool_sources": {
      "get_lecturer_schedule": "model"
    },
    "decision": null,
    "errors": [],
    "timings": {
      "tool_turn": 0.01
    },
    "tool_turns": 1,
    "tool_calls": [
      [
        "get_lecturer_schedule"
      ]
    ],
    "seconds": 0.02
  },
  "options": null
}
```
