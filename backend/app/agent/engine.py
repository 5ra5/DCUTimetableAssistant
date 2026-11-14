"""
Runs a feature's tools and builds its response.

Python controls the data and final decisions. The model can choose tools, suggest
a branch action, and write an optional note. Its suggestions never override the
Python rules or the values supplied by the user.

Flow: reject unsupported questions, run tools, apply any branch rule, build the
summary, then check an optional note.
"""
import inspect
import json
import logging
import threading
import time
from typing import Optional

from . import client as llm
from .guards import UNSUPPORTED_SUMMARY, unsupported_reason
from .notes import check_note
from .prompts import SYSTEM_AGENT, SYSTEM_NOTE
from ..features import FEATURES, Branch
from ..schema import AgentResult

log = logging.getLogger(__name__)

TOOL_TURN_TOKENS = 60
SHORT_TOKENS = 80  # decision and note calls


def agent_health() -> dict:
    return llm.health()


def agent_startup() -> None:
    """Warm the model without delaying app startup."""
    threading.Thread(target=llm.warm_up, daemon=True).start()


def _short(value, limit: int = 80) -> str:
    """repr() of a value, cut to `limit` characters so one bad argument can't bloat the trace."""
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + f"... ({len(text)} chars)"


def _same(a, b) -> bool:
    """Compare values without caring about case or extra spaces."""
    return " ".join(str(a).split()).lower() == " ".join(str(b).split()).lower()


def _build_args(tool, model_args: dict, pinned: dict, errors: list, from_model: bool) -> dict:
    """Keep valid model arguments, then replace them with any user-supplied values."""
    name, params = tool.__name__, inspect.signature(tool).parameters
    args = {}
    for key, value in model_args.items():
        if key in params:
            args[key] = value
        else:
            errors.append(f"unknown_argument:{name}.{key}")
    for key in params:
        if key in pinned:
            if from_model and key not in args:
                errors.append(f"argument_missing:{name}.{key}")
            elif key in args and not _same(args[key], pinned[key]):
                errors.append(
                    f"argument_overridden:{name}.{key} model={_short(args[key])} pinned={_short(pinned[key])}")
            args[key] = pinned[key]
    return args


def _decide(branch: Branch, after_result: dict) -> dict:
    """Ask the model for a branch action in the required JSON shape."""
    d = branch.decision
    question = d.question(after_result)
    schema = {
        "type": "object",
        "properties": {
            "reason": {"type": "string"},
            "action": {"type": "string", "enum": ["finish", d.continue_action]},
        },
        "required": ["reason", "action"],
    }
    resp = llm.chat(
        [{"role": "system", "content": d.system}, {
            "role": "user", "content": question}],
        fmt=schema, num_predict=SHORT_TOKENS,
    )
    data = json.loads(resp.message.content)
    if data.get("action") not in ("finish", d.continue_action):
        raise ValueError(f"bad action {data.get('action')!r}")
    return {"asked": question, "reason": str(data.get("reason", ""))[:300], "action": data["action"]}


