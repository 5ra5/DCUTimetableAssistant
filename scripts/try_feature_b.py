"""Try Feature B (AI Room Locator) from the command line, using the local database.

    python3 scripts/try_feature_b.py GLA.FT 2026-11-17 14:00 60 closest_buildings
    python3 scripts/try_feature_b.py GLA.CA 2026-11-17 11:00 120 more_options      # widens campus-wide
    python3 scripts/try_feature_b.py GLA.CA 2026-11-17 11:00 120 same_building --no-llm

Arguments: building_code date(YYYY-MM-DD) start(HH:MM) duration_minutes preference
           (preference = same_building | closest_buildings | more_options)

It prints (1) the two tools called directly, which shows exactly what the database says and needs NO Ollama, then
(2) the full agent answer. With --no-llm the model is switched off so only Python's rules run; without it the
script needs Ollama (see docs/how-the-agent-works.md). Check `errors` in the trace to see any model mistakes the
engine corrected. Nothing here calls Redbrick: all data comes from data/timetable.db (run scripts/init_db.py first).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.agent import client as llm                                 # noqa: E402
from backend.app.agent.engine import run_agent                              # noqa: E402
from backend.app.tools.rooms import find_rooms_in_building, find_rooms_nearby   # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--no-llm"]
    if len(args) != 5:
        sys.exit(__doc__)
    building, day, start, minutes, pref = args[0], args[1], args[2], int(args[3]), args[4]
    if "--no-llm" in sys.argv:
        def off(*a, **k):
            raise ConnectionError("model disabled by --no-llm")
        llm.chat = off

    print("=== tool 1: find_rooms_in_building")
    first = find_rooms_in_building(building, day, start, minutes, pref)
    print(json.dumps(first, indent=2))
    print("\n=== tool 2: find_rooms_nearby (the engine only runs it when the rule says so)")
    print(json.dumps(find_rooms_nearby(building, day, start, minutes, pref), indent=2))

    print("\n=== full agent run")
    pinned = {"building_code": building, "date": day, "start_time": start,
              "duration_minutes": minutes, "search_preference": pref}
    result = run_agent("feature_b_rooms", f"Find rooms in building {building}.", pinned)
    print("status:", result.status)
    print(result.summary)
    print("ai_note:", result.ai_note)
    print("trace:", json.dumps(result.trace, indent=2, default=str))


if __name__ == "__main__":
    main()