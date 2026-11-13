from fastapi import APIRouter, HTTPException
import sqlite3
from .programmes import DB_PATH
from ..agent.engine import run_agent
from ..schema import AgentResult, WeeklyAnalysisRequest
from .weekly_calendar import get_weekly_timetable
from .weekly_dates import get_monday_dates


router = APIRouter()
#CONCEPTUAL LAYOUT
"""
There are three things we still need to resolve:
1. Request validation: WeeklyAnalysisRequest needs to be defined in schema.py, including your actual six allowed options and date rules.
2. Programme validation: The README requires us to check that programme_uuid exists and return 404 if it doesn't. The example above doesn't implement that yet.
3. Agent arguments: We need to confirm how your Feature A configuration expects pinned values and how it distinguishes the six analysis options. We shouldn't assume that putting the option in the message is sufficient."""
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

    #generate the message and add the analysis option
    user_message = (f"Analyse the student's weekly timetable. Selected analysis: {request.analysis_option}.")

    #RUN AGENT HERE:
    # result = run_agent("feature_a", user_message, pinned)

    # Temporary response until the agent is integrated.
    return {
        "status": "unsupported",
        "summary": "Weekly analysis agent integration is pending.",
        "ai_note": None,
        "facts": {},
        "trace": {}
    }
