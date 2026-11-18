"""Run every Feature A menu option through the REAL engine with the REAL Ollama and the real tools.

    docker compose exec app python scripts/try_feature_a.py              # sample week, no internet needed
    docker compose exec app python scripts/try_feature_a.py --redbrick   # the live Redbrick timetable instead
    docker compose exec app python scripts/try_feature_a.py busiest_days # just one option

Per option it prints the summary, the note, which tools the model called itself and every mistake it made
(`errors`), and checks that `facts` equals what the tools return when called directly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.agent import client as llm                          # noqa: E402
from backend.app.agent.engine import run_agent                       # noqa: E402
from backend.app.features import FEATURES                            # noqa: E402
from backend.app.features.analysis_options import ANALYSIS_OPTIONS   # noqa: E402
from backend.app.tools import weekly as wk                           # noqa: E402

UUID = "0b5f2026-989f-0035-5e70-b86354e625a8"      # COMSCI3
WEEK = "2026-11-02"


def use_sample_week() -> None:
    from backend.tests.featureAtests.sample_timetables import comsci3_nov02 as events
    raw = [{"module_name": e["module_name1"], "description": e["short_description"], "start": e["start"], "end": e["end"],
            "extras": {"summary_long": e["module_name2"], "location": e["location"], "description": e["long_description"]}}
           for e in events]
    wk.fetch_timetable_events = lambda url, start, end: raw


def main(argv: list) -> int:
    live = "--redbrick" in argv
    wanted = [a for a in argv if not a.startswith(
        "--")] or list(ANALYSIS_OPTIONS)
    health = llm.health()
    print("health:", health)
    if health["ollama"] != "ok" or not health.get("model_installed"):
        print("-> Ollama is unreachable or the model is not pulled: the runs below only show the fallback.\n")
    if not live:
        use_sample_week()
    print("events from:", "live Redbrick" if live else "the built-in sample week", "\n")

    bad = 0
    for option in wanted:
        feature = ANALYSIS_OPTIONS[option]["feature"]
        pinned = {"programme_uuid": UUID, "week_start": WEEK}
        message = f"Analyse the weekly timetable of programme {UUID} for the week starting {WEEK}. Selected analysis: {ANALYSIS_OPTIONS[option]['label']}"
        wk._cache.clear()
        r = run_agent(feature, message, pinned)
        wk._cache.clear()
        expected = {name: getattr(wk, name)(**pinned)
                    for name in FEATURES[feature].required}
        t = r.trace
        print(f"=== {option}  ({feature})")
        print("status      :", r.status)
        print("summary     :", r.summary)
        print("ai_note     :", r.ai_note)
        print("llm_ok      :", t["llm_ok"],
              "| tool_sources:", t["tool_sources"])
        print("errors      :", t["errors"] or "none")
        print("note_rejected:", t["note_rejected"])
        print("timings     :", t["timings"], "| total", t["seconds"], "s")
        same = r.facts == expected
        bad += not same
        print("CHECK facts equal the tools' own output:", same, "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
