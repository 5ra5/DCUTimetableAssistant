"""API endpoint for weekly timetable analysis options"""

from fastapi import APIRouter
from ..features.analysis_options import ANALYSIS_OPTIONS

router = APIRouter(prefix="/weekly", tags=["weekly_analysis"])

@router.get("/analysis/options")
def get_weekly_analysis_options():
    """return the available weekly timetable analysis choices"""
    options = []
    for option_id, option in ANALYSIS_OPTIONS.items():
        options.append({"value": option_id, "label": option["label"],})
    return options