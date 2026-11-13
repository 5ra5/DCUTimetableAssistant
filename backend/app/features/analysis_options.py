"""Available weekly timetable analysis options for feature A"""

#keys such as week_balance are stable identifiers that the frontend will submit
ANALYSIS_OPTIONS = {
    "week_balance": {
        "label": "How is my week balanced?",
        "tool": "get_daily_breakdown",
        "feature": "feature_a_daily",
    },
    "study_opportunities": {
        "label": "Find best studying opportunities.",
        "tool": "analyse_free_gaps",
        "feature": "feature_a_gaps",
    },
    "free_time": {
        "label": "When do I have free time?",
        "tool": "analyse_free_gaps",
        "feature": "feature_a_gaps",
    },
    "busiest_days": {
        "label": "Which days are the busiest?",
        "tool": "analyse_class_patterns",
        "feature": "feature_a_patterns",
    },
    "whole_week": {
        "label": "Analyze my whole week.",
        "tool": "get_daily_breakdown",
        "feature": "feature_a_daily",
    },
    "weekly_insights": {
        "label": "What should I know about my week?",
        "tool": "get_daily_breakdown",
        "feature": "feature_a_patterns",
    },
}