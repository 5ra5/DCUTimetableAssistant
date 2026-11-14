#summary for feature A tools
def weekly_analysis_summary(facts: dict) -> str:
    """build a summary from the timetable analysis results"""

    if "get_daily_breakdown" in facts:
        return f"Your daily timetable breakdown: {facts['get_daily_breakdown']}"

    if "analyse_free_gaps" in facts:
        return f"Your free gaps analysis: {facts['analyse_free_gaps']}"

    if "analyse_class_patterns" in facts:
        return f"Your class patterns analysis: {facts['analyse_class_patterns']}"

    return "No timetable analysis results were available."