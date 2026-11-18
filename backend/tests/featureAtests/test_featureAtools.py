from app.tools.featureAtools import get_daily_breakdown, analyse_free_gaps, analyse_class_patterns
from .sample_timetables import comsci3_nov02, comsci1_sep14, combus2_oct5, mint2_nov02, bajh1_sep14, comsci4_sep14
import pytest


#------------------------TESTING get_daily_breakdown ---------------------- 
#test1 -> computer science year 3
def test_comsci3():
    result = get_daily_breakdown(comsci3_nov02)

    assert result["Monday"] == {
        "lecture": 5,
        "total_daily_events": 5,
        "total_scheduled_hours": 6.0,
        "first_class": "09:00",
        "last_class": "17:00"
    }

    assert result["Tuesday"] == {
        "lab": 1,
        "lecture": 2,
        "total_daily_events": 3,
        "total_scheduled_hours": 4.0,
        "first_class": "11:00",
        "last_class": "16:00"
    }

    assert result["Wednesday"] == {
        "lecture": 3,
        "tutorial": 1,
        "lab": 1,
        "total_daily_events": 5,
        "total_scheduled_hours": 7.0,
        "first_class": "09:00",
        "last_class": "18:00"
    }

    assert result["Thursday"] == {
        "lecture": 1,
        "lab": 1,
        "total_daily_events": 2,
        "total_scheduled_hours": 3.0,
        "first_class": "10:00",
        "last_class": "15:00"
    }

    assert result["Friday"] == {
        "total_daily_events": 0,
        "total_scheduled_hours": 0,
        "first_class": None,
        "last_class": None
    }


#test2 -> computer science year 1
#mathematics lectures have unusual short_description values
def test_comsci1():
    result = get_daily_breakdown(comsci1_sep14)

    assert result["Monday"] == {
        "lecture": 2,
        "lab": 1,
        "total_daily_events": 3,
        "total_scheduled_hours": 5.0,
        "first_class": "09:00",
        "last_class": "16:00"
    }

    assert result["Tuesday"] == {
        "lecture": 1,
        "lab": 2,
        "total_daily_events": 3,
        "total_scheduled_hours": 5.0,
        "first_class": "10:00",
        "last_class": "16:00"
    }

    assert result["Wednesday"] == {
        "total_daily_events": 0,
        "total_scheduled_hours": 0,
        "first_class": None,
        "last_class": None
    }

    assert result["Thursday"] == {
        "lab": 1,
        "lecture": 4,
        "total_daily_events": 5,
        "total_scheduled_hours": 6.0,
        "first_class": "08:00",
        "last_class": "16:00"
    }

    assert result["Friday"] == {
        "lecture": 1,
        "total_daily_events": 1,
        "total_scheduled_hours": 1.0,
        "first_class": "10:00",
        "last_class": "11:00"
    }


#test 3 -> computing for Business Year 2
def test_combus2():
    result = get_daily_breakdown(combus2_oct5)

    assert result["Monday"] == {
        "lecture": 3,
        "lab": 1,
        "total_daily_events": 4,
        "total_scheduled_hours": 7.0,
        "first_class": "09:00",
        "last_class": "17:00"
    }

    assert result["Tuesday"] == {
        "lab": 2,
        "lecture": 2,
        "total_daily_events": 4,
        "total_scheduled_hours": 6.0,
        "first_class": "08:00",
        "last_class": "17:00"
    }

    assert result["Wednesday"] == {
        "total_daily_events": 0,
        "total_scheduled_hours": 0,
        "first_class": None,
        "last_class": None
    }

    assert result["Thursday"] == {
        "lecture": 3,
        "total_daily_events": 3,
        "total_scheduled_hours": 4.0,
        "first_class": "10:00",
        "last_class": "17:00"
    }

    assert result["Friday"] == {
        "total_daily_events": 0,
        "total_scheduled_hours": 0,
        "first_class": None,
        "last_class": None
    }


