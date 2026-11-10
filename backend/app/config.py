"""
Settings for the application. Loaded from environment variables and .env file.
Locally: uvicorn backend.app.main:app --reload --port 8080 --env-file .env
"""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] #repo root

def _env(name: str, default: str) -> str:
    """Get environment variable or default value"""
    return os.environ.get(name, default)

@dataclass(frozen=True)
class Settings:
    """Application settings"""

    # --------------------------------------------------
    # Project paths
    # --------------------------------------------------

    ollama_host: str = _env("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = _env("OLLAMA_MODEL", "llama3.2:3b")
    llm_timeout_s: float = float(_env("LLM_TIMEOUT_S", "60.0"))
    min_rooms: int = int(_env("MIN_ROOMS", "2"))
    frontend_dir: Path = ROOT / "frontend"
    
settings = Settings()