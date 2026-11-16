import sqlite3
import logging
import json
import unicodedata
from pathlib import Path
from ..config import settings

CURRPATH = Path(__file__).resolve().parent
DBPATH = settings.db_path
class CalendarDatabaseError(Exception):
    """Base error"""
    pass

class DatabaseConfigurationError(CalendarDatabaseError):
    """Connection issues"""
    pass 

def setup_connection():
    if not DBPATH.is_file():
        logging.error(f"Database file not found at: {DBPATH}")
        raise DatabaseConfigurationError(f"Database file missing at {DBPATH}")
    try:
        logging.info(f"Attempting to connect to database at: {DBPATH}")
        conn = sqlite3.connect(DBPATH, timeout=6.0)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.DatabaseError as e:
        logging.exception(f"Database file integrity failure. Path {DBPATH}. "
        "The file may be corrupted, encrypted, or in an invalid SQLite format.")
        raise  DatabaseConfigurationError("Could not connect to the storage engine.") from e


def fetch_all_events(query: str, params=()):
    conn = None
    try:
        conn = setup_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.exception("Failed to excecute fetch query")
        raise CalendarDatabaseError("Unable to retrieve calendar events") from e
    finally:
        if conn:
            conn.close()

def unicode_remover(text: str) -> str:
    if not isinstance(text, str):
        return ""
    normalised = unicodedata.normalize("NFKD", text)
    parsed_text = normalised.encode("ascii", "ignore").decode()
    return parsed_text

# Tools that the LLM Agent will eventually call
def search_lecturer(lecturer: str) -> dict:
    if not lecturer:
        return {"status": "error", 
                "message": "search term can not be empty"}
    if isinstance(lecturer, str) == False:
        return {"status": "error", 
                "message": "search term must be a string"}

    lecturer = unicode_remover(lecturer)
    lecturer = " ".join(lecturer.strip().split())

    logging.info(f"Attempting to search for {lecturer} in the database")
    query = ("""SELECT
                l.redbrick_identifier,
                GROUP_CONCAT(m.module_name, ", ") AS modules
                FROM lecturers as l
                JOIN lecturer_modules as lm ON lm.lecturer_id = l.id
                JOIN modules AS m ON lm.module_id = m.id
                LEFT JOIN lecturer_identity_mappings AS lim ON lim.lecturer_id = l.id
                LEFT JOIN directory_staff AS ds ON ds.id = lim.staff_id
                WHERE l.redbrick_identifier LIKE ?
                    OR ds.full_name LIKE ?
                GROUP BY l.id, l.redbrick_identifier""")
    
    results = fetch_all_events(query, (f"%{lecturer}%", f"%{lecturer}%",))
    logging.info(f"DEBUG:Recieved lecturer search term -> {results}")
    if not results:
        return {"status": "success", 
                "message": f"No lecturer found for {lecturer}"}
    if len(results) > 25:
        return {"status": "success", 
                "message": (f"Too many lecturers matched '{lecturer}'."
                "Please refine your search.")}
    if len(results) == 1:
        return {"status": "success", "data": results[0]}
    return {"status": "ambiguous", "candidates": results}

def find_next_lecturer(lecturer_id, date, time):
    if (not lecturer_id):
        logging.warning("Missing lecturer ID recieved. Please provide a lecturer ID.")
        return {"status": "error",
                "message": "Lecturer ID cannot be empty"}
    if ((not date or not time)):
        missingdata = "date" if date == None else "time"
        logging.warning(f"Missing {missingdata}")
        return {"status": "error",
                "message": "Both time and date are required"}

    formatted_time = f"{time}:00" if len(time.strip()) == 5 else time.strip()
    target_time = f"{date.strip()}T{formatted_time}Z"
    
    logging.info(f"Checking ahead for next avaliable teaching slot for {lecturer_id} on {date} at {time}")

    query = """
            SELECT
            r.room_name,
            e.staff_member,
            e.start_time,
            e.end_time,
            e.module_name
            FROM timetable_events as e
            JOIN timetable_event_rooms AS er ON er.event_id = e.id
            LEFT JOIN lecturers AS l on e.staff_member LIKE '%' || l.redbrick_identifier || '%'
            LEFT JOIN lecturer_identity_mappings AS lim ON lim.lecturer_id = l.id
            LEFT JOIN directory_staff AS ds ON ds.id = lim.staff_id
            JOIN teaching_rooms as r ON r.id = er.room_id
            WHERE (e.staff_member LIKE ? OR ds.full_name  LIKE ? OR ds.last_name  LIKE ?)
            LIMIT 1
            """
    
    results = fetch_all_events(query,  (f"%{lecturer_id.strip()}%", f"%{lecturer_id.strip()}%", f"%{lecturer_id.strip()}%"))
    if not results:
        logging.info(f"Search completed: No future classes found for {lecturer_id}")
        return {"status": "error", "message": f"No upcoming classes found for lecturer {lecturer_id}"}
    result = results[0]
    logging.info(f"SUCCESS: Found next class for {lecturer_id}"
                 f"Module: {result['module_name']}, Room: {result['room_name']}")
    
    return {"status": "success", "data": result}


def get_lecturer_schedule(lecturer_id, date, time):
    if (not lecturer_id):
        logging.warning("Missing lecturer ID recieved. Please provide a lecturer ID.")
        return {"status": "error", 
                "message": "Lecturer ID cannot be empty"}
    if ((not date or not time)):
        missingdata = "date" if date == None else "time"
        logging.warning(f"Missing {missingdata}")
        return {"status": "error", 
                "message": "Both time and date are required"}
    
    logging.info(f"Checking schedule for lecturer {lecturer_id} on {date} at {time}")
    formatted_time = f"{time}:00" if len(time.strip()) == 5 else time.strip()
    target_time = f"{date.strip()}T{formatted_time}Z"
    query = """
          SELECT
            r.room_name,
            e.staff_member,
            e.start_time,
            e.end_time,
            e.module_name
            FROM timetable_events as e
            JOIN timetable_event_rooms AS er ON er.event_id = e.id
            LEFT JOIN lecturers AS l on e.staff_member LIKE '%' || l.redbrick_identifier || '%'
            LEFT JOIN lecturer_identity_mappings AS lim ON lim.lecturer_id = l.id
            LEFT JOIN directory_staff AS ds ON ds.id = lim.staff_id
            JOIN teaching_rooms as r ON r.id = er.room_id
            WHERE (e.staff_member LIKE ? OR ds.full_name  LIKE ? OR ds.last_name  LIKE ?)
               AND ? >= e.start_time 
               AND ? < e.end_time 
            LIMIT 1
            """
    results = fetch_all_events(query, (f"%{lecturer_id.strip()}%", f"%{lecturer_id.strip()}%", f"%{lecturer_id.strip()}%",  target_time, target_time))

    if not results:
        logging.info(f"Search completed: Did not find class for {lecturer_id} at {time} on {date}")
        return {"status": "error", 
                "message": f"No class found for lecturer {lecturer_id} at {time} on {date}"}
    
    result = results[0]
    logging.info(f"SUCCESS: Found class for {lecturer_id}: "
    f"Module: {result['module_name']}, Room: {result['room_name']}")
    return {"status": "success", "data": result}

