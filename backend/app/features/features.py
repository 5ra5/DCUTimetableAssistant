"""
Feature configs: which tools a feature uses, how the summary text is built, and (optionally) how the
LLM is prompted for that feature.

Register your feature in FEATURES at the bottom. The engine (agent/engine.py) will:
  1. offer the model only this feature's tools and let it make the first tool call,
  2. run any REQUIRED tool the model skipped (Python never depends on the model's choice),
  3. if there is a Branch: ask the model for a decision, but Python's 'needs_next' rule has the last word,
  4. build 'summary' from your 'template' (always correct, never written by the model),
  5. optionally ask the model for a one-sentence 'ai_note', and keep it only if it passes agent/notes.py.

'facts' is a dict keyed by tool name: {"find_rooms_in_building": <that tool's dict>, ...}.
'template' and 'is_empty' receive these facts. 'needs_next' and 'Decision.question' receive ONE tool's
result (the 'after' tool's dict).
"""
from dataclasses import dataclass
from typing import Callable, Optional

from ..config import settings
from ..tools.registry import (  # noqa: F401  (tool functions are imported here by name)
    weekly_daily_breakdown,
    weekly_class_patterns,
    weekly_free_gaps,
)
from .weekly import daily_summary, gaps_summary, patterns_summary, week_summary, weekly_is_empty


@dataclass
class Decision:
    """How the model is asked whether the Branch should run. Python's rule still decides."""
    continue_action: str                    # JSON action meaning "run next_tool", e.g. "broaden_search"
    # 'after' result -> plain-language question, e.g. "Rooms found: 3. Minimum needed: 2."
    question: Callable[[dict], str]
    # system prompt (state the rule in plain words, say "state the number, then the action")
    system: str


@dataclass
class Branch:
    # run the rule after this tool (must be in 'required')
    after: str
    # tool to also run when the rule says more is needed
    next_tool: str
    # the rule, applied to the 'after' tool's result
    needs_next: Callable[[dict], bool]
    # optional: ask the model too (its answer is only logged)
    decision: Optional[Decision] = None


@dataclass
class FeatureConfig:
    # tool functions this feature may use (the model sees their docstrings)
    tools: list
    required: list                          # tool NAMES that always run, in order
    template: Callable[[dict], str]         # facts -> summary text
    branch: Optional[Branch] = None
    # ---- everything below is optional LLM wording ----
    # ordering hint added to the system prompt, e.g. "Always start with find_rooms_in_building."
    agent_hint: str = ""
    # one-sentence instruction for the ai_note. Empty = no note call for this feature
    note_instruction: str = ""
    # facts -> ask for a note? None = always
    note_when: Optional[Callable[[dict], bool]] = None
    # facts -> words; the note must contain one of them
    note_must_mention: Optional[Callable[[dict], tuple]] = None
    # facts -> True means status "none" (nothing found)
    is_empty: Optional[Callable[[dict], bool]] = None

    def __post_init__(self):
        names = {t.__name__ for t in self.tools}
        missing = [n for n in self.required if n not in names]
        if missing:
            raise ValueError(f"required tools not in tools list: {missing}")
        if self.branch:
            if self.branch.after not in self.required:
                raise ValueError(
                    f"branch.after '{self.branch.after}' must be a required tool")
            if self.branch.next_tool not in names:
                raise ValueError(
                    f"branch.next_tool '{self.branch.next_tool}' not in tools list")


# Feature A: one feature per kind of analysis. features/analysis_options.py maps each menu option to one of these.
# The model is offered all three tools; `required` says which ones must run. A tool the model picks that is not
# required is ignored and logged, and a required tool the model skips is run by Python.
_WEEKLY_TOOLS = [weekly_daily_breakdown,
                 weekly_class_patterns, weekly_free_gaps]


def _weekly_feature(required, template, hint, note):
    return FeatureConfig(
        tools=_WEEKLY_TOOLS, required=required, template=template, is_empty=weekly_is_empty,
        agent_hint=hint, note_instruction=note +
        " Do not give advice or opinions. Use only days, times and numbers from the text.",
    )


FEATURES = {
    "feature_a_daily": _weekly_feature(
        ["weekly_daily_breakdown"], daily_summary,
        "Call weekly_daily_breakdown for the daily class counts and teaching hours.",
        "State ONE fact in a single sentence: how many classes the week has."),
    "feature_a_gaps": _weekly_feature(
        ["weekly_free_gaps", "weekly_daily_breakdown"], gaps_summary,
        "Call weekly_free_gaps for the breaks between classes, and weekly_daily_breakdown.",
        "State ONE fact in a single sentence: the longest gap between classes, with its day and times."),
    "feature_a_patterns": _weekly_feature(
        ["weekly_class_patterns"], patterns_summary,
        "Call weekly_class_patterns for the busiest and lightest days and the earliest start and latest finish.",
        "State ONE fact in a single sentence: which day is the busiest."),
    "feature_a_week": _weekly_feature(
        ["weekly_daily_breakdown", "weekly_class_patterns",
            "weekly_free_gaps"], week_summary,
        "Call all three analysis tools: weekly_daily_breakdown, weekly_class_patterns and weekly_free_gaps.",
        "State ONE fact in a single sentence about the week."),
}

"""example:
FEATURES = {
    "rooms": FeatureConfig(
        tools=[find_rooms_in_building, find_rooms_nearby],
        required=["find_rooms_in_building"],
        template=rooms_summary,
        agent_hint="Always start with find_rooms_in_building for the requested building.",
        branch=Branch(
            after="find_rooms_in_building",
            next_tool="find_rooms_nearby",
            needs_next=lambda r: r["count"] < settings.min_rooms,
            decision=Decision(
                continue_action="broaden_search",
                question=lambda r: f"Rooms found: {r['count']}. Minimum needed: {settings.min_rooms}.",
                system="You decide the next step of a room search. ...",
            ),
        ),
    ),
}"""
