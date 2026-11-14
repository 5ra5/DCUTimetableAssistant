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

    ollama_host: str = _env("OLLAMA_HOST", "http://ollama:11434")
    ollama_model: str = _env("OLLAMA_MODEL", "llama3.2:3b")
    llm_timeout_s: float = float(_env("LLM_TIMEOUT_S", "60.0"))
    min_rooms: int = int(_env("MIN_ROOMS", "2"))
    frontend_dir: Path = ROOT / "frontend"
    # DB_PATH in .env / compose may be relative (data/timetable.db); resolve it against the repo root, not the cwd
    db_path: Path = ROOT / _env("DB_PATH", "data/timetable.db")
    log_level: str = _env("LOG_LEVEL", "INFO").upper()


settings = Settings()
