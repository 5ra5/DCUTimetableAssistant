import sqlite3

from fastapi import APIRouter

from ..config import settings

"""This function belongs to endpoint GET /programmes
   it reads the programmes from SQLite and returns their names and UUIDS as json
   for the frontend to populate the dropdown menu for feature A
"""

router = APIRouter(tags=["timetable"])

# one setting for the whole app (config.py); tests point this at a temporary database
DB_PATH = str(settings.db_path)


@router.get("/programmes")
def get_programmes():
    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()  # allows to execute SQL statements
    cursor.execute("SELECT redbrick_name, redbrick_uuid FROM programmes ORDER BY redbrick_name")
    data = cursor.fetchall()
    con.close()

    programmes = []

    for row in data:
        programmes.append({"redbrick_name": row[0], "redbrick_uuid": row[1]})

    return programmes


def find_programme(redbrick_uuid: str):
    """The programme row for this uuid, or None. Used to answer 404 before any tool or model work."""
    con = sqlite3.connect(DB_PATH)
    try:
        row = con.execute("SELECT redbrick_name, redbrick_uuid FROM programmes WHERE redbrick_uuid = ?",
                          (redbrick_uuid,)).fetchone()
    finally:
        con.close()
    return {"redbrick_name": row[0], "redbrick_uuid": row[1]} if row else None
