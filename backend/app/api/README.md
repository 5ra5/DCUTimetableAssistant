# Adding an API endpoint

API routes go in `backend/app/api/`. The app in `main.py` adds `/api` to each
router, then serves the frontend. Add your router to `ROUTERS` before the
frontend mount.

The current example is `meta.py`, with `GET /api/health`. For a new feature,
you'll usually:

1. Add a request model in `schema.py`.
2. Make a router file in `api/`.
3. Check that submitted IDs exist.
4. Call the agent with the request values.
5. Register your router in `main.py`.

## 1. Validate the request

Use a Pydantic model for request data. FastAPI will return `422` if validation
fails. `schema.py` has date/time helpers and an example Monday check; add the
rules your feature needs there.

Check that courses, buildings, lecturers, and other IDs exist before calling
the agent. Return `404` for an unknown catalog item. Pass form values to the
agent as `pinned` values so Ollama can't change them.

## 2. Make a router

Here's the basic shape. Replace the example request and feature names with
yours:

```python
from fastapi import APIRouter

from ..agent.engine import run_agent
from ..schema import AgentResult, ExampleRequest

router = APIRouter()


@router.post("/example", response_model=AgentResult)
def example(request: ExampleRequest):
    # Check IDs before calling tools or Ollama.
    pinned = {"building": request.building, "date": request.date}
    message = f"Find the requested info for {request.building} on {request.date}."
    return run_agent("example", message, pinned)
```

This is a pattern, not a drop-in endpoint: define `ExampleRequest` and add the
`"example"` feature first. Use a regular `def` for routes that call the
synchronous agent; FastAPI runs it in a thread pool.

If the student needs to choose between results, return `status="needs_choice"`
and fill in `options`. For example, show lecturer matches and let the student
send the chosen ID in a follow-up request.

## 3. Hook up the router

Import your module and add its router to `ROUTERS` in `main.py`:

```python
from .api import example

ROUTERS = [
    meta.router,
    example.router,
]
```

The app adds `/api`, so `@router.post("/example")` becomes `POST
/api/example`. Don't put `/api` in the route itself.

## 4. Return the expected shape

Agent routes should use the shared `AgentResult` model from `schema.py`:

```json
{
  "status": "ok",
  "summary": "A short answer written by Python.",
  "ai_note": null,
  "facts": {},
  "trace": {}
}
```

The supported statuses are `"ok"`, `"needs_choice"`, `"none"`, and
`"unsupported"`. Add `options` when the student needs to pick something. The
frontend should show `summary` and `facts`; `ai_note` is optional, and it
shouldn't need to read `trace`.

Use `422` for bad input and `404` for unknown IDs, before calling the model. The
agent returns `"unsupported"` if the request asks for info the system doesn't
have. If a tool reports an error, the agent returns `"none"` with an
explanation—don't present it as a successful result.

## 5. Health and startup

`GET /api/health` in `meta.py` checks the app and Ollama. `main.py` warms up the
agent when the app starts. Just register your route; don't start another Ollama
client or warm-up thread in the endpoint.
