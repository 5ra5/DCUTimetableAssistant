"""POST /api/weekly/analysis - Feature A: the student picks a programme, a week and one of the analysis options."""
from fastapi import APIRouter, HTTPException

from ..agent.engine import run_agent
from ..features.analysis_options import ANALYSIS_OPTIONS
from ..schema import AgentResult, WeeklyAnalysisRequest
from .programmes import find_programme
from .weekly_dates import get_monday_dates

router = APIRouter()


@router.post("/weekly/analysis", response_model=AgentResult)
def weekly_analysis(request: WeeklyAnalysisRequest):
    # Check every input BEFORE any tool or model work: 422 for a bad option or week, 404 for an unknown programme.
    selected = ANALYSIS_OPTIONS.get(request.analysis_option)
    if selected is None:
        raise HTTPException(
            status_code=422, detail="Invalid analysis option (see GET /api/weekly/analysis/options)")
    if not any(w["start"] == request.start and w["end"] == request.end for w in get_monday_dates()):
        raise HTTPException(
            status_code=422, detail="Invalid teaching week (see GET /api/weeks)")
    if find_programme(request.programme_uuid) is None:
        raise HTTPException(status_code=404, detail="Programme not found")

    # The form values are pinned: whatever the model writes in a tool call, the tools get these. The tools load the
    # week's events themselves (tools/weekly.py), so the timetable is not passed through the model's arguments.
    pinned = {"programme_uuid": request.programme_uuid,
              "week_start": request.start[:10]}
    message = (f"Analyse the weekly timetable of programme {request.programme_uuid} for the week starting "
               f"{pinned['week_start']}. Selected analysis: {selected['label']}")
    return run_agent(selected["feature"], message, pinned)
