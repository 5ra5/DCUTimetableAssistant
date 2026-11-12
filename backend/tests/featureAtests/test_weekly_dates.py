import backend.app.api.weekly_dates as weekly_dates
from datetime import date

#test 1 -> correct number of teaching weeks
def test_number_of_weeks():
    result = weekly_dates.get_monday_dates()

    assert len(result) == 12


#test 2 -> correct first teaching week
def test_first_week():
    result = weekly_dates.get_monday_dates()

    assert result[0] == {
        "label": "Monday, 07 September 2026",
        "start": "2026-09-07T00:00:00Z",
        "end": "2026-09-11T23:59:59Z"
    }


#test 3 -> correct last teaching week
def test_last_week():
    result = weekly_dates.get_monday_dates()

    assert result[-1] == {
        "label": "Monday, 23 November 2026",
        "start": "2026-11-23T00:00:00Z",
        "end": "2026-11-27T23:59:59Z"
    }


#test 4 -> every week starts on Monday and ends on Friday
def test_monday_to_friday():
    result = weekly_dates.get_monday_dates()

    for week in result:
        assert week["start"][10:] == "T00:00:00Z"
        assert week["end"][10:] == "T23:59:59Z"

        from datetime import date

        start_date = date.fromisoformat(week["start"][:10])
        end_date = date.fromisoformat(week["end"][:10])

        assert start_date.weekday() == 0
        assert end_date.weekday() == 4


#test 5 -> consecutive Mondays are seven days apart
def test_weeks_seven_days_apart():
    from datetime import date

    result = weekly_dates.get_monday_dates()

    for i in range(len(result) - 1):
        current = date.fromisoformat(result[i]["start"][:10])
        following = date.fromisoformat(result[i + 1]["start"][:10])

        assert (following - current).days == 7


# test 6 -> teaching start is not a Monday
def test_start_not_monday(monkeypatch):
    monkeypatch.setattr(weekly_dates, "teaching_start", "2026-09-09")
    monkeypatch.setattr(weekly_dates, "teaching_end", "2026-09-25")

    result = weekly_dates.get_monday_dates()

    assert result[0]["start"] == "2026-09-14T00:00:00Z"
    assert result[-1]["start"] == "2026-09-21T00:00:00Z"
    assert len(result) == 2


#test 7 -> semester ends during a teaching week
def test_end_before_friday(monkeypatch):
    monkeypatch.setattr(weekly_dates, "teaching_start", "2026-11-16")
    monkeypatch.setattr(weekly_dates, "teaching_end", "2026-11-26")

    result = weekly_dates.get_monday_dates()

    assert len(result) == 2

    assert result[-1] == {
        "label": "Monday, 23 November 2026",
        "start": "2026-11-23T00:00:00Z",
        "end": "2026-11-26T23:59:59Z"
    }


#test 8 -> start date is after end date
def test_start_after_end(monkeypatch):
    monkeypatch.setattr(weekly_dates, "teaching_start", "2026-12-01")
    monkeypatch.setattr(weekly_dates, "teaching_end", "2026-11-27")

    result = weekly_dates.get_monday_dates()

    assert result == []


#test 9 -> semester shorter than a week with no Monday
def test_no_monday_in_date_range(monkeypatch):
    monkeypatch.setattr(weekly_dates, "teaching_start", "2026-09-08")
    monkeypatch.setattr(weekly_dates, "teaching_end", "2026-09-11")

    result = weekly_dates.get_monday_dates()

    assert result == []


#test 10 -> only one teaching week
def test_single_week(monkeypatch):
    monkeypatch.setattr(weekly_dates, "teaching_start", "2026-09-07")
    monkeypatch.setattr(weekly_dates, "teaching_end", "2026-09-11")

    result = weekly_dates.get_monday_dates()

    assert result == [
        {
            "label": "Monday, 07 September 2026",
            "start": "2026-09-07T00:00:00Z",
            "end": "2026-09-11T23:59:59Z"
        }
    ]
