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
from .summaryC import lecturer_summary_A, lecturer_summary_B
from ..tools.registry import *  # noqa: F401,F403  (tool functions are imported here by name)
from ..tools.featureCtools import get_lecturer_schedule, search_lecturer, find_next_lecturer


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

FEATURES = {}

FEATURES["feature_C_A"] = FeatureConfig(
    tools=[get_lecturer_schedule, find_next_lecturer],
    required=["get_lecturer_schedule"],
    template=lecturer_summary_A,
    agent_hint="Always check the exact schedule using get_lecturer_schedule first then use find_next_lecturer as a fallback if none is found",
    branch=Branch(
        after="get_lecturer_schedule",
        next_tool="find_next_lecturer",
        needs_next=lambda r: r.get("status") != "success",
        decision=Decision(
            continue_action="find_next_lecture",
            question=lambda r: f"Lecturer schedule found: {r.get('status')}. Minimum needed: success.",
            system=f"You decide the next step of a lecturer search. The student needs at least one successful schedule. If the student has a successful schedule, the action is immediately 'finish'."
        )
    ),

    is_empty=lambda facts: (facts.get("get_lecturer_schedule", {}).get("status") != "success" and
                    facts.get("find_next_lecturer", {}).get("status") != "success"
                    ),

        
)

FEATURES["feature_C_B"] = FeatureConfig(
    tools=[search_lecturer],
    required=["search_lecturer"],
    template=lecturer_summary_B,
    agent_hint="Search for the requested lecturer name using search_lecturer.",
    is_empty=lambda facts: (facts.get("search_lecturer", {}).get("status") != "success"),

)

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
