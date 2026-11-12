# Timetable database

This folder covers the SQLite database used by the DCU Smart Campus Timetable Assistant. The database brings together building and room information, Redbrick timetable events, modules and lecturer identifiers so the assistant can answer questions about room availability and where a lecturer is scheduled to teach.

The idea is to keep setup simple for the rest of the team. The data is already saved as CSV files, so you don't need to call the Redbrick API or collect anything manually just to run the project.

## Getting started

Run these commands from the **root of the repository**:

```bash
python3 scripts/init_db.py
```

This creates `data/timetable.db` (and the `data` folder if necessary), applies `backend/app/db/schema.sql`, and loads the seed files from `data/seed/`.

You only need Python 3 and SQLite support through Python's built-in `sqlite3` module for the initialisation script. No extra Python packages are needed for this step.

A successful run ends with checks similar to:

```text
Integrity check: ok
Foreign key violations: 0
```

The script can be run again without creating duplicate seed records. It updates or reuses existing records rather than inserting another copy of each one. Keep in mind that it isn't a database reset: existing data that isn't in the seed files won't necessarily be removed.

To inspect the database from the terminal, you can use the SQLite command-line tool:

```bash
sqlite3 data/timetable.db
```

Then, inside SQLite:

```sql
.tables
.quit
```

The SQLite command-line tool is useful for checking the data, but it isn't required to initialise it.

## What's included?

The current dataset contains:

| Table | Records | What it's for |
| --- | ---: | --- |
| `buildings` | 33 | Building names, codes and campuses |
| `building_proximity` | 45 | Distances between buildings |
| `programmes` | 940 | Programme details and Redbrick identifiers |
| `teaching_rooms` | 313 | Room names and Redbrick room IDs |
| `modules` | 4,985 | Modules from the Redbrick catalogue |
| `lecturers` | 37 | Lecturer labels used in Redbrick timetables |
| `lecturer_modules` | 60 | Known links between lecturers and modules |
| `directory_staff` | 32 | Candidate full names from staff-directory data |
| `lecturer_identity_mappings` | 32 | Possible matches between Redbrick labels and staff names |
| `timetable_events` | 21,614 | Scheduled events in the collected timetable snapshot |
| `timetable_event_rooms` | 25,489 | Links between events and rooms |
| `room_sync_coverage` | 207 | Rooms for which the semester timetable was successfully checked |

These counts are from a clean initialisation in **normal mode**. The numbers for staff and identity mappings change slightly if demo mode is enabled.

### Where the data comes from

The timetable, room, module and lecturer-label information was collected from the Redbrick DCU timetable service. Building information, proximity data and candidate lecturer names are held in separate seed files. The candidate full-name matches are **not verified identities** just because a Redbrick label looks similar to someone's name.

The timetable snapshot covers **1 September to 20 December 2026**. This is the date range used for the export, not a claim about the university's official semester dates.

There are 313 rooms in the room catalogue, but semester timetable requests were collected successfully for **207 rooms**. The other rooms should not be treated as available just because no events were imported for them.

## How the tables fit together

Most of the relationships are fairly straightforward:

- `timetable_events` stores each event once, identified by its Redbrick UUID.
- `timetable_event_rooms` connects an event to one or more rooms. A single event can use multiple rooms, which is why this table has more records than `timetable_events`.
- `teaching_rooms` holds the room catalogue, while `room_sync_coverage` records which room timetables were actually checked.
- `lecturer_modules` links known Redbrick lecturer labels to modules.
- `directory_staff` and `lecturer_identity_mappings` help with resolving abbreviated lecturer names. A mapping marked `candidate` should not be presented as confirmed.

Events with no physical room were not added to this seed dataset just to make the lecturer timetable appear more complete. During a cross-check, 24 additional events were found for CSC1015, but all were asynchronous recordings with no location. They weren't useful for locating a lecturer on campus.

## Example queries

These examples can be run in the SQLite terminal, or from Python using `sqlite3`.

**Find events scheduled in a particular room:**

```sql
SELECT
    r.room_name,
    e.event_name,
    e.staff_member,
    e.start_time,
    e.end_time
FROM timetable_events AS e
JOIN timetable_event_rooms AS er ON er.event_id = e.id
JOIN teaching_rooms AS r ON r.id = er.room_id
WHERE r.room_name = 'GLA.XG14'
ORDER BY e.start_time
LIMIT 20;
```

