"""Try the agent with Ollama and the local database.

Start the app and Ollama:
    docker compose -f compose.yaml -f ollama.compose.yaml up -d --build

Then try a few cases:
    docker compose exec app python scripts/try_agent.py GLA.FT 100  # enough results
    docker compose exec app python scripts/try_agent.py GLA.A 200   # should search wider
    docker compose exec app python scripts/try_agent.py GLA.A 100   # should search wider

This adds a temporary 'buildings_demo' feature with a widening search, a model
decision, and an optional note. Its tools read the 'building_proximity' table
created by 'init_db.py'; they don't change project files. Check 'errors' in the
output to see where the engine caught and fixed a model mistake.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.agent import client as llm                       # noqa: E402
from backend.app.agent.engine import run_agent                    # noqa: E402
from backend.app.features import FEATURES, Branch, Decision, FeatureConfig   # noqa: E402

DB = Path(__file__).resolve().parent.parent / "data" / "timetable.db"
MIN_FOUND = 2

_SQL = """
SELECT CASE WHEN a.building_code = :b THEN c.building_code ELSE a.building_code END, p.distance_metres
FROM building_proximity p
JOIN buildings a ON a.id = p.building_a_id
JOIN buildings c ON c.id = p.building_b_id
WHERE (a.building_code = :b OR c.building_code = :b) AND p.distance_metres <= :m
ORDER BY p.distance_metres
"""


def _within(building: str, metres: float) -> dict:
    with sqlite3.connect(DB) as conn:
        if not conn.execute("SELECT 1 FROM buildings WHERE building_code = ?", (building,)).fetchone():
            return {"error": "unknown_building"}
        rows = conn.execute(_SQL, {"b": building, "m": metres}).fetchall()
    return {"building": building, "max_metres": metres, "buildings": [r[0] for r in rows], "count": len(rows)}


def find_buildings_within(building: str, max_metres: int) -> dict:
    """Find buildings no farther than max_metres from the requested building.

    Args:
        building: Building code, e.g. GLA.FT.
        max_metres: Search distance in metres, e.g. 200.
    """
    return _within(building, max_metres)


def find_buildings_within_wider(building: str, max_metres: int) -> dict:
    """Search up to twice max_metres from the requested building.

    Args:
        building: Building code, e.g. GLA.FT.
        max_metres: Original search distance in metres, e.g. 200.
    """
    return _within(building, max_metres * 2)


def summary(facts: dict) -> str:
    own = facts["find_buildings_within"]
    text = f"Found {own['count']} buildings within {own['max_metres']:g} metres of {own['building']}: {', '.join(own['buildings']) or 'none'}."
    wide = facts.get("find_buildings_within_wider")
    if wide:
        text += f" I also searched twice as far and found {wide['count']} buildings within {wide['max_metres']:g} metres: {', '.join(wide['buildings']) or 'none'}."
    return text


def register() -> None:
    FEATURES["buildings_demo"] = FeatureConfig(
        tools=[find_buildings_within, find_buildings_within_wider],
        required=["find_buildings_within"],
        template=summary,
        agent_hint="Always start with find_buildings_within for the requested building.",
        note_instruction=("Codes like GLA.FT are buildings, not rooms: never call them rooms. This is only about distances "
                          "between buildings, so say nothing about availability. Tell the student the result. If the text says a "
                          "wider search was done, say that you searched wider."),
        # If we searched wider, the note must mention it or give the wider distance.
        note_must_mention=lambda f: (("wider", "twice", "further", "broaden", "expand", f"{f['find_buildings_within_wider']['max_metres']:g}")
                                     if "find_buildings_within_wider" in f else ()),
        branch=Branch(
            after="find_buildings_within",
            next_tool="find_buildings_within_wider",
            needs_next=lambda r: r["count"] < MIN_FOUND,
            decision=Decision(
                continue_action="broaden_search",
                question=lambda r: f"Buildings found: {r['count']}. Minimum needed: {MIN_FOUND}.",
                system=(f"You decide the next step of a building search. The student needs at least {MIN_FOUND} buildings. "
                        f"If the number of buildings found is {MIN_FOUND} or more, choose finish. If it is less than {MIN_FOUND}, "
                        "choose broaden_search. First give a short reason that states the number found, then the action."),
            ),
        ),
    )


def main(argv: list) -> int:
    building, metres = (argv + ["GLA.A", "200"]
                        )[:2] if len(argv) < 2 else argv[:2]
    if not DB.exists():
        print("No database. Run: python scripts/init_db.py")
        return 1
    health = llm.health()
    print("health:", health)
    if health["ollama"] != "ok" or not health.get("model_installed"):
        print("-> Ollama is unreachable or the model is not pulled. Fix that first (the run below would use the fallback).\n")
    register()
    message = f"Find campus buildings within {metres} metres of {building}."
    print("message:", message, "\n")
    r = run_agent("buildings_demo", message, {
                  "building": building, "max_metres": int(metres)})
    t = r.trace
    print("status      :", r.status)
    print("summary     :", r.summary)
    print("ai_note     :", r.ai_note)
    print("llm_ok      :", t["llm_ok"])
    print("tool_sources:", t["tool_sources"])
    print("decision    :", t["decision"])
    print("errors      :", t["errors"] or "none")
    print("note_rejected:", t["note_rejected"])
    print("timings     :", t["timings"], "| total", t["seconds"], "s")
    expected = find_buildings_within(building, int(metres))
    print("\nCHECK summary facts match the database:",
          r.facts.get("find_buildings_within") == expected)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
