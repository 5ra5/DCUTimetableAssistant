import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.agent.engine import run_agent
from backend.app.features import FEATURES, FeatureConfig
from backend.app.features.weekly_summary import weekly_analysis_summary
from backend.app.tools.registry import (get_daily_breakdown, analyse_free_gaps, analyse_class_patterns)


# Sample validated events in the same format as weekly_calendar.py
weekly_events = [
    {
        "module_name1": "Computer Networks",
        "module_name2": "Computer Networks (Lecture)",
        "location": "FTG11",
        "long_description": "Lecture, On Campus",
        "short_description": "Lecture",
        "start": "2026-11-02T09:00:00Z",
        "end": "2026-11-02T11:00:00Z",
    },
    {
        "module_name1": "Advanced Algorithms",
        "module_name2": "Advanced Algorithms (Lecture)",
        "location": "FTG13",
        "long_description": "Lecture, On Campus",
        "short_description": "Lecture",
        "start": "2026-11-02T12:00:00Z",
        "end": "2026-11-02T13:00:00Z",
    },
    {
        "module_name1": "Advanced Algorithms",
        "module_name2": "Advanced Algorithms (Lab)",
        "location": "LG27",
        "long_description": "Lab, On Campus",
        "short_description": "Lab",
        "start": "2026-11-03T11:00:00Z",
        "end": "2026-11-03T13:00:00Z",
    },
]


def main():
    tests = [
        (
            "feature_a_test_gaps",
            analyse_free_gaps,
            "Find my free gaps between classes this week.",
        ),
        (
            "feature_a_test_patterns",
            analyse_class_patterns,
            "Analyse my weekly class patterns and busiest days.",
        ),
    ]

    for feature_name, tool, message in tests:
        # Register a temporary feature for this test only.
        FEATURES[feature_name] = FeatureConfig(
            tools=[
                get_daily_breakdown,
                analyse_free_gaps,
                analyse_class_patterns,
            ],
            required=[tool.__name__],
            template=weekly_analysis_summary,
            agent_hint=(
                f"Analyse the student's timetable. "
                f"For this test, select {tool.__name__}."
            ),
            note_instruction=(
                "Briefly explain the timetable analysis "
                "without inventing information."
            ),
        )

        print(f"\n=== TESTING {tool.__name__} ===")

        result = run_agent(
            feature_name,
            message,
            {"weekly_events": weekly_events},
        )

        expected = tool(weekly_events)
        actual = result.facts.get(tool.__name__)

        print("Status       :", result.status)
        print("Summary      :", result.summary)
        print("AI note      :", result.ai_note)
        print("LLM successful:", result.trace.get("llm_ok"))
        print("Tool sources :", result.trace.get("tool_sources"))
        print("Errors       :", result.trace.get("errors"))
        print("Timings      :", result.trace.get("timings"))

        assert result.status == "ok", (
            f"{tool.__name__}: agent status was not ok"
        )
        assert actual == expected, (
            f"{tool.__name__}: agent facts differ from Python result"
        )

        print(f"PASS: {tool.__name__} returned correct facts.")

        source = result.trace.get("tool_sources", {}).get(tool.__name__)

        if source == "model":
            print("PASS: Ollama selected the expected tool.")
        else:
            print(
                "NOTE: Python executed the expected tool, "
                "but Ollama did not select it."
            )


if __name__ == "__main__":
    main()
