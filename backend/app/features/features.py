"""
Feature configs: LLM rules for how to answer a question, which tools to call, and how to summarize the results.

Register your feature in FEATURES below. The agent will call the tools in the order you specify, and then
use your template to summarize the results. If you need to call a second tool based on the result of the first, use a Branch to specify the rule and the second tool.

A FeatureConfig says which tools a feature uses, which of them always run, how the summary text is
built, and an optional Branch: "after tool X, also run tool Y when the rule says so"
(e.g. fewer than 2 free rooms -> also search nearby buildings).
"""
from dataclasses import dataclass
from typing import Callable, Optional

from ..config import settings
from ..tools.registry import * #toolnames here


@dataclass
class Branch:
    after: str                              # run the rule after this tool
    # tool to also run when the rule says more is needed
    next_tool: str
    # the rule, applied to the `after` tool's result
    needs_next: Callable[[dict], bool]


@dataclass
class FeatureConfig:
    tools: list                             # tools this feature may use
    required: list                          # tool names that always run, in order
    template: Callable[[dict], str]         # facts -> summary text
    branch: Optional[Branch] = None



FEATURES = {}
""" example:
FEATURES = {
    "weekly": FeatureConfig(
        tools=[analyze_class_patterns, analyze_free_gaps],
        required=[analyze_class_patterns],
        template=weekly_summary,
        branch=Branch(
            after="analyze_free_gaps",
            next_tool="analyze_nearby_buildings",
            needs_next=lambda facts: facts["free_rooms"] < settings.min_rooms
        )
    )"""