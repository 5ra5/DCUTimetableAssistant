"""
Smoke test for a hosted Ollama service, using the ollama library exactly as the engine does.
Run it BEFORE pointing the app at the service.

    export OLLAMA_HOST=https://ai.rb.dcu.ie/ollama      # no /v1: the library adds /api/chat itself
    export OLLAMA_API_KEY=...                           # sent as "Authorization: Bearer ..." (never printed)
    export OLLAMA_MODEL=qwen3.8:27b
    python scripts/try_hosted.py

Checks, in order: 1 the model is listed, 2 a plain reply, 3 a native tool call using the real
find_rooms_in_building signature and the engine's prompt, 4 the forced-JSON decision for 1 room (should
broaden) and 3 rooms (should finish). It uses the engine's real output limits (num_predict 60 / 80): a
"thinking" model can spend that budget on reasoning and return nothing, which this will show.
Exits non-zero if any check fails.
"""
import json
import os
import sys
import time
from pathlib import Path

import ollama

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.tools.registry import find_rooms_in_building      # noqa: E402  (same docstring the model sees)

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
KEY = os.environ.get("OLLAMA_API_KEY")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

client = ollama.Client(host=HOST, headers={
                       "Authorization": f"Bearer {KEY}"} if KEY else None, timeout=120)
failures = 0


def chat(**kw):
    """One call. Tries think=False first (reasoning models can burn the small token budget thinking)."""
    t0 = time.time()
    try:
        resp = client.chat(model=MODEL, think=False, **kw)
    except Exception as e:
        if "think" not in str(e).lower():
            raise
        print(
            "      (think=False was rejected by the library or model; retrying without it)")
        resp = client.chat(model=MODEL, **kw)
    return resp, time.time() - t0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failures
    failures += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


print(f"host={HOST}  model={MODEL}  key={'set' if KEY else 'NOT SET'}\n")

# 1. the model is listed
try:
    names = [m.model for m in client.list().models]
    check("model is listed", any(n == MODEL or n.startswith(MODEL)
          for n in names), f"({len(names)} models on the service)")
except Exception as e:
    check("model is listed", False, f"{type(e).__name__}: {e}")

# 2. plain reply
try:
    r, secs = chat(messages=[{"role": "user", "content": "Reply with the single word: ok"}], options={
                   "temperature": 0, "num_predict": 20})
    text = (r.message.content or "").strip()
    check("plain reply", bool(text), f"{secs:.1f}s -> {text[:40]!r}")
    if getattr(r.message, "thinking", None):
        print("      note: the reply included reasoning ('thinking') text, so this is a reasoning model")
except Exception as e:
    check("plain reply", False, f"{type(e).__name__}: {e}")

# 3. native tool call, same prompt and token limit as the engine's tool turn
try:
    r, secs = chat(
        messages=[{"role": "system", "content": "You are a timetable assistant for DCU students. Always call the provided tool "
                   "to get data; never answer from memory. Always start with find_rooms_in_building for the requested building."},
                  {"role": "user", "content": "Find a free room in GLA.FT on 2026-10-19 at 10:00 for 60 minutes."}],
        tools=[find_rooms_in_building], options={"temperature": 0, "num_predict": 60})
    calls = r.message.tool_calls or []
    detail = f"{secs:.1f}s -> " + (", ".join(
        f"{c.function.name}({dict(c.function.arguments)})" for c in calls) or "no tool call")
    check("native tool call", bool(calls)
          and calls[0].function.name == "find_rooms_in_building", detail)
except Exception as e:
    check("native tool call", False, f"{type(e).__name__}: {e}")

# 4. forced-JSON decision, same schema and prompt shape as the engine's branch decision
schema = {"type": "object",
          "properties": {"reason": {"type": "string"}, "action": {"type": "string", "enum": ["finish", "broaden_search"]}},
          "required": ["reason", "action"]}
system = ("You decide the next step of a room search. The student needs at least 2 free rooms. If the number of rooms found is "
          "2 or more, choose finish. If it is less than 2, choose broaden_search. First give a short reason that states the "
          "number found, then the action.")
for found, expected in [(1, "broaden_search"), (3, "finish"), (2, "finish"), (0, "broaden_search")]:
    try:
        r, secs = chat(messages=[{"role": "system", "content": system},
                                 {"role": "user", "content": f"Rooms found: {found}. Minimum needed: 2."}],
                       format=schema, options={"temperature": 0, "num_predict": 80})
        d = json.loads(r.message.content)
        check(f"decision, {found} room(s) -> {expected}", d.get("action")
              == expected, f"{secs:.1f}s  reason: {d.get('reason')}")
    except Exception as e:
        check(f"decision, {found} room(s) -> {expected}",
              False, f"{type(e).__name__}: {e}")

print(f"\n{'all checks passed' if not failures else f'{failures} check(s) FAILED'}")
sys.exit(1 if failures else 0)
