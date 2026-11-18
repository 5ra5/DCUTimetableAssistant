# Feature B: AI Room Locator

The Room Locator finds teaching rooms with no recorded timetable event or booking during a requested time. Results
are **potentially available**, not guaranteed to be empty, unlocked, or open to students. It reads the local
`data/timetable.db`; searches do not call Redbrick.

## API for the frontend

The app serves these routes under `/api`. The frontend should load the options at startup rather than hard-code
building codes, date limits, preference labels, durations, or search hours.

### `GET /api/rooms/options`

Returns the data needed to populate the search form:

```json
{
  "buildings": [
    { "code": "GLA.FT", "name": "Polaris", "room_count": 12 }
  ],
  "search_preferences": [
    { "value": "same_building", "label": "Same building only" },
    { "value": "closest_buildings", "label": "Closest buildings" },
    { "value": "more_options", "label": "More options (anywhere on campus)" }
  ],
  "durations_minutes": [30, 60, 90, 120, 150, 180, 210, 240, 300],
  "date_min": "2026-09-01",
  "date_max": "2026-12-19",
  "earliest_start": "08:00",
  "latest_finish": "22:00",
  "data_as_of": "2026-11-12"
}
```

The values above illustrate the response shape; building data, date range, and `data_as_of` come from the current
database. `date_min`, `date_max`, and `data_as_of` can be `null` if the database has no coverage. `room_count` is the
number of rooms with imported timetable coverage for the building.

### `POST /api/rooms/search`

Send JSON with these fields:

```json
{
  "building_code": "GLA.FT",
  "date": "2026-11-17",
  "start_time": "14:00",
  "duration_minutes": 60,
  "search_preference": "closest_buildings"
}
```

`date` is `YYYY-MM-DD`; `start_time` is 24-hour Dublin local time (`HH:MM`). `duration_minutes` is an integer,
validated against the request model's 15-240 bound and the configured `MIN_DURATION_MINUTES` /
`MAX_DURATION_MINUTES` (defaults: 30-240). The options endpoint lists the offered duration choices; it does not
define the complete set of values accepted by the API. `search_preference` must be one of `same_building`,
`closest_buildings`, or `more_options`.

The response follows the shared `AgentResult` shape. Example with rooms found:

```json
{
  "status": "ok",
  "summary": "3 rooms potentially available on Tue 17 Nov, 14:00-15:00: GLA.FT101, GLA.FT102 and 1 more from GLA.FT.\nThese rooms are not guaranteed to be empty, unlocked or open to students.",
  "ai_note": null,
  "facts": {
    "find_rooms_in_building": {
      "building_code": "GLA.FT",
      "building_name": "Polaris",
      "date": "2026-11-17",
      "start_time": "14:00",
      "end_time": "15:00",
      "duration_minutes": 60,
      "search_preference": "closest_buildings",
      "count": 3,
      "can_expand": true,
      "rooms": [
        {
          "room_name": "GLA.FT101",
          "building_code": "GLA.FT",
          "building_name": "Polaris",
          "distance_metres": null,
          "free_until": null,
          "stage": "preferred"
        },
        {
          "room_name": "GLA.FT102",
          "building_code": "GLA.FT",
          "building_name": "Polaris",
          "distance_metres": null,
          "free_until": null,
          "stage": "preferred"
        },
        {
          "room_name": "GLA.FT103",
          "building_code": "GLA.FT",
          "building_name": "Polaris",
          "distance_metres": null,
          "free_until": "17:00",
          "stage": "preferred"
        }
      ],
      "rooms_checked": 4,
      "rooms_without_data": 0,
      "data_as_of": "2026-11-12"
    }
  },
  "trace": {
    "llm_ok": true,
    "tool_sources": { "find_rooms_in_building": "model" },
    "decision": null,
    "errors": [],
    "timings": { "tool_turn": 0.42 },
    "note_rejected": null,
    "seconds": 1.23,
    "tool_turns": 1,
    "tool_calls": [["find_rooms_in_building"]]
  },
  "options": null
}
```

