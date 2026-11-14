"""Request and response models. FastAPI turns a failed request-model validation into a 422 response with details."""

from datetime import datetime as _date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

DATE = r"^\d{4}-\d{2}-\d{2}$"
TIME = "%H:%M"


def check_date(v: str) -> str:
    """Check date format (YYYY-MM-DD)"""
    _date.fromisoformat(v)  # raises ValueError if invalid
    return v


def check_time(v: str) -> str:
    """Check time format (HH:MM)"""
    datetime.strptime(v, TIME)  # raises ValueError if invalid
    return v

class LecturerSearchQuery(BaseModel):
    lecturer_name: str

class LecturerScheduleQuery(BaseModel):
    lecturer_name: str
    date: str
    time: str
    @field_validator("date")
    @classmethod
    def validate_date(clss, v: str) -> str:
        return check_date(v)
    @field_validator("time")
    @classmethod
    def validate_time(clss, v: str) -> str:
        return check_time(v)


class AgentResult(BaseModel):
    """The response of every agent endpoint. The frontend renders `facts` and `summary`,
    treats `ai_note` as optional and never depends on `trace`."""
    status: Literal["ok", "needs_choice", "none", "unsupported"]
    summary: str
    # one model-written sentence, only if it passed the checks. May be null
    ai_note: Optional[str] = None
    facts: dict = Field(default_factory=dict)   # {tool_name: tool result}
    # what the model did and every mistake it made (for the evaluators)
    trace: dict = Field(default_factory=dict)
    # lecturer search: the candidates the student chooses from
    options: Optional[list] = None


"""
SAMPLE REQUEST MODEL

class WeeklyRequest(BaseModel):
    course_code: str = Field(min_length=2, max_length=20, description="Programme code, e.g. COMSCI3")
    week_start: str = Field(pattern=DATE, description="Monday of the week, YYYY-MM-DD")

    @field_validator("week_start")
    @classmethod
    def _monday(cls, v):
        if _date.fromisoformat(check_date(v)).weekday() != 0:
            raise ValueError("week_start must be a Monday")
        return v
"""
