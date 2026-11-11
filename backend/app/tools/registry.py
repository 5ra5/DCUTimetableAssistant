"""
The ONE place the rest of the app imports tools from.

Everything above this file (agent, api) imports from here

Two groups:
  AGENT TOOLS   - what the LLM may call. Docstrings are part of the model's prompt.
  CATALOG       - plain data functions for /api/timetable (no LLM involved).
"""
from ..config import settings

""" AGENT TOOLS: functions the LLM may call. Docstrings are part of the model's prompt.
from .weekly import analyze_class_patterns, analyze_free_gaps                       # noqa: F401
"""