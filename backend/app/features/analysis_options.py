"""Available weekly timetable analysis options for feature A"""

# keys such as week_balance are stable identifiers that the frontend will submit.
# "feature" (a key of FEATURES in features/features.py) decides what runs; "tool" is only a note for readers.
ANALYSIS_OPTIONS = {
    "week_balance": {
        "label": "How is my week balanced?",
        "tool": "weekly_daily_breakdown",
        "feature": "feature_a_daily",
    },
    "study_opportunities": {
        "label": "Find best studying opportunities.",
        "tool": "weekly_free_gaps",
        "feature": "feature_a_gaps",
    },
    "free_time": {
        "label": "When do I have free time?",
        "tool": "weekly_free_gaps",
        "feature": "feature_a_gaps",
    },
    "busiest_days": {
        "label": "Which days are the busiest?",
        "tool": "weekly_class_patterns",
        "feature": "feature_a_patterns",
    },
    "whole_week": {
        "label": "Analyse my whole week.",
        "tool": "all three analysis tools",
        "feature": "feature_a_week",
    },
    "weekly_insights": {
        "label": "What should I know about my week?",
        "tool": "weekly_class_patterns",
        "feature": "feature_a_patterns",
    },
}
