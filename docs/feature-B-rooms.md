# Feature B: AI Room Locator

Finds teaching rooms with **no recorded timetable event or booking** for a requested time. Results are always
described as *potentially available*: a room with no clash may still be locked or booked outside Redbrick.

## Request flow

1. `POST /api/rooms/search` (`api/rooms.py`) checks the form: building exists (404), time within 08:00-22:00 and the
   date inside the imported timetable (422). `GET /api/rooms/options` returns what the frontend form needs (backend only: the frontend is built separately).
2. `run_agent("feature_b_rooms", ...)` runs the engine with the form values **pinned**.
3. **Tool 1 `find_rooms_in_building`** (always runs): free rooms in the preferred building.
4. **Branch rule** (`features/rooms.py: rooms_needs_next`): widen only if fewer than `MIN_ROOMS` (default 2) rooms
   were found **and** the preference allows it. The model is also asked (`broaden_search` / `finish`); Python's rule
   has the last word and the tool itself refuses to widen against the student's preference.
5. **Tool 2 `find_rooms_nearby`**: nearby buildings (<= 300 m, nearest first), then, for "More options" only, the
   rest of campus. Stops as soon as enough rooms are found.
6. `rooms_summary` writes the answer in Python; the model may add a one-sentence `ai_note` that is checked first.

| Preference | Same building | Nearby (<= 300 m) | Rest of campus |
| --- | :-: | :-: | :-: |
| Same building only | yes | no | no |
| Closest buildings | yes | yes | no |
| More options | yes | yes | yes |

## Data: zero Redbrick calls

Everything comes from `data/timetable.db` (`timetable_events`, `timetable_event_rooms`, `room_sync_coverage`,
`teaching_rooms`, `buildings`, `building_proximity`), opened **read-only**. A room is offered only if
(1) `room_sync_coverage` covers the slot, and (2) no linked event overlaps it (`start < slot_end AND end > slot_start`,
so back-to-back classes are fine). Only `WRB-CANCELLED` events are ignored; every other event type blocks the room.
Student times are Dublin local time and are converted to UTC before comparing.

## Rules you can change (top of `tools/rooms.py`)

`SEARCH_DAY_START/END` (08:00-22:00), `NEARBY_MAX_METRES` (300), `MAX_ROOMS_PER_BUILDING` (6),
`NON_BLOCKING_EVENT_TYPES`, `PREFERENCES`. The "at least 2 rooms" target is `MIN_ROOMS` in `config.py`.

## Known limitations

- The data is a snapshot (`data_as_of` is shown to the student); bookings made after the export are missing.
- 106 rooms have no building in `teaching_rooms` (AHC / SPC / some GLA) so they cannot be searched.
- `GLA.CA` and `GLA.T` have no rows in `building_proximity`: "Closest buildings" cannot widen from them, and
  "More options" shows other buildings without distances.
- Only the 12 buildings with imported room timetables appear in the form.

## Try it

```bash
python3 scripts/init_db.py
python3 scripts/try_feature_b.py GLA.CA 2026-11-17 11:00 120 more_options --no-llm
python3 -m pytest backend/tests/featureBtests
# app: uvicorn backend.app.main:app --port 8080  ->  POST http://localhost:8080/api/rooms/search
```