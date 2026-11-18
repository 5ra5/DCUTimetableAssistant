from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    _DUBLIN = ZoneInfo("Europe/Dublin")
except Exception:  # tzdata missing -> fall back to UTC
    _DUBLIN = timezone.utc


def _fmt_when(iso) -> str:
    """'2026-11-19T10:00:00Z' -> '10:00 - 19/11/2026' (Irish local time, matching the frontend)."""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_DUBLIN).strftime("%H:%M - %d/%m/%Y")
    except ValueError:
        return str(iso)


def _details(r: dict) -> str:
    return f"{r['module_name']} in room {r['room_name']} at {_fmt_when(r['start_time'])}"


def lecturer_summary_A(facts: dict) -> str:
    schedule = facts.get("get_lecturer_schedule", {})
    if schedule.get("status") == "success":
        return f"Found class: {_details(schedule['data'])}."

    summary = "No class found at this time slot."
    # only present if the fallback search actually ran
    if "find_next_lecturer" in facts:
        nxt = facts["find_next_lecturer"]
        if nxt.get("status") == "success":
            summary += f"\nThe lecturer's next class is {_details(nxt['data'])}."
        else:
            summary += "\nThe lecturer has no recorded classes."
    return summary
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
