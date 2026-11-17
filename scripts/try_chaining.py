"""Does the model chain tool calls? Measure it with the REAL Ollama on the features that need more than one tool.

    docker compose exec app python scripts/try_chaining.py                       # all variants, 4 cases each
    docker compose exec app python scripts/try_chaining.py --cases 6
    docker compose exec app python scripts/try_chaining.py --variants ok,nudge --features feature_a_week

A case is a different sample week (so the prompt differs: at temperature 0 repeating the same input gives the same
answer). For each wording of the message the model gets after a tool ran (a "variant"), it counts how often the model
called ALL the required tools itself, in one turn or over several turns, and how often Python had to run some.
The notes are switched off here, so a run is only the tool phase. Needs no internet (sample weeks, no Redbrick).
"""
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.agent import client as llm                          # noqa: E402
from backend.app.agent import engine                                 # noqa: E402
from backend.app.features import FEATURES                            # noqa: E402
from backend.app.features.analysis_options import ANALYSIS_OPTIONS   # noqa: E402
from backend.app.tools import weekly as wk                           # noqa: E402
from backend.tests.featureAtests import sample_timetables as sample  # noqa: E402

UUID = "0b5f2026-989f-0035-5e70-b86354e625a8"
WEEKS = [("comsci3_nov02", "2026-11-02"), ("comsci1_sep14", "2026-09-14"), ("combus2_oct5", "2026-10-05"),
         ("mint2_nov02", "2026-11-02"), ("bajh1_sep14", "2026-09-14"), ("comsci4_sep14", "2026-09-14")]
# the features whose `required` has more than one tool
FEATURE_NAMES = ["feature_a_gaps", "feature_a_week"]

_default_feedback, _default_nudge = engine._tool_feedback, engine._nudge
VARIANTS = {
    # name: (what the tool message says, extra user message after a turn while tools are still needed)
    # "OK. Still to do: a, b."
    "remaining": (_default_feedback, _default_nudge),
    # no hint at all
    "ok": (lambda name, result, left: "OK", lambda left: None),
    # the data, cut to 300 chars
    "result": (lambda name, result, left: json.dumps(result)[:300], lambda left: None),
    "nudge": (lambda name, result, left: "OK",
              # generic, names nothing
              lambda left: "Continue the analysis. Call any tool that is still needed."),
}


def sample_week(name):
    raw = [{"module_name": e["module_name1"], "description": e["short_description"], "start": e["start"], "end": e["end"],
            "extras": {"summary_long": e["module_name2"], "location": e["location"], "description": e["long_description"]}}
           for e in getattr(sample, name)]
    wk.fetch_timetable_events = lambda url, start, end: raw


def classify(trace, required):
    sources = trace["tool_sources"]
    if any(sources.get(n) != "model" for n in required):
        return "python finished it"
    return "all in one turn" if trace["tool_turns"] == 1 else "chained over turns"


def main(argv):
    def option(flag, default):
        return argv[argv.index(flag) + 1] if flag in argv else default
    cases = int(option("--cases", 4))
    variants = option("--variants", ",".join(VARIANTS)).split(",")
    features = option("--features", ",".join(FEATURE_NAMES)).split(",")

    health = llm.health()
    print("health:", health)
    if health["ollama"] != "ok" or not health.get("model_installed"):
        print("-> Ollama is unreachable or the model is not pulled; nothing below would be a real measurement.")
        return 1

    table = {}
    for feature in features:
        base = FEATURES[feature]
        # tool phase only
        FEATURES["_chaining_" +
                 feature] = dataclasses.replace(base, note_instruction="")
        labels = [o["label"]
                  for o in ANALYSIS_OPTIONS.values() if o["feature"] == feature]
        for variant in variants:
            engine._tool_feedback, engine._nudge = VARIANTS[variant]
            rows = []
            for i in range(cases):
                name, week_start = WEEKS[i % len(WEEKS)]
                sample_week(name)
                wk._cache.clear()
                message = (f"Analyse the weekly timetable of programme {UUID} for the week starting {week_start}. "
                           f"Selected analysis: {labels[i % len(labels)]}")
                r = engine.run_agent("_chaining_" + feature, message,
                                     {"programme_uuid": UUID, "week_start": week_start})
                kind = classify(r.trace, base.required)
                other = [e for e in r.trace["errors"]
                         if not e.startswith("python_ran")]
                rows.append(
                    (kind, r.trace["tool_turns"], r.trace["timings"].get("tool_turn", 0), other))
                print(f"{feature:15} {variant:10} {name:14} {kind:19} turns={r.trace['tool_turns']} "
                      f"calls={r.trace['tool_calls']} model_s={rows[-1][2]} other_errors={other or 'none'}")
            table[(feature, variant)] = rows
    engine._tool_feedback, engine._nudge = _default_feedback, _default_nudge

    print("\n=== summary: how often the model called every required tool itself")
    print(f"{'feature':16} {'variant':10} {'one turn':>9} {'chained':>8} {'python':>7} {'avg model s':>12}")
    for (feature, variant), rows in table.items():
        n = len(rows)
        def count(k): return sum(1 for r in rows if r[0] == k)
        print(f"{feature:16} {variant:10} {count('all in one turn'):>6}/{n:<2} {count('chained over turns'):>5}/{n:<2} "
              f"{count('python finished it'):>4}/{n:<2} {sum(r[2] for r in rows) / n:>12.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
