import sqlite3
from dotenv import load_dotenv
import os

"""This function belongs to endpoint GET /pogrammes
   it reads the programmes from SQLite and returns their names and UUIDS as json 
   for the frontend to populate the dropdown menu for feature A
"""

load_dotenv()
DB_PATH = os.getenv("DB_PATH")

def get_programmes():
   con  = sqlite3.connect(DB_PATH)
   cursor = con.cursor() #allows to execute SQL statements
   cursor.execute("SELECT redbrick_name, redbrick_uuid FROM programmes ORDER BY redbrick_name")
   data = cursor.fetchall()
   con.close()

   programmes = []

   for row in data:
      programmes.append({"redbrick_name": row[0], "redbrick_uuid": row[1]})

   return programmes


