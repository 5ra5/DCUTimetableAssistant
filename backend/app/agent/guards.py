"""queries the system can't answer are refused with an explanation, WITHOUT calling the model.

The database holds timetable data only (classes, rooms, times). It has no office locations, emails or
phone numbers, so a question about them must never reach the model, which might invent an answer.
"""
import re
from typing import Optional

_UNSUPPORTED = re.compile(
    r"\b(offices?|e-?mails?|phone|telephone|contact|extension|mobile)\b", re.IGNORECASE)

UNSUPPORTED_SUMMARY = (
    "I can't help with that. I only have timetable information (classes, rooms and times). "
    "I don't have office locations, email addresses or phone numbers for staff."
)


def unsupported_reason(text: str) -> Optional[str]:
    """Return the matched word if the text asks for something we don't have, otherwise None."""
    m = _UNSUPPORTED.search(text or "")
    return m.group(0).lower() if m else None
