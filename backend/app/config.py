"""
Settings for the application. Loaded from environment variables and .env file.
Locally: uvicorn backend.app.main:app --reload --port 8080 --env-file .env
"""

import os
import dotenv
from dataclasses import dataclass
from pathlib import Path
import logging

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]  # repo root


def _env(name: str, default: str) -> str:
    """Get environment variable or default value"""
    env_value = os.environ.get(name, default)
    log.debug("Setting %s=%s", name, env_value)
    return env_value


@dataclass(frozen=True)
class Settings:
    """Application settings"""

    # --------------------------------------------------
    # Project paths
    # --------------------------------------------------

    port: int = int(_env("PORT", "8080"))
    ollama_host: str = _env("OLLAMA_HOST", "http://ollama:11434")
    ollama_model: str = _env("OLLAMA_MODEL", "llama3.2:3b")
    llm_timeout_s: float = float(_env("LLM_TIMEOUT_S", "60.0"))
    frontend_dir: Path = ROOT / "frontend"
    db_path: Path = ROOT / _env("DB_PATH", "data/timetable.db")
    db_time_format: str = _env("DB_TIME_FORMAT", "%Y-%m-%dT%H:%M:%SZ")
    log_level: str = _env("LOG_LEVEL", "INFO").upper()

    api_key: str = _env("OLLAMA_API_KEY", "")
    use_api_key: bool = _env("OLLAMA_USE_API_KEY", "false").lower() == "true"

    tool_turn_tokens: int = int(_env("TOOL_TURN_TOKENS", "512"))
    max_tool_turns: int = int(_env("MAX_TOOL_TURNS", 4))
    short_tokens: int = int(_env("SHORT_TOKENS", 80))
    keep_alive: str = _env("KEEP_MODEL_ALIVE_FOR", "30m")
    min_rooms: int = int(_env("MIN_ROOMS", "2"))
    max_rooms_per_building: int = int(_env("MAX_ROOMS_PER_BUILDING", "6"))
    max_search_metres: int = int(_env("NEARBY_MAX_METRES", "200"))
    min_room_duration_minutes: int = int(_env("MIN_DURATION_MINUTES", "30"))
    max_room_duration_minutes: int = int(_env("MAX_DURATION_MINUTES", "240"))

settings = Settings()
