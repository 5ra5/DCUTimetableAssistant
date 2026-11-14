from fastapi import APIRouter, HTTPException

from ..schema import LecturerScheduleQuery, LecturerSearchQuery
from ..tools.tools import search_lecturer, get_lecturer_schedule, find_next_lecturer

router = APIRouter(prefix="/lecturers", tags=["Lecturers", "Tools"])

def lecturer_schedule_fallback(query: LecturerScheduleQuery):
    return find_next_lecturer(
        lecturer_id=query.lecturer_id,
        date=query.date,
        time=query.time
    )

@router.post("/search")
def lecturer_search_route(query: LecturerSearchQuery):
    results = search_lecturer(query.lecturer_name)
    if not results:
        return {"status": "not_found", "message": "No lecturer matching that name was found"}
    return {"status": "success", "data": results}

@router.post("/schedule")
def lecturer_schedule_route(query: LecturerScheduleQuery):

    result = get_lecturer_schedule(
        lecturer_id = query.lecturer_id,
        date = query.date,
        time = query.time
    )
    
    if result:
        return {"status": "success", "match_type": "exact", "data": result}

    fallback_result = lecturer_schedule_fallback(query)

    if not fallback_result:
        return {"status": "not_found", "message": "No schedule or upcoming slots found for this lecturer."}
    
    return {"status": "fallback_used",
            "match_type": "fallback option",
            "message": "Showing next avaliable slot",
            "data": fallback_result
    }