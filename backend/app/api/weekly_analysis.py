from fastapi import APIRouter, HTTPException
import sqlite3
from .programmes import DB_PATH
from ..agent.engine import run_agent
from ..schema import AgentResult, WeeklyAnalysisRequest
from .weekly_calendar import get_weekly_timetable
from .weekly_dates import get_monday_dates
from ..features.analysis_options import ANALYSIS_OPTIONS

router = APIRouter()
#CONCEPTUAL LAYOUT NEED TO UPDATE
@router.post("/weekly/analysis", response_model=AgentResult)
def weekly_analysis(request: WeeklyAnalysisRequest):
    #validating that the selected programme exists in the db
    con = sqlite3.connect(DB_PATH)
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT 1 FROM programmes WHERE redbrick_uuid = ?",
            (request.programme_uuid,)
        )
        programme = cursor.fetchone()
    finally:
        con.close()

    if programme is None:
        raise HTTPException(status_code=404, detail="Programme not found")

    #validate the start and end dates
    valid_weeks = get_monday_dates()

    week_found = False

    for week in valid_weeks:
        if week["start"] == request.start and week["end"] == request.end:
            week_found = True
            break

    if not week_found:
        raise HTTPException(
            status_code=422,
            detail="Invalid teaching week"
        )

    #validating the selected analysis option
    selected = ANALYSIS_OPTIONS.get(request.analysis_option)

    if selected is None:
        raise HTTPException(
            status_code=422,
            detail="Invalid analysis option",)

    #select the agent feature to handle the selected analysis option
    feature = selected["feature"]

    #fetch programme's weekly timetable.
    timetable = get_weekly_timetable(
        request.programme_uuid,
        request.start,
        request.end
    )

    #extract the validated timetable events from the result of get_weekly_timetable()
    weekly_events = timetable["events"]

    #prepare the tools'arguments (perhaps need to change this)
    pinned = {"weekly_events": weekly_events}

    #using the same analysis option as displayed to the user for ollama to understand the request
    user_message = (
        "Analyse the student's weekly timetable. "
        f"Selected analysis: {selected['label']}"
    )

    #RUN AGENT HERE:
    result = run_agent(feature, user_message, pinned)
    return result