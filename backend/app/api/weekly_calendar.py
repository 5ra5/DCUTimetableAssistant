from fastapi import APIRouter
from ..sync.redbrick_client import fetch_timetable_events
from datetime import datetime

"""This is the function for endpoint GET /weekly/timetable 
   used in feature A to get and display the weekly timetable
   of a degree"""

base_url = "https://timetable.redbrick.dcu.ie/api/v3/timetable"


router = APIRouter(tags=["timetable"])
@router.get("/weekly/timetable")
def get_weekly_timetable(programme_uuid, start, end):
    url = f"{base_url}/category/course/items/{programme_uuid}/events"
   
    weekly_events = fetch_timetable_events(url, start, end) #getting the time table as dictionary from the redbrick_client.py
    
    #where we will store the events of between start and end of the programme
    usable_timetable = []

    #get start  times and end times exist, make sure they are all valid time stamps, that endtimes are after start times, if any of these are true then we will skip the event
    #where we will count the number of skipped events that do not have a proper start and end times
    skipped_events = 0

    #selecting only these fields, so that timetable and tools for feature A can receive
    #only valid events
    for event in weekly_events:
        #check that the event has valid start and end times
        try: 
            event_start = datetime.fromisoformat(event["start"])
            event_end = datetime.fromisoformat(event["end"])
            if event_end <= event_start: #if the end time is before the start time, skip this event
                skipped_events += 1
                continue

        except(KeyError, TypeError, ValueError): #if the start and end times are not valid date strings, skip them
            skipped_events += 1
            continue

        extras = event.get("extras") or {}

        usable_timetable.append({
            "module_name1": event.get("module_name"), #full module name 1 from Redbrick e.g. CSC1202[1] Prompt Engineering and LLM-Based Agents
            "module_name2": extras.get("summary_long"), #shorted readable name in case name 1 does not exist
            "location": extras.get("location"),  #the room location
            "long_description": extras.get("description"), #what event it is, e.g. lab/lecture on campus
            "short_description": event.get("description"),
            "start": event.get("start"), #start time as in 2026-11-02T16:00:00Z
            "end": event.get("end") #end time as in 2026-11-02T17:00:00Z
        })

    usable_timetable.sort(key=sortHelper)
    return {"events": usable_timetable, "skipped_events": skipped_events} #LUCERO: make sure you inform chid about the skipped events

def sortHelper(event):
    return event.get("start")




#if __name__ == "__main__":
    #for line in get_weekly_timetable("0b5f2026-989f-0035-5e70-b86354e625a8","2026-11-02T00:00:00","2026-11-06T23:59:59"):
    #    print(line)
    #print(get_weekly_timetable("0b5f2026-989f-0035-5e70-b86354e625a8","2026-11-02T00:00:00","2026-11-06T23:59:59"))
    #print(get_weekly_timetable("d810d60d-8f84-834c-3fce-78cbec883f6e","2026-09-14T00:00:00","2026-09-19T23:59:59"))
    #print(get_weekly_timetable("af375a3e-003d-fab5-0a87-88a4b0bde60a","2026-10-05T00:00:00","2026-10-09T23:59:59"))
    #print(get_weekly_timetable("1e876675-54ad-ce6e-575f-aab0e0fcc827","2026-11-02T00:00:00","2026-11-06T23:59:59"))
    #print(get_weekly_timetable("d0495b89-0afa-15fa-7388-0c8c216379fa", "2026-09-14T00:00:00","2026-09-19T23:59:59"))
    #print(get_weekly_timetable("dddbcbe4-95d1-d531-8cb4-707c763d8adb", "2026-09-14T00:00:00","2026-09-19T23:59:59"))