#test 4 -> marketing and Innovation Technology Year 2
#some short_description values are None
#workshops and lectures must still be counted correctly
def test_mint2():
    result = get_daily_breakdown(mint2_nov02)

    assert result["Monday"] == {
        "workshop": 1,
        "lecture": 1,
        "total_daily_events": 2,
        "total_scheduled_hours": 3.0,
        "first_class": "10:00",
        "last_class": "18:00"
    }

    assert result["Tuesday"] == {
        "lecture": 2,
        "total_daily_events": 2,
        "total_scheduled_hours": 4.0,
        "first_class": "12:00",
        "last_class": "16:00"
    }

    assert result["Wednesday"] == {
        "lecture": 1,
        "total_daily_events": 1,
        "total_scheduled_hours": 2.0,
        "first_class": "10:00",
        "last_class": "12:00"
    }

    assert result["Thursday"] == {
        "workshop": 1,
        "lecture": 2,
        "total_daily_events": 3,
        "total_scheduled_hours": 5.0,
        "first_class": "10:00",
        "last_class": "17:00"
    }

    assert result["Friday"] == {
        "total_daily_events": 0,
        "total_scheduled_hours": 0,
        "first_class": None,
        "last_class": None
    }


#test 5 -> gaeilge and Philosophy Year 1
#checks that seminars are recognized as an activity type
def test_bajh1():
    result = get_daily_breakdown(bajh1_sep14)

    assert result["Monday"] == {
        "total_daily_events": 0,
        "total_scheduled_hours": 0,
        "first_class": None,
        "last_class": None
    }

    assert result["Tuesday"] == {
        "seminar": 1,
        "lecture": 2,
        "total_daily_events": 3,
        "total_scheduled_hours": 4.0,
        "first_class": "08:00",
        "last_class": "16:00"
    }

    assert result["Wednesday"] == {
        "lecture": 2,
        "total_daily_events": 2,
        "total_scheduled_hours": 2.0,
        "first_class": "13:00",
        "last_class": "15:00"
    }

    assert result["Thursday"] == {
        "lecture": 4,
        "total_daily_events": 4,
        "total_scheduled_hours": 4.0,
        "first_class": "11:00",
        "last_class": "16:00"
    }

    assert result["Friday"] == {
        "lecture": 1,
        "total_daily_events": 1,
        "total_scheduled_hours": 1.0,
        "first_class": "12:00",
        "last_class": "13:00"
    }


#test 6 -> computer Science Year 4
#some short_description values contain module information.
def test_comsci4():
    result = get_daily_breakdown(comsci4_sep14)

    assert result["Monday"] == {
        "lecture": 2,
        "total_daily_events": 2,
        "total_scheduled_hours": 3.0,
        "first_class": "08:00",
        "last_class": "14:00"
    }

    assert result["Tuesday"] == {
        "lecture": 3,
        "total_daily_events": 3,
        "total_scheduled_hours": 4.0,
        "first_class": "09:00",
        "last_class": "15:00"
    }

    assert result["Wednesday"] == {
        "lecture": 2,
        "total_daily_events": 2,
        "total_scheduled_hours": 4.0,
        "first_class": "11:00",
        "last_class": "16:00"
    }

    assert result["Thursday"] == {
        "lecture": 1,
        "total_daily_events": 1,
        "total_scheduled_hours": 1.0,
        "first_class": "13:00",
        "last_class": "14:00"
    }

    assert result["Friday"] == {
        "total_daily_events": 0,
        "total_scheduled_hours": 0,
        "first_class": None,
        "last_class": None
    }


#test 7 -> completely empty timetable
def test_empty_week():
    result = get_daily_breakdown([])

    assert len(result) == 5

    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        assert result[day] == {
            "total_daily_events": 0,
            "total_scheduled_hours": 0,
            "first_class": None,
            "last_class": None
        }


