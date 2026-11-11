import threading
import json
import time
from typing import Optional

from . import client as llm
from ..config import settings
from ..features import FEATURES, Branch, FeatureConfig
from .prompts import SYSTEM_AGENT, SYSTEM_NOTE

def agent_health() -> dict:
    return llm.health()


def agent_startup() -> None:
    """Warm the model in the background so startup isn't blocked."""
    threading.Thread(target=llm.warm_up, daemon=True).start()

def run_agent(feature: str, user_message: str, pinned: dict) -> 