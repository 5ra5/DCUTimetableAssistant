"""Feature A (weekly analysis): the summary text for each menu option, built by Python from the tools' results.

`facts` is keyed by tool name: weekly_daily_breakdown, weekly_class_patterns, weekly_free_gaps (whichever the option
ran). Counts are written with their unit ("11 lectures", "7 hours") so agent/notes.py can compare a note against them.
"""

NO_CLASSES = "No classes were found for this programme in that week."
_DAY_STATS = ("total_daily_events", "total_scheduled_hours",
              "first_class", "last_class")   # not class types


def _duration(hours: float) -> str:
    minutes = round(hours * 60)
    h, m = divmod(minutes, 60)
    parts = []
    if h:
        parts.append(f"{h} hour" + ("" if h == 1 else "s"))
    if m:
        parts.append(f"{m} minute" + ("" if m == 1 else "s"))
    return " ".join(parts) or "0 minutes"


def _names(items) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _count(n: int, word: str) -> str:
    if word == "undetermined":
        word = "unclassified event"
    plural = "classes" if word == "class" else word + "s"
    return f"{n} {word if n == 1 else plural}"


def weekly_is_empty(facts: dict) -> bool:
    """True when the programme has no classes that week (status 'none')."""
    if "weekly_daily_breakdown" in facts:
        return all(day["total_daily_events"] == 0 for day in facts["weekly_daily_breakdown"].values())
    patterns = facts["weekly_class_patterns"]
    return patterns["busiest_day"] is None and not patterns["earliest_start"]["days"]


# ---------------------------------------------------------------- sentence builders
def _counts(days: dict) -> str:
    total = sum(day["total_daily_events"] for day in days.values())
    types: dict = {}
    for day in days.values():
        for name, n in day.items():
            if name not in _DAY_STATS:
                types[name] = types.get(name, 0) + n
    by_type = [_count(n, name) for name, n in sorted(
        types.items(), key=lambda kv: -kv[1])]
    return f"The week has {_count(total, 'class')}: {_names(by_type)}."


def _per_day(days: dict) -> list:
    lines = []
    for name, day in days.items():
        if day["total_daily_events"] == 0:
            lines.append(f"{name}: no classes.")
        else:
            lines.append(f"{name}: {_count(day['total_daily_events'], 'class')}, {_duration(day['total_scheduled_hours'])}, "
                         f"{day['first_class']} to {day['last_class']}.")
    return lines


def _patterns(patterns: dict) -> list:
    out = []
    busiest, lightest = patterns["busiest_day"], patterns["lightest_day"]
    if busiest:
        label, each = ("Busiest day", "") if len(
            busiest["days"]) == 1 else ("Busiest days", " each")
        out.append(
            f"{label}: {_names(busiest['days'])} ({_duration(busiest['scheduled_hours'])}{each}).")
    if lightest and (not busiest or lightest["days"] != busiest["days"]):
        label, each = ("Lightest day", "") if len(
            lightest["days"]) == 1 else ("Lightest days", " each")
        out.append(
            f"{label}: {_names(lightest['days'])} ({_duration(lightest['scheduled_hours'])}{each}).")
    if patterns["days_without_classes"]:
        out.append(
            f"No classes on {_names(patterns['days_without_classes'])}.")
    early, late = patterns["earliest_start"], patterns["latest_finish"]
    if early["days"]:
        out.append(
            f"Earliest start: {early['time']} on {_names(early['days'])}.")
    if late["days"]:
        out.append(f"Latest finish: {late['time']} on {_names(late['days'])}.")
    return out


def _longest_gap(gaps: dict) -> str:
    longest = gaps["longest_weekly_gap"]
    if not longest:
        return "There are no gaps between classes."
    where = _names(
        f"{g['day']} ({g['gap_start']} to {g['gap_end']})" for g in longest)
    return f"Longest gap between classes: {_duration(longest[0]['gap_duration'])} on {where}."


def _gaps_per_day(gaps: dict, days: dict) -> list:
    lines = []
    for name, day in days.items():
        if day["total_daily_events"] == 0:
            lines.append(f"{name}: no classes.")
            continue
        found = list(gaps[name]["individual_daily_gaps"].values())
        if not found:
            lines.append(f"{name}: no gaps.")
        else:
            times = ", ".join(
                f"{g['gap_start']} to {g['gap_end']}" for g in found)
            lines.append(f"{name}: {_count(len(found), 'gap')} ({times}).")
    return lines


# ---------------------------------------------------------------- one summary per feature
def daily_summary(facts: dict) -> str:
    """'How is my week balanced?': classes by type, then each day."""
    if weekly_is_empty(facts):
        return NO_CLASSES
    days = facts["weekly_daily_breakdown"]
    return " ".join([_counts(days)] + _per_day(days))


def gaps_summary(facts: dict) -> str:
    """'When do I have free time?': the gaps of each day, then the longest."""
    if weekly_is_empty(facts):
        return NO_CLASSES
    gaps = facts["weekly_free_gaps"]
    return " ".join(_gaps_per_day(gaps, facts["weekly_daily_breakdown"]) + [_longest_gap(gaps)])


def patterns_summary(facts: dict) -> str:
    """'Which days are the busiest?': busiest and lightest days, free days, earliest start and latest finish."""
    if weekly_is_empty(facts):
        return NO_CLASSES
    return " ".join(_patterns(facts["weekly_class_patterns"]))


def week_summary(facts: dict) -> str:
    """'Analyse my whole week': the overview from all three tools."""
    if weekly_is_empty(facts):
        return NO_CLASSES
    return " ".join([_counts(facts["weekly_daily_breakdown"])] + _patterns(facts["weekly_class_patterns"])
                    + [_longest_gap(facts["weekly_free_gaps"])])