#test 8 -> overlapping classes
#scheduled hours count each event, even when they overlap
def test_overlapping_classes():
    events = [
        {
            "long_description": "Lecture, On Campus",
            "short_description": "Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T11:00:00Z"
        },
        {
            "long_description": "Lab, On Campus",
            "short_description": "Lab",
            "start": "2026-11-02T10:00:00Z",
            "end": "2026-11-02T12:00:00Z"
        }
    ]

    result = get_daily_breakdown(events)

    assert result["Monday"] == {
        "lecture": 1,
        "lab": 1,
        "total_daily_events": 2,
        "total_scheduled_hours": 4.0,
        "first_class": "09:00",
        "last_class": "12:00"
    }


#test 9 -> missing long_description
#an unknown activity must still count as an event
def test_missing_description():
    events = [
        {
            "long_description": None,
            "short_description": "Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        }
    ]

    result = get_daily_breakdown(events)

    assert result["Monday"] == {
        "undetermined": 1,
        "total_daily_events": 1,
        "total_scheduled_hours": 1.0,
        "first_class": "09:00",
        "last_class": "10:00"
    }


#test 10 -> vents are not sorted
#first and last classes must be based on times, not list order
def test_unsorted_events():
    events = [
        {
            "long_description": "Lab, On Campus",
            "start": "2026-11-02T14:00:00Z",
            "end": "2026-11-02T16:00:00Z"
        },
        {
            "long_description": "Lecture, On Campus",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "long_description": "Tutorial, On Campus",
            "start": "2026-11-02T11:00:00Z",
            "end": "2026-11-02T12:00:00Z"
        }
    ]

    result = get_daily_breakdown(events)

    assert result["Monday"] == {
        "lab": 1,
        "lecture": 1,
        "tutorial": 1,
        "total_daily_events": 3,
        "total_scheduled_hours": 4.0,
        "first_class": "09:00",
        "last_class": "16:00"
    }


#test 11 -> description formatting
#activity names should ignore extra spaces and capitalization
def test_description_formatting():
    events = [
        {
            "long_description": "  LECTURE  , On Campus",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "long_description": "lecture, Online",
            "start": "2026-11-02T10:00:00Z",
            "end": "2026-11-02T11:00:00Z"
        }
    ]

    result = get_daily_breakdown(events)

    assert result["Monday"]["lecture"] == 2
    assert result["Monday"]["total_daily_events"] == 2
    assert result["Monday"]["total_scheduled_hours"] == 2.0

#---------------------------TESTING TOOL 2--------------------------------

#test 12-> computer science year 3
def test_gaps_comsci3():
    result = analyse_free_gaps(comsci3_nov02)

    assert result["Monday"]["number_gaps"] == 2
    assert result["Monday"]["total_gaps_hours"] == 2.0
    assert result["Monday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "13:00", "gap_end": "14:00"},
        "gap1": {"gap_duration": 1.0, "gap_start": "15:00", "gap_end": "16:00"}
    }

    assert result["Tuesday"]["number_gaps"] == 1
    assert result["Tuesday"]["total_gaps_hours"] == 1.0
    assert result["Tuesday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "13:00", "gap_end": "14:00"}
    }

    assert result["Wednesday"]["number_gaps"] == 2
    assert result["Wednesday"]["total_gaps_hours"] == 2.0
    assert result["Wednesday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "10:00", "gap_end": "11:00"},
        "gap1": {"gap_duration": 1.0, "gap_start": "14:00", "gap_end": "15:00"}
    }

    assert result["Thursday"]["number_gaps"] == 1
    assert result["Thursday"]["total_gaps_hours"] == 2.0
    assert result["Thursday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 2.0, "gap_start": "11:00", "gap_end": "13:00"}
    }

    assert result["Friday"]["number_gaps"] == 0
    assert result["Friday"]["total_gaps_hours"] == 0
    assert result["Friday"]["individual_daily_gaps"] == {}

    assert result["longest_weekly_gap"] == [
        {"day": "Thursday", "gap_start": "11:00",
         "gap_end": "13:00", "gap_duration": 2.0}
    ]


#test 13 -> computer science year 1
def test_gaps_comsci1():
    result = analyse_free_gaps(comsci1_sep14)

    assert result["Monday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 2.0, "gap_start": "12:00", "gap_end": "14:00"}
    }

    assert result["Tuesday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "12:00", "gap_end": "13:00"}
    }

    assert result["Wednesday"]["number_gaps"] == 0
    assert result["Wednesday"]["total_gaps_hours"] == 0

    assert result["Thursday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "10:00", "gap_end": "11:00"},
        "gap1": {"gap_duration": 1.0, "gap_start": "12:00", "gap_end": "13:00"}
    }

    assert result["Friday"]["number_gaps"] == 0

    assert result["longest_weekly_gap"] == [
        {"day": "Monday", "gap_start": "12:00",
         "gap_end": "14:00", "gap_duration": 2.0}
    ]


#test 14 -> computing for business year 2
def test_gaps_combus2():
    result = analyse_free_gaps(combus2_oct5)

    assert result["Monday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "12:00", "gap_end": "13:00"}
    }

    assert result["Tuesday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 2.0, "gap_start": "11:00", "gap_end": "13:00"},
        "gap1": {"gap_duration": 1.0, "gap_start": "14:00", "gap_end": "15:00"}
    }

    assert result["Wednesday"]["number_gaps"] == 0

    assert result["Thursday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 2.0, "gap_start": "11:00", "gap_end": "13:00"},
        "gap1": {"gap_duration": 1.0, "gap_start": "14:00", "gap_end": "15:00"}
    }

    assert result["Friday"]["number_gaps"] == 0

    assert result["longest_weekly_gap"] == [
        {"day": "Tuesday", "gap_start": "11:00",
         "gap_end": "13:00", "gap_duration": 2.0},
        {"day": "Thursday", "gap_start": "11:00",
         "gap_end": "13:00", "gap_duration": 2.0}
    ]


#test 15 -> marketing and innovation technology year 2
def test_gaps_mint2():
    result = analyse_free_gaps(mint2_nov02)

    assert result["Monday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 5.0, "gap_start": "11:00", "gap_end": "16:00"}
    }

    assert result["Tuesday"]["number_gaps"] == 0
    assert result["Wednesday"]["number_gaps"] == 0

    assert result["Thursday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 2.0, "gap_start": "11:00", "gap_end": "13:00"}
    }

    assert result["Friday"]["number_gaps"] == 0

    assert result["longest_weekly_gap"] == [
        {"day": "Monday", "gap_start": "11:00",
         "gap_end": "16:00", "gap_duration": 5.0}
    ]


#test 16 -> gaeilge and philosophy year 1
def test_gaps_bajh1():
    result = analyse_free_gaps(bajh1_sep14)

    assert result["Monday"]["number_gaps"] == 0

    assert result["Tuesday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "10:00", "gap_end": "11:00"},
        "gap1": {"gap_duration": 3.0, "gap_start": "12:00", "gap_end": "15:00"}
    }

    assert result["Wednesday"]["number_gaps"] == 0

    assert result["Thursday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "12:00", "gap_end": "13:00"}
    }

    assert result["Friday"]["number_gaps"] == 0

    assert result["longest_weekly_gap"] == [
        {"day": "Tuesday", "gap_start": "12:00",
         "gap_end": "15:00", "gap_duration": 3.0}
    ]


#test 17 -> computer science year 4
def test_gaps_comsci4():
    result = analyse_free_gaps(comsci4_sep14)

    assert result["Monday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 3.0, "gap_start": "10:00", "gap_end": "13:00"}
    }

    assert result["Tuesday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 2.0, "gap_start": "11:00", "gap_end": "13:00"}
    }

    assert result["Wednesday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "13:00", "gap_end": "14:00"}
    }

    assert result["Thursday"]["number_gaps"] == 0
    assert result["Friday"]["number_gaps"] == 0

    assert result["longest_weekly_gap"] == [
        {"day": "Monday", "gap_start": "10:00",
         "gap_end": "13:00", "gap_duration": 3.0}
    ]


#test 18 -> completely empty timetable
def test_gaps_empty_week():
    result = analyse_free_gaps([])

    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        assert result[day] == {
            "total_gaps_hours": 0,
            "number_gaps": 0,
            "individual_daily_gaps": {}
        }

    assert result["longest_weekly_gap"] is None


#test 19 -> overlapping classes must not create false gaps
def test_gaps_overlapping_classes():
    events = [
        {"start": "2026-11-02T09:00:00Z", "end": "2026-11-02T12:00:00Z"},
        {"start": "2026-11-02T10:00:00Z", "end": "2026-11-02T11:00:00Z"},
        {"start": "2026-11-02T11:30:00Z", "end": "2026-11-02T13:00:00Z"}
    ]

    result = analyse_free_gaps(events)

    assert result["Monday"]["number_gaps"] == 0
    assert result["Monday"]["total_gaps_hours"] == 0
    assert result["Monday"]["individual_daily_gaps"] == {}
    assert result["longest_weekly_gap"] is None


#test 20 -> consecutive classes have no gap
def test_gaps_consecutive_classes():
    events = [
        {"start": "2026-11-02T09:00:00Z", "end": "2026-11-02T10:00:00Z"},
        {"start": "2026-11-02T10:00:00Z", "end": "2026-11-02T11:00:00Z"}
    ]

    result = analyse_free_gaps(events)

    assert result["Monday"]["number_gaps"] == 0
    assert result["Monday"]["total_gaps_hours"] == 0
    assert result["longest_weekly_gap"] is None


#test 21 -> events in an unexpected order
def test_gaps_unsorted_events():
    events = [
        {"start": "2026-11-02T14:00:00Z", "end": "2026-11-02T15:00:00Z"},
        {"start": "2026-11-02T09:00:00Z", "end": "2026-11-02T10:00:00Z"},
        {"start": "2026-11-02T11:00:00Z", "end": "2026-11-02T12:00:00Z"}
    ]

    result = analyse_free_gaps(events)

    assert result["Monday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "10:00", "gap_end": "11:00"},
        "gap1": {"gap_duration": 2.0, "gap_start": "12:00", "gap_end": "14:00"}
    }

    assert result["Monday"]["number_gaps"] == 2
    assert result["Monday"]["total_gaps_hours"] == 3.0
    assert result["longest_weekly_gap"] == [
        {"day": "Monday", "gap_start": "12:00",
         "gap_end": "14:00", "gap_duration": 2.0}
    ]


#test 22 -> no gaps before the first or after the last class
def test_gaps_only_between_classes():
    events = [
        {"start": "2026-11-02T12:00:00Z", "end": "2026-11-02T13:00:00Z"}
    ]

    result = analyse_free_gaps(events)

    assert result["Monday"]["number_gaps"] == 0
    assert result["Monday"]["total_gaps_hours"] == 0
    assert result["Monday"]["individual_daily_gaps"] == {}
    assert result["longest_weekly_gap"] is None


#test 23 -> a real gap after overlapping classes
def test_gaps_after_overlap():
    events = [
        {"start": "2026-11-02T09:00:00Z", "end": "2026-11-02T12:00:00Z"},
        {"start": "2026-11-02T10:00:00Z", "end": "2026-11-02T11:00:00Z"},
        {"start": "2026-11-02T13:00:00Z", "end": "2026-11-02T14:00:00Z"}
    ]

    result = analyse_free_gaps(events)

    assert result["Monday"]["individual_daily_gaps"] == {
        "gap0": {"gap_duration": 1.0, "gap_start": "12:00", "gap_end": "13:00"}
    }

    assert result["Monday"]["number_gaps"] == 1
    assert result["Monday"]["total_gaps_hours"] == 1.0
    assert result["longest_weekly_gap"] == [
        {"day": "Monday", "gap_start": "12:00",
         "gap_end": "13:00", "gap_duration": 1.0}
    ]
#----------------------------TESTING TOOL 3------------------------------

#test 24 -> computer science year 3
def test_patterns_comsci3():
    result = analyse_class_patterns(comsci3_nov02)

    assert result["most_common_activity"] == {
        "activities": ["lecture"],
        "count": 11
    }

    assert result["busiest_day"] == {
        "days": ["Wednesday"],
        "scheduled_hours": 7.0
    }

    assert result["lightest_day"] == {
        "days": ["Thursday"],
        "scheduled_hours": 3.0
    }

    assert result["days_without_classes"] == ["Friday"]

    assert result["earliest_start"] == {
        "days": ["Monday", "Wednesday"],
        "time": "09:00"
    }

    assert result["latest_finish"] == {
        "days": ["Wednesday"],
        "time": "18:00"
    }


#test 25 -> computer science year 1
def test_patterns_comsci1():
    result = analyse_class_patterns(comsci1_sep14)

    assert result["most_common_activity"] == {
        "activities": ["lecture"],
        "count": 8
    }

    assert result["busiest_day"] == {
        "days": ["Thursday"],
        "scheduled_hours": 6.0
    }

    assert result["lightest_day"] == {
        "days": ["Friday"],
        "scheduled_hours": 1.0
    }

    assert result["days_without_classes"] == ["Wednesday"]

    assert result["earliest_start"] == {
        "days": ["Thursday"],
        "time": "08:00"
    }

    assert result["latest_finish"] == {
        "days": ["Monday", "Tuesday", "Thursday"],
        "time": "16:00"
    }


#test 26 -> computing for business year 2
def test_patterns_combus2():
    result = analyse_class_patterns(combus2_oct5)

    assert result["most_common_activity"] == {
        "activities": ["lecture"],
        "count": 8
    }

    assert result["busiest_day"] == {
        "days": ["Monday"],
        "scheduled_hours": 7.0
    }

    assert result["lightest_day"] == {
        "days": ["Thursday"],
        "scheduled_hours": 4.0
    }

    assert result["days_without_classes"] == ["Wednesday", "Friday"]

    assert result["earliest_start"] == {
        "days": ["Tuesday"],
        "time": "08:00"
    }

    assert result["latest_finish"] == {
        "days": ["Monday", "Tuesday", "Thursday"],
        "time": "17:00"
    }


#test 27 -> marketing and innovation technology year 2
def test_patterns_mint2():
    result = analyse_class_patterns(mint2_nov02)

    assert result["most_common_activity"] == {
        "activities": ["lecture"],
        "count": 6
    }

    assert result["busiest_day"] == {
        "days": ["Thursday"],
        "scheduled_hours": 5.0
    }

    assert result["lightest_day"] == {
        "days": ["Wednesday"],
        "scheduled_hours": 2.0
    }

    assert result["days_without_classes"] == ["Friday"]

    assert result["earliest_start"] == {
        "days": ["Monday", "Wednesday", "Thursday"],
        "time": "10:00"
    }

    assert result["latest_finish"] == {
        "days": ["Monday"],
        "time": "18:00"
    }


#test 28 -> gaeilge and philosophy year 1
def test_patterns_bajh1():
    result = analyse_class_patterns(bajh1_sep14)

    assert result["most_common_activity"] == {
        "activities": ["lecture"],
        "count": 9
    }

    assert result["busiest_day"] == {
        "days": ["Tuesday", "Thursday"],
        "scheduled_hours": 4.0
    }

    assert result["lightest_day"] == {
        "days": ["Friday"],
        "scheduled_hours": 1.0
    }

    assert result["days_without_classes"] == ["Monday"]

    assert result["earliest_start"] == {
        "days": ["Tuesday"],
        "time": "08:00"
    }

    assert result["latest_finish"] == {
        "days": ["Tuesday", "Thursday"],
        "time": "16:00"
    }


#test 29 -> computer science year 4
def test_patterns_comsci4():
    result = analyse_class_patterns(comsci4_sep14)

    assert result["most_common_activity"] == {
        "activities": ["lecture"],
        "count": 8
    }

    assert result["busiest_day"] == {
        "days": ["Tuesday", "Wednesday"],
        "scheduled_hours": 4.0
    }

    assert result["lightest_day"] == {
        "days": ["Thursday"],
        "scheduled_hours": 1.0
    }

    assert result["days_without_classes"] == ["Friday"]

    assert result["earliest_start"] == {
        "days": ["Monday"],
        "time": "08:00"
    }

    assert result["latest_finish"] == {
        "days": ["Wednesday"],
        "time": "16:00"
    }


#test 30 -> completely empty timetable
def test_patterns_empty_week():
    result = analyse_class_patterns([])

    assert result["most_common_activity"] is None
    assert result["busiest_day"] is None
    assert result["lightest_day"] is None

    assert result["days_without_classes"] == [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"
    ]

    assert result["earliest_start"] == {
        "days": [],
        "time": None
    }

    assert result["latest_finish"] == {
        "days": [],
        "time": None
    }


#test 31 -> multiple activity types tied for most common
def test_patterns_activity_tie():
    events = [
        {
            "long_description": "Lecture, On Campus",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T10:00:00Z"
        },
        {
            "long_description": "Lab, On Campus",
            "start": "2026-11-02T10:00:00Z",
            "end": "2026-11-02T11:00:00Z"
        },
        {
            "long_description": "Tutorial, On Campus",
            "start": "2026-11-03T09:00:00Z",
            "end": "2026-11-03T10:00:00Z"
        }
    ]

    result = analyse_class_patterns(events)

    assert set(result["most_common_activity"]["activities"]) == {
        "lecture", "lab", "tutorial"
    }
    assert result["most_common_activity"]["count"] == 1


#test 32 -> one class in the entire week
def test_patterns_one_class():
    events = [
        {
            "long_description": "Lecture, On Campus",
            "start": "2026-11-02T12:00:00Z",
            "end": "2026-11-02T13:00:00Z"
        }
    ]

    result = analyse_class_patterns(events)

    assert result["most_common_activity"] == {
        "activities": ["lecture"],
        "count": 1
    }

    assert result["busiest_day"] == {
        "days": ["Monday"],
        "scheduled_hours": 1.0
    }

    assert result["lightest_day"] == {
        "days": ["Monday"],
        "scheduled_hours": 1.0
    }

    assert result["days_without_classes"] == [
        "Tuesday", "Wednesday", "Thursday", "Friday"
    ]

    assert result["earliest_start"] == {
        "days": ["Monday"],
        "time": "12:00"
    }

    assert result["latest_finish"] == {
        "days": ["Monday"],
        "time": "13:00"
    }


#test 33 -> missing long description
#event still counts toward the daily hours and busiest day
def test_patterns_missing_description():
    events = [
        {
            "long_description": None,
            "short_description": "Lecture",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T11:00:00Z"
        }
    ]

    result = analyse_class_patterns(events)

    assert result["most_common_activity"] == {
        "activities": ["undetermined"],
        "count": 1
    }

    assert result["busiest_day"] == {
        "days": ["Monday"],
        "scheduled_hours": 2.0
    }

    assert result["lightest_day"] == {
        "days": ["Monday"],
        "scheduled_hours": 2.0
    }


#test 34 -> overlapping classes count as separate scheduled hours
def test_patterns_overlapping_classes():
    events = [
        {
            "long_description": "Lecture, On Campus",
            "start": "2026-11-02T09:00:00Z",
            "end": "2026-11-02T11:00:00Z"
        },
        {
            "long_description": "Lab, On Campus",
            "start": "2026-11-02T10:00:00Z",
            "end": "2026-11-02T12:00:00Z"
        }
    ]

    result = analyse_class_patterns(events)

    assert result["busiest_day"] == {
        "days": ["Monday"],
        "scheduled_hours": 4.0
    }

    assert result["lightest_day"] == {
        "days": ["Monday"],
        "scheduled_hours": 4.0
    }

    assert result["earliest_start"] == {
        "days": ["Monday"],
        "time": "09:00"
    }

    assert result["latest_finish"] == {
        "days": ["Monday"],
        "time": "12:00"
    }