Replace `GLA.XG14` with a room name from `teaching_rooms` if that room isn't in your local data.

**Find a lecturer label's scheduled teaching locations:**

```sql
SELECT DISTINCT
    e.staff_member,
    e.start_time,
    e.end_time,
    r.room_name,
    e.module_name,
    e.event_name
FROM timetable_events AS e
JOIN timetable_event_rooms AS er ON er.event_id = e.id
JOIN teaching_rooms AS r ON r.id = er.room_id
WHERE e.staff_member = 'Healy G'
ORDER BY e.start_time
LIMIT 20;
```

This returns **scheduled room locations**, not the lecturer's live physical whereabouts. A Redbrick lecturer label also shouldn't be automatically treated as a verified full-name identity.

**Check how many rooms have timetable coverage:**

```sql
SELECT COUNT(DISTINCT room_id) AS rooms_checked
FROM room_sync_coverage;
```

The expected result for this snapshot is `207`.

## Using the database in the application

For **room availability (Feature B)**, check `room_sync_coverage` first to confirm the room has timetable data for the requested period. Then look for events whose times overlap the requested interval, using `timetable_event_rooms` to connect events to rooms. A room with no overlapping timetable event is *not necessarily* unlocked, accessible or bookable.

For **lecturer locations (Feature C)**, use the `staff_member` label in timetable events to find the rooms where someone is scheduled to teach. Lecturer names can be abbreviated or ambiguous, so full-name matches should be handled carefully. The `lecturer_identity_mappings` table can support a clarification question where there is more than one candidate.

Times in the event CSV are stored as UTC timestamps. Convert them to **Europe/Dublin** when showing dates and times to students; don't assume UTC and Irish local time are always the same.

Queries outside the exported date range, or for rooms without coverage, should return a clear *data not available* response rather than saying the room is free or the lecturer has no classes.

## Optional demo data

For the Feature C demonstration, there is a separate file:

```text
data/seed/demo_lecturer_ambiguity.csv
```

It adds **Grace Healy**, a fictional staff-directory identity, as a second possible match for the Redbrick label `Healy G`. The normal seed already contains **Graham Healy** as an existing *candidate* match. This allows the application to demonstrate asking the user which person they mean.

To include the fictional record in a **fresh** database, run:

```bash
python3 scripts/init_db.py --demo
```

Normal mode has 32 directory-staff records and 32 identity mappings; demo mode has 33 of each.

**A note on switching modes:** `--demo` adds a record; running the normal command afterwards does not automatically delete it. If you need a clean normal database after testing demo mode, back up or rename your existing `data/timetable.db` first, then run the normal initialisation command to create a new one.

Grace Healy is test data, not a real DCU lecturer. The application should label this option as a demo identity and **must not assign real `Healy G` timetable events to the fictional person**.

## Files worth knowing about

```text
backend/app/db/schema.sql             SQLite table definitions
scripts/init_db.py                    Creates and seeds the local database
scripts/export_semester_events.py     Exports the room timetable snapshot
scripts/check_lecturer_module_coverage.py
                                      Checks event coverage for known lecturer modules
data/seed/*.csv                        Data used to initialise SQLite
data/seed/unmatched_event_locations.csv
                                      Audit of locations not matched to the room catalogue
data/timetable.db                      Generated local database
```

The exporter and coverage-check scripts were used while preparing the dataset. You **don't** need to run them for normal setup. The raw API responses used during development are not required for initialisation either.

The unmatched-location report contains three location names that could not be confidently matched to a room in the catalogue (`GLA.N202`, `GLA.N222` and `GLA.FTG00LA`). These were left unresolved rather than guessing a room mapping. The report is for auditing and is not imported as a database table.

Avoid committing generated `.db` files, local backups or `data/raw/` to Git. The schema, scripts and seed CSVs are what teammates need to rebuild the database on their own machines.

## A few limitations to keep in mind

This is a **snapshot**, not a live timetable feed. Changes made after the data was exported won't appear until the dataset is refreshed. Lecturer coverage is limited to the identifiers and known module associations collected for this project, and a timetable location is not proof of where a lecturer is at that exact moment.

The current seed data is intended to support the team's prototype and demo. It provides a useful starting point for room and lecturer-location queries, but the application still needs to handle unknown rooms, missing coverage, ambiguous identities and dates outside the snapshot properly.
