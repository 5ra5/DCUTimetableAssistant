def lecturer_summary_A(facts: dict) -> str:
    schedule = facts.get("get_lecturer_schedule", {})
    if schedule.get("status") == "success":
        result = schedule["data"]
        return f"Found class: {result['module_name']} in room {result['room_name']} at {result['start_time']}."
    return "No class found at this time slot."

def lecturer_summary_B(facts: dict) -> str:
    request = facts.get("search_lecturer", {})
    status = request.get("status")
    if status =="success" and "data" in request:
        lecturer = request["data"]
        return f"Found exact matching lecturer: {lecturer['redbrick_identifier']}"
    if status == "ambiguous":
        candidates = request.get("candidates", [])
        return f"Found {len(candidates)} matching lecturers. Please clarify which one"
    return request.get("message", "No lecturers found matching that name")
