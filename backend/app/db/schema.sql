CREATE TABLE IF NOT EXISTS "buildings" (
	"id"	INTEGER,
	"building_code"	TEXT NOT NULL UNIQUE,
	"building_name"	TEXT NOT NULL,
	"campus"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "teaching_rooms" (
	"id"	INTEGER,
	"redbrick_uuid"	TEXT UNIQUE,
	"room_name"	TEXT NOT NULL,
	"building_id"	INTEGER,
	"last_refreshed"	TEXT,
	FOREIGN KEY("building_id") REFERENCES "buildings"("id"),
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "building_proximity" (
	"id"	INTEGER,
	"building_a_id"	INTEGER NOT NULL,
	"building_b_id"	INTEGER NOT NULL,
	"distance_metres"	REAL NOT NULL, distance_source TEXT, last_verified TEXT,
	FOREIGN KEY("building_a_id") REFERENCES "buildings"("id"),
	FOREIGN KEY("building_b_id") REFERENCES "buildings"("id"),
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "lecturers" (
	"id"	INTEGER,
	"redbrick_identifier"	TEXT NOT NULL UNIQUE,
	"last_refreshed"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "modules" (
	"id"	INTEGER,
	"redbrick_uuid"	TEXT UNIQUE,
	"module_code"	TEXT,
	"module_name"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "directory_staff" (
	"id"	INTEGER,
	"first_name"	TEXT,
	"last_name"	TEXT,
	"full_name"	TEXT NOT NULL,
	"role"	TEXT,
	"campus"	TEXT,
	"source_url"	TEXT NOT NULL,
	"last_refreshed"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS lecturer_identity_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    staff_id INTEGER NOT NULL,
    lecturer_id INTEGER NOT NULL,

    verification_status TEXT NOT NULL DEFAULT 'candidate',
    verification_note TEXT,

    FOREIGN KEY (staff_id)
        REFERENCES directory_staff(id),

    FOREIGN KEY (lecturer_id)
        REFERENCES lecturers(id),

    UNIQUE (staff_id, lecturer_id)
);

CREATE TABLE IF NOT EXISTS "lecturer_modules" (
	"lecturer_id"	INTEGER,
	"module_id"	INTEGER,
	FOREIGN KEY("lecturer_id") REFERENCES "lecturers"("id"),
	FOREIGN KEY("module_id") REFERENCES "modules"("id"),
	PRIMARY KEY("lecturer_id","module_id")
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_building_pair
ON building_proximity (
    MIN(building_a_id, building_b_id),
    MAX(building_a_id, building_b_id)
);

-- Programme timetable mappings from Redbrick.
-- Used to identify the correct timetable when a student selects a course.

CREATE TABLE IF NOT EXISTS programmes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    redbrick_name TEXT NOT NULL,

    programme_code TEXT,

    degree TEXT,

    year INTEGER,

    redbrick_uuid TEXT NOT NULL UNIQUE
);

-- Speeds up searches by degree and year.
CREATE INDEX IF NOT EXISTS idx_programmes_degree_year
ON programmes(degree, year);

--- SEMESTER TIMETABLE EVENTS
CREATE TABLE IF NOT EXISTS timetable_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    redbrick_uuid TEXT NOT NULL UNIQUE,

    event_name TEXT,
    module_name TEXT,
    staff_member TEXT,
    description TEXT,
    event_type TEXT,

    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,

    CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_timetable_events_time
ON timetable_events(start_time, end_time);

--- EVENT TO ROOM RELATIONSHIPS
CREATE TABLE IF NOT EXISTS timetable_event_rooms (
    event_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,

    PRIMARY KEY (event_id, room_id),

    FOREIGN KEY (event_id)
        REFERENCES timetable_events(id),

    FOREIGN KEY (room_id)
        REFERENCES teaching_rooms(id)
);

CREATE INDEX IF NOT EXISTS idx_event_rooms_room
ON timetable_event_rooms(room_id);

--- ROOM TIMETABLE IMPORT COVERAGE
CREATE TABLE IF NOT EXISTS room_sync_coverage (
    room_id INTEGER NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    last_successful_sync TEXT NOT NULL,

    PRIMARY KEY (room_id, period_start, period_end),

    FOREIGN KEY (room_id)
        REFERENCES teaching_rooms(id),

    CHECK (period_end > period_start)
);