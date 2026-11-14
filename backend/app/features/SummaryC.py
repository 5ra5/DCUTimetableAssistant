def lecturer_summary_A(facts: dict) -> str:
    schedule = facts.get("get_lecturer_schedule", {})
    if schedule.get("status") == "success":
        result = schedule["data"]
        return f"Found class: {result['module_name']} in room {result['room_name']} at {result['start_time']}."
    return "No class found at this time slot."

def lecturer_summary_B(facts: dict) -> str:
    request = facts.get("search_lecturer", {})
    if request.get("status") == "success":
        hits = request.get("data", [])
        count = len(hits)
        if count == 1:
            return f"Found exact matching lecturer: {hits[0]['name']}"
        return f"Found {count} matching lecturers. Please clarify which one to view their modules."
    return "No lecturers found matching that name."