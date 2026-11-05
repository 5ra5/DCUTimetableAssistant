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