This is a shape example, not a fixed result. In an actual response:

- `status` is `ok` when rooms are found, `none` when none are found (or a search tool reports an error),
  or `unsupported` if the agent rejects the request. The other shared status, `needs_choice`, is not currently
  used by this feature.
- `summary` is composed in Python. It may contain a second sentence explaining an expanded search or suggesting
  another preference, and a final availability caveat when rooms are found. It lists up to two room codes per
  building; use `facts` for the detailed results.
- `ai_note` is optional and may be `null`; do not rely on or require it.
- `facts.find_rooms_in_building` is always present for a completed search. Its `rooms` list is capped per building
  by `MAX_ROOMS_PER_BUILDING` (default 6); `count` is the full number found. A room has `room_name`,
  `building_code`, `building_name`, `distance_metres`, `free_until`, and `stage`. `free_until` is a local `HH:MM`
  time or `null` if no later event was recorded that day.
- `facts.find_rooms_nearby` is present only if the wider-search tool ran. It reports its additional `rooms` and
  `count`, plus `searched` buildings, `stages_used`, `skipped`, `exhausted`, and `no_nearby_data`. The count for
  this tool is additional to the preferred building's count.
- `trace` is for diagnostics and can change; frontend behavior must not depend on it. `options` is `null` for
  this endpoint.

Invalid request shape, unsupported duration/time, or a date outside timetable coverage returns HTTP `422` with
FastAPI's `detail`; an unknown or unsearchable building returns `404`; an unavailable timetable database returns
`503`. Validate and display these HTTP errors separately from an `AgentResult`.

## Search behavior

1. The API validates the time slot and checks the building and timetable coverage **before** calling the agent.
   Submitted form values are pinned so the model cannot alter them.
2. The required `find_rooms_in_building` tool checks the preferred building first.
3. If fewer than `MIN_ROOMS` rooms are found (default 2) and the preference allows expansion, the search checks
   nearby buildings, nearest first, stopping when enough rooms are found.
4. Only `More options` continues beyond the nearby limit, searching known farther buildings first and then
   buildings without distance data. Python enforces the rule and each tool independently respects the preference.
5. Python builds the final summary from the tool results. The model may provide a one-sentence `ai_note`, but it is
   checked before inclusion and is never the source of the room facts.

| Preference | Preferred building | Nearby buildings | Rest of campus |
| --- | :-: | :-: | :-: |
| `same_building` | yes | no | no |
| `closest_buildings` | yes | yes | no |
| `more_options` | yes | yes | yes |

`NEARBY_MAX_METRES` controls the nearby threshold (default 200 m). `MAX_ROOMS_PER_BUILDING`, `MIN_ROOMS`, and the
minimum/maximum duration are configurable through settings/environment variables. Search hours are currently
08:00-22:00 in `tools/rooms.py`.

## Availability and data

All data comes from `data/timetable.db` (`timetable_events`, `timetable_event_rooms`, `room_sync_coverage`,
`teaching_rooms`, `buildings`, and `building_proximity`), opened read-only. A room is included only when its
coverage includes the entire requested slot and no linked event overlaps it (`event_start < slot_end` and
`event_end > slot_start`). Back-to-back events do not clash. Only `WRB-CANCELLED` events are ignored; all other
event types, including missing event types, block the room. Dublin local times are converted to UTC for database
comparisons.

The database is an imported snapshot, so bookings made after the relevant import may be missing. `data_as_of`
reports the oldest successful room import date; it is available in the options response and tool facts, but is not
currently shown in the result summary. Buildings without imported room coverage are not offered in the form.
Nearby expansion also depends on available rows in `building_proximity`; `More options` can still search supported
buildings without known distances.

## Running and testing

```bash
python scripts/init_db.py
python scripts/try_feature_b.py GLA.FT 2026-11-17 11:00 120 more_options --no-llm
python -m pytest backend/tests/featureBtests
uvicorn backend.app.main:app --port 8080
```

The API is then available at `http://localhost:8080/api/rooms/options` and
`http://localhost:8080/api/rooms/search`.
