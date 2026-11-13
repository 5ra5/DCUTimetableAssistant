#summary for feature A tools

"""Readable, deterministic summaries for weekly timetable analysis."""


def _hours(value):
    """Format an hour count without unnecessary decimal places."""
    return f"{value:g} hour{'s' if value != 1 else ''}"


def _daily_summary(data):
    lines = ["Your daily timetable breakdown:"]

    for day, details in data.items():
        count = details["total_daily_events"]

        if count == 0:
            lines.append(f"{day}: No scheduled classes.")
            continue

        hours = _hours(details["total_scheduled_hours"])
        first = details["first_class"]
        last = details["last_class"]

        activities = [
            f"{number} {activity}{'s' if number != 1 else ''}"
            for activity, number in details.items()
            if activity not in (
                "total_daily_events",
                "total_scheduled_hours",
                "first_class",
                "last_class",
            )
            and isinstance(number, int)
            and number > 0
        ]

        lines.append(
            f"{day}: {count} scheduled classes "
            f"({', '.join(activities)}), "
            f"{hours} of teaching, from {first} to {last}."
        )

    return "\n".join(lines)


def _gaps_summary(data):
    total_gaps = sum(
        details["number_gaps"]
        for details in data.values()
        if isinstance(details, dict) and "number_gaps" in details
    )
    total_hours = sum(
        details["total_gaps_hours"]
        for details in data.values()
        if isinstance(details, dict) and "total_gaps_hours" in details
    )

    lines = [
        "Your free time between classes:",
        f"You have {total_gaps} gaps totaling {_hours(total_hours)}.",
    ]

    for day, details in data.items():
        if day == "longest_weekly_gap":
            continue

        count = details["number_gaps"]

        if count == 0:
            lines.append(f"{day}: No gaps between classes.")
            continue

        gaps = details["individual_daily_gaps"].values()
        periods = [
            f"{gap['gap_start']}–{gap['gap_end']}"
            for gap in gaps
        ]

        lines.append(
            f"{day}: {count} gap{'s' if count != 1 else ''} "
            f"({', '.join(periods)}), "
            f"totaling {_hours(details['total_gaps_hours'])}."
        )

    longest = data.get("longest_weekly_gap", [])

    if longest:
        periods = [
            f"{gap['day']} {gap['gap_start']}–{gap['gap_end']} "
            f"({_hours(gap['gap_duration'])})"
            for gap in longest
        ]
        lines.append("Longest gap: " + "; ".join(periods) + ".")

    return "\n".join(lines)


def _patterns_summary(data):
    lines = ["Your weekly class patterns:"]

    busiest = data.get("busiest_day", {})
    if busiest.get("days"):
        days = ", ".join(busiest["days"])
        lines.append(
            f"Busiest day: {days}, "
            f"with {_hours(busiest['scheduled_hours'])} scheduled."
        )

    lightest = data.get("lightest_day", {})
    if lightest.get("days"):
        days = ", ".join(lightest["days"])
        lines.append(
            f"Lightest day with classes: {days}, "
            f"with {_hours(lightest['scheduled_hours'])} scheduled."
        )

    free_days = data.get("days_without_classes", [])
    if free_days:
        lines.append("Days without classes: " + ", ".join(free_days) + ".")

    common = data.get("most_common_activity", {})
    if common.get("activities"):
        lines.append(
            "Most common activity: "
            + ", ".join(common["activities"])
            + f" ({common['count']} occurrences)."
        )

    earliest = data.get("earliest_start", {})
    if earliest.get("days") and earliest.get("time"):
        lines.append(
            f"Earliest start: {earliest['time']} "
            f"on {', '.join(earliest['days'])}."
        )

    latest = data.get("latest_finish", {})
    if latest.get("days") and latest.get("time"):
        lines.append(
            f"Latest finish: {latest['time']} "
            f"on {', '.join(latest['days'])}."
        )

    return "\n".join(lines)


def weekly_analysis_summary(facts: dict) -> str:
    """Build a readable summary from the Python tool results."""

    sections = []

    if "get_daily_breakdown" in facts:
        sections.append(_daily_summary(facts["get_daily_breakdown"]))

    if "analyse_free_gaps" in facts:
        sections.append(_gaps_summary(facts["analyse_free_gaps"]))

    if "analyse_class_patterns" in facts:
        sections.append(_patterns_summary(facts["analyse_class_patterns"]))

    if not sections:
        return "No timetable analysis results were available."

    return "\n\n".join(sections)
