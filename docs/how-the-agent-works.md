# How the timetable assistant works

The assistant combines regular Python code with a language model. Python looks
up timetable data, applies the rules, and builds the main answer. The model
helps pick tools and can add a short note, but it doesn't get to make up the
underlying timetable facts.

## Features and tools

Each feature handles one kind of request, such as analysing a week, finding a
room, or looking up a lecturer. A feature is set up with the tools it can use,
which tools must run, and a Python function that turns their results into a
summary.

Tools are ordinary Python functions that fetch or calculate data. For example,
a room-search feature might first check the requested building, then search
nearby buildings if the first search doesn't find enough rooms.

## What happens when you ask a question

1. **The API checks your input.** Invalid data is rejected. Requests for
   information the system doesn't have, such as staff contact details, may be
   declined before they reach the model.
2. **The model is offered that feature's tools.** It can choose tools and fill
   in arguments. The app supplies the actual form values separately, and those
   values take priority over anything the model suggests.
3. **Python runs the required tools.** If the model skips a required tool, or
   Ollama isn't available, Python can still run it from the supplied values.
4. **Python checks whether another search is needed.** The model may suggest
   continuing, but Python's rule makes sure it can't skip a search the feature
   requires. A model suggestion can still cause an extra search.
5. **Python builds the main summary.** The model may also write an optional
   note; the app checks it before showing it.

The language model helps with coordination and wording. Python and the tools
remain responsible for the data and the rules.

## The response

Agent endpoints use a shared response shape:

```json
{
  "status": "ok",
  "summary": "The main answer, built from the tool results.",
  "ai_note": null,
  "facts": {},
  "trace": {}
}
```

- `status` says whether the request succeeded, found nothing, needs a choice,
  or isn't supported.
- `summary` is the main answer.
- `ai_note` is optional and may be `null`.
- `facts` contains the results used to build the answer.
- `options` may be included when you need to choose between matches.
- `trace` records model and tool activity for debugging and evaluation. The
  frontend shouldn't need it to show the answer.

If Ollama is unavailable, the app can still run required tools and build the
Python summary. The optional model note is simply left out.
