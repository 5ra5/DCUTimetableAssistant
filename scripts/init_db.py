import csv
import sqlite3
from pathlib import Path

# --------------------------------------------------
# Project paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "data" / "timetable.db"
SCHEMA_PATH = ROOT / "backend" / "app" / "db" / "schema.sql"

DATA_DIR = ROOT / "data" / "seed"

BUILDINGS_CSV = DATA_DIR / "buildings.csv"
PROXIMITY_CSV = DATA_DIR / "building_proximity.csv"
PROGRAMMES_CSV = DATA_DIR / "programmes.csv"
LECTURERS_CSV = DATA_DIR / "lecturer_names.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def initialise_database():

    print("=== DCU DATABASE INITIALISATION ===")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # ------------------------------------------
        # Create tables
        # ------------------------------------------

        print("\nCreating database tables...")

        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema)

        print("Database schema created.")

        # ------------------------------------------
        # Import buildings
        # ------------------------------------------

        buildings = read_csv(BUILDINGS_CSV)

        for row in buildings:
            connection.execute(
                """
                INSERT INTO buildings (
                    building_code,
                    building_name,
                    campus
                )
                VALUES (?, ?, ?)
                ON CONFLICT(building_code)
                DO UPDATE SET
                    building_name = excluded.building_name,
                    campus = excluded.campus
                """,
                (
                    row["building_code"],
                    row["building_name"],
                    row["campus"],
                ),
            )

        print(f"Buildings imported: {len(buildings)}")

        # ------------------------------------------
        # Import building proximity
        # ------------------------------------------

        distances = read_csv(PROXIMITY_CSV)

        building_ids = {
            code: building_id
            for building_id, code in connection.execute(
                "SELECT id, building_code FROM buildings"
            )
        }

        for row in distances:

            building_a = building_ids[row["building_a_code"]]
            building_b = building_ids[row["building_b_code"]]

            connection.execute(
                """
                INSERT INTO building_proximity (
                    building_a_id,
                    building_b_id,
                    distance_metres,
                    distance_source,
                    last_verified
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT DO UPDATE SET
                    distance_metres = excluded.distance_metres,
                    distance_source = excluded.distance_source,
                    last_verified = excluded.last_verified
                """,
                (
                    building_a,
                    building_b,
                    float(row["distance_metres"]),
                    row["distance_source"],
                    row["last_verified"],
                ),
            )

        print(f"Building distances imported: {len(distances)}")

        # ------------------------------------------
        # Import programmes
        # ------------------------------------------

        programmes = read_csv(PROGRAMMES_CSV)

        for row in programmes:
            year = (
                int(row["year"])
                if row["year"].strip()
                else None
            )

            connection.execute(
                """
                INSERT INTO programmes (
                    redbrick_name,
                    programme_code,
                    degree,
                    year,
                    redbrick_uuid
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT(redbrick_uuid)
                DO UPDATE SET
                    redbrick_name = excluded.redbrick_name,
                    programme_code = excluded.programme_code,
                    degree = excluded.degree,
                    year = excluded.year
                """,
                (
                    row["redbrick_name"],
                    row["programme_code"],
                    row["degree"],
                    year,
                    row["redbrick_uuid"],
                ),
            )

        print(f"Programmes imported: {len(programmes)}")

        # ------------------------------------------
        # Import lecturers and directory staff
        # ------------------------------------------

        lecturers = read_csv(LECTURERS_CSV)

        for row in lecturers:

            identifier = row["redbrick_identifier"]
            full_name = row["full_name"]

            # Redbrick lecturer identifier
            connection.execute(
                """
                INSERT OR IGNORE INTO lecturers (
                    redbrick_identifier
                )
                VALUES (?)
                """,
                (identifier,),
            )

            # DCU staff directory
            # Source URL identifies this seed data source.
            connection.execute(
                """
                INSERT INTO directory_staff (
                    first_name,
                    last_name,
                    full_name,
                    role,
                    campus,
                    source_url
                )
                SELECT ?, ?, ?, NULL, NULL, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM directory_staff
                    WHERE full_name = ?
                      AND source_url = ?
                )
                """,
                (
                    row["first_name"],
                    row["last_name"],
                    full_name,
                    "https://www.dcu.ie/computing/people",
                    full_name,
                    "https://www.dcu.ie/computing/people",
                ),
            )

            lecturer_id = connection.execute(
                """
                SELECT id FROM lecturers
                WHERE redbrick_identifier = ?
                """,
                (identifier,),
            ).fetchone()[0]

            staff_id = connection.execute(
                """
                SELECT id FROM directory_staff
                WHERE full_name = ?
                  AND source_url = ?
                """,
                (
                    full_name,
                    "https://www.dcu.ie/computing/people",
                ),
            ).fetchone()[0]

            # Identity mapping
            connection.execute(
                """
                INSERT INTO lecturer_identity_mappings (
                    lecturer_id,
                    staff_id,
                    verification_status,
                    verification_note
                )
                VALUES (?, ?, ?, ?)

                ON CONFLICT(staff_id, lecturer_id)
                DO UPDATE SET
                    verification_status =
                        excluded.verification_status,
                    verification_note =
                        excluded.verification_note
                """,
                (
                    lecturer_id,
                    staff_id,
                    row["verification_status"],
                    row["verification_note"],
                ),
            )

        print(f"Lecturer mappings imported: {len(lecturers)}")

        # ------------------------------------------
        # Final checks
        # ------------------------------------------

        connection.commit()

        print("\n=== DATABASE COUNTS ===")

        tables = [
            "buildings",
            "building_proximity",
            "programmes",
            "lecturers",
            "directory_staff",
            "lecturer_identity_mappings",
        ]

        for table in tables:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(f"{table}: {count}")

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print("\nDatabase integrity:", integrity)

        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print("Foreign key violations:", len(foreign_keys))

        print("\nDatabase saved to:")
        print(DB_PATH)

    finally:
        connection.close()


if __name__ == "__main__":
    initialise_database()
