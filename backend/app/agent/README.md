# Adding an agent feature

The agent connects a feature's tools to its API endpoint. Python runs the tools,
applies the real rules, and writes the main summary. Ollama can pick tools,
suggest an extra search, and add an optional note.

## Where things live

- `features/features.py` - feature setup and the `FEATURES` list.
- `tools/registry.py` - tools available to features.
- `agent/engine.py` - runs tools and builds the response.
- `agent/client.py` - shared Ollama client and settings.
- `agent/guards.py` - requests we refuse before asking Ollama.
- `agent/notes.py` - checks optional notes before showing them.
- `schema.py` - shared response model, `AgentResult`.

Want to see the whole flow working? Check
[`scripts/try_agent.py`](../../../scripts/try_agent.py). It adds a temporary
feature at runtime, so it doesn't change the normal feature list.

## 1. Add your tools

Tools are regular Python functions. Add or import them through
`tools/registry.py`. The model sees each tool's name, arguments, and docstring,
so keep those clear and include a useful argument example.

Return plain dictionaries. For expected lookup problems, return something like
`{"error": "unknown_building"}`. If a tool result has an `"error"` key, the
engine stops and returns a `"none"` response.

Keep database queries and timetable calculations in the tools/data layer. The
agent's job is to connect the pieces, not redo their work.

## 2. Add your feature

Add a `FeatureConfig` to `FEATURES` in `features/features.py`. `tools` is a list
of tool functions; `required` is a list of their names.

```python
FEATURES["example"] = FeatureConfig(
    tools=[find_example, find_example_wider],
    required=["find_example"],
    template=example_summary,
    agent_hint="Start with find_example.",
    branch=Branch(
        after="find_example",
        next_tool="find_example_wider",
        needs_next=lambda result: result["count"] < 2,
    ),
)
```

Swap in your real tools and summary. For a branch:

- `after` must be a required tool.
- `next_tool` must be in `tools`.
- `needs_next` gets the first tool's result and returns `True` or `False`.
- If `needs_next` is true, Python runs the next tool. If the model suggests
  continuing, the engine also runs it—even if the Python rule says no. The model
  can't make Python skip a search the rule requires, but it can trigger an
  extra one.
- Add `Decision` if you want to ask the model for a structured suggestion.
  Without it, only the Python rule is used.

Other `FeatureConfig` options:

- `agent_hint`: a hint about which tool to call first.
- `note_instruction`: turns on the optional `ai_note` call. Leave it empty to
  skip the call.
- `note_when(facts)`: choose when to ask for a note.
- `note_must_mention(facts)`: words the note must include.
- `is_empty(facts)`: return `True` when the result should have status `"none"`.

`template(facts)` writes the main summary. `facts` is a dictionary of tool
results, keyed by tool name. Keep the important answer in the summary; notes are
optional and can be rejected.

## 3. Pass the request to the agent

Your endpoint calls:

```python
run_agent(feature, user_message, pinned)
```

- `feature` is the key you added to `FEATURES`.
- `user_message` is the student's request. Ollama uses it to pick tools, and
  the guard checks it before any model call.
- `pinned` holds trusted form values, with keys matching tool arguments.

Pinned values always win over model arguments. The engine logs missing,
unexpected, or changed arguments in `trace.errors`. Include all the values
needed to run your tools in `pinned`, so the feature still works if Ollama is
down or skips a tool.

The guard currently blocks questions about staff offices and contact details.
If the data or policy changes, update `agent/guards.py` too.

## 4. Response and checks

`AgentResult` has:

- `status`: `"ok"`, `"none"`, `"unsupported"`, or `"needs_choice"`.
- `summary`: the Python-written answer.
- `ai_note`: an optional model-written sentence; may be `null`.
- `facts`: tool results.
- `trace`: model status, tool sources, decisions, errors, and timings.
- `options`: optional choices, such as lecturer matches.

The engine creates `"ok"`, `"none"`, and `"unsupported"` responses.
`"needs_choice"` and `options` are available for endpoints that need the
student to choose a result.

The model never writes the main summary. `check_note` catches common note
problems, but it can't prove every sentence is true—treat `summary` and `facts`
as the actual answer.

## 5. Try it out

From the repo root, run:

```bash
docker compose -f compose.yaml  -f ollama.compose.yaml up -d --build
docker compose exec app python scripts/try_agent.py GLA.FT 100
```

The example uses the real engine, database, and Ollama. It prints the result,
tool calls, model decision, errors, and timings, then checks the first tool's
facts against a direct call. It needs the database and Ollama/model set up; see
the script's opening notes.

When testing your feature, try both sides of any branch, missing or wrong model
tool calls, bad arguments, Ollama being down, tool errors, and rejected notes.