def run_agent(feature: str, user_message: str, pinned: dict) -> AgentResult:
    if feature not in FEATURES:
        raise ValueError(f"unknown feature {feature!r}")
    cfg = FEATURES[feature]
    t_start = time.perf_counter()
    errors: list = []
    trace = {"llm_ok": True, "tool_sources": {}, "decision": None, "errors": errors,
             "timings": {}, "note_rejected": None, "seconds": 0.0}

    def finish(**fields) -> AgentResult:
        # set `seconds` BEFORE building the result: pydantic copies the trace dict on construction
        trace["seconds"] = round(time.perf_counter() - t_start, 2)
        return AgentResult(trace=trace, **fields)

    def llm_failed(where: str, exc: Exception) -> None:
        trace["llm_ok"] = False
        errors.append(f"llm_unreachable:{where}:{type(exc).__name__}: {exc}")
        log.warning("Model call failed (%s): %s", where, exc)

    # Refuse unsupported questions before they reach the model.
    word = unsupported_reason(user_message)
    if word:
        trace["guard"] = word
        trace["llm_ok"] = None   # never asked
        return finish(status="unsupported", summary=UNSUPPORTED_SUMMARY, facts={})

    tools = {t.__name__: t for t in cfg.tools}

    # Offer only the tools for this feature.
    calls = []
    system = SYSTEM_AGENT + (" " + cfg.agent_hint if cfg.agent_hint else "")
    t0 = time.perf_counter()
    try:
        resp = llm.chat(
            [{"role": "system", "content": system}, {
                "role": "user", "content": user_message}],
            tools=cfg.tools, num_predict=TOOL_TURN_TOKENS,
        )
        calls = resp.message.tool_calls or []
    except Exception as e:
        llm_failed("tool_turn", e)
    trace["timings"]["tool_turn"] = round(time.perf_counter() - t0, 2)

    # Run every required tool; ignore optional or duplicate model calls.
    model_calls = {}
    for call in calls:
        name = call.function.name
        if name not in cfg.required:
            errors.append(f"ignored_tool_call:{name}")
        elif name in model_calls:
            errors.append(f"duplicate_tool_call:{name}")
        else:
            model_calls[name] = dict(call.function.arguments or {})

    results: dict = {}
    for name in cfg.required:
        from_model = name in model_calls
        if not from_model and trace["llm_ok"]:
            errors.append(f"python_ran:{name}")
        args = _build_args(tools[name], model_calls.get(
            name, {}), pinned, errors, from_model)
        results[name] = tools[name](**args)
        trace["tool_sources"][name] = "model" if from_model else "python"

    # branch: the model decides; Python enforces the minimum (the rule) so a wrong "finish" can't break it
    branch = cfg.branch
    if branch and "error" not in results[branch.after]:
        after_result = results[branch.after]
        # the rule: next tool is REQUIRED
        needs = bool(branch.needs_next(after_result))
        model_continue = False                             # what the model chose
        if branch.decision and trace["llm_ok"]:
            t0 = time.perf_counter()
            try:
                decision = _decide(branch, after_result)
                model_continue = decision["action"] == branch.decision.continue_action
                decision["agreed"] = model_continue == needs
                trace["decision"] = decision
                if not decision["agreed"]:
                    outcome = "overridden" if needs else "honoured"
                    errors.append(
                        f"wrong_decision:model said {decision['action']}, rule needs_next={needs} ({outcome})")
            except (ValueError, KeyError, TypeError, AttributeError) as e:   # includes bad JSON
                errors.append(f"decision_invalid:{type(e).__name__}: {e}")
            except Exception as e:
                llm_failed("decision", e)
            trace["timings"]["branch"] = round(time.perf_counter() - t0, 2)
        if model_continue or needs:
            results[branch.next_tool] = tools[branch.next_tool](
                **_build_args(tools[branch.next_tool], {}, pinned, errors, False))
            trace["tool_sources"][branch.next_tool] = "model_decision" if model_continue else "python"

    facts = dict(results)

    # Tools return errors as data; stop here instead of building a normal response.
    failed = [f"{n}: {r['error']}" for n,
              r in facts.items() if isinstance(r, dict) and "error" in r]
    if failed:
        return finish(status="none", summary="The search could not be completed (" + "; ".join(failed) + ").", facts=facts)

    # The summary comes from Python, not the model.
    summary = cfg.template(facts)
    status = "none" if (cfg.is_empty and cfg.is_empty(facts)) else "ok"

    # Keep a model-written note only if it passes the checks.
    note: Optional[str] = None
    wants_note = cfg.note_instruction and (
        cfg.note_when is None or cfg.note_when(facts))
    if wants_note and trace["llm_ok"]:
        t0 = time.perf_counter()
        try:
            resp = llm.chat(
                [{"role": "system", "content": SYSTEM_NOTE +
                    cfg.note_instruction}, {"role": "user", "content": summary}],
                num_predict=SHORT_TOKENS,
            )
            text = (resp.message.content or "").strip().strip('"').strip()
            must = cfg.note_must_mention(
                facts) if cfg.note_must_mention else ()
            reason = check_note(text, summary, facts, must)
            if reason:
                trace["note_rejected"] = {"reason": reason, "text": text}
                log.warning("ai_note rejected (%s): %s", reason, text)
            else:
                note = text
        except Exception as e:
            llm_failed("note", e)
        trace["timings"]["note"] = round(time.perf_counter() - t0, 2)

    return finish(status=status, summary=summary, ai_note=note, facts=facts)
