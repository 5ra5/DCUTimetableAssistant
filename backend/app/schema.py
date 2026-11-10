"""Request Models: FastAPI turns a failed request model validation into a 422 response with details of the failure"""

from datetime import datetime as _date, datetime
from pydantic import BaseModel, Field, field_validator

DATE = "%Y-%m-%d"
TIME = "%H:%M"

def check_date(v: str) ->str:
    """Check date format"""
    _date.fromisoformat(v) # raises ValueError if invalid
    return v

def check_time(v: str) ->str:
    """Check time format"""
    datetime.strptime(v, TIME) # raises ValueError if invalid
    return v

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
