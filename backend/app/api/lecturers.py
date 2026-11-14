from fastapi import APIRouter, HTTPException

from ..agent.engine import run_agent
from ..schema import LecturerScheduleQuery, LecturerSearchQuery

router = APIRouter(prefix="/lecturers", tags=["Lecturers"])

@router.post("/search")
def lecturer_search_route(query: LecturerSearchQuery):
    staged = {"lecturer_name": query.lecturer_name}
    user_message = f"Search for lecturer {query.lecturer_name}"
    return run_agent("feature_C_B", user_message, staged)

@router.post("/schedule")
def lecturer_schedule_route(query: LecturerScheduleQuery):
    staged = {
        "lecturer_name": query.lecturer_name,
        "date": query.date,
        "time": query.time,
    }

    user_message = f"Check schedule for {query.lecturer_name} on {query.date} at {query.time}"

    return run_agent("feature_C_A", user_message, staged)