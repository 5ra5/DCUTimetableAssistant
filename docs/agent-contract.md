# Agent contract

## Response of every agent endpoint (`schema.AgentResult`)

    {"status": "ok" | "needs_choice" | "none" | "unsupported",
     "summary": "...",        built by Python from the feature's template; always correct
     "ai_note": "..." | null, one model sentence, only if it passed agent/notes.py; may be null
     "facts": {tool_name: tool_result, ...},
     "trace": {...},          what the model did and every mistake it made (the evaluators read this)
     "options": [...]}        lecturer search only: the candidates to choose from

The frontend renders `facts` and `summary`, treats `ai_note` as optional and never depends on `trace`.
Bad input -> 422. Unknown course / building / lecturer -> 404 (check this BEFORE calling the agent).

## How `run_agent(feature, user_message, pinned)` behaves

1. **Guard.** A message containing office / email / phone / contact is refused (`status: unsupported`), no model call.
2. **Tool turn.** One model call offering only the feature's tools. Only REQUIRED tools are accepted from the model.
3. **Required tools.** Every tool in `required` runs. Arguments come from `pinned` (the form values) and always
   overwrite what the model sent.
4. **Branch.** The model is asked for a forced-JSON decision (`finish` or `continue_action`). Python's
   `needs_next` rule decides; a disagreement is only logged, so a wrong decision can't add or remove a search.
5. **Summary** from the template. **6. Note**: optional model sentence, kept only if it passes `check_note`.

If Ollama is down, 1 model call is attempted, the rest are skipped, and `facts`/`summary` are identical.

`trace` fields: `llm_ok`, `tool_sources` (`model` | `python` | `model_decision`), `decision`, `errors`,
`timings`, `note_rejected` (`{reason, text}`), `seconds`. Error entries: `python_ran:<tool>`,
`ignored_tool_call:<tool>`, `duplicate_tool_call:<tool>`, `argument_overridden:<tool>.<arg> model=.. pinned=..`,
`argument_missing:<tool>.<arg>`, `unknown_argument:<tool>.<arg>`, `wrong_decision:..`, `decision_invalid:..`,
`llm_unreachable:<step>:..`.

## What a feature provides (`features/features.py`)

- **Tools**: plain functions returning plain dicts, with a Google-style docstring (`Args:` with examples such as
  `GLA.FT`): the docstring is what the model reads. On a bad id return `{"error": "unknown_building"}`, don't raise.
  Parameter names must match the keys of `pinned`.
- **`FeatureConfig`**: `tools`, `required` (tool names), `template(facts) -> str`, optional `branch`
  (`Branch(after, next_tool, needs_next, decision=Decision(...))`), optional `agent_hint`, `note_instruction`,
  `note_when`, `note_must_mention`, `is_empty`. A typo in a tool name raises when the app starts.
- **`facts`** is `{tool_name: result}`. `template` and `is_empty` get that; `needs_next` and `Decision.question`
  get only the `after` tool's result.

## Adding an endpoint

    # api/rooms.py
    router = APIRouter()

    class RoomsRequest(BaseModel):
        building: str; date: str; start_time: str; duration_minutes: int   # names = tool parameter names

    @router.post("/rooms", response_model=AgentResult)
    def rooms(req: RoomsRequest):                       # plain `def`: FastAPI runs it in a thread pool
        ...check the building exists, else raise HTTPException(404)...
        msg = f"Find free rooms in {req.building} on {req.date} at {req.start_time} for {req.duration_minutes} minutes."
        return run_agent("rooms", msg, req.model_dump())

then add `rooms.router` to `ROUTERS` in `main.py`.

## Time rules (all tools)

Tools take and return Dublin local `YYYY-MM-DD` / `HH:MM`. Never add a fixed `+1` hour: 19 to 25 Oct 2026 contains the
clock change. Intervals are half-open. "Next lecture" starts strictly after the requested time.
