"""One shared Ollama client, plus health and warm-up."""
import logging

import ollama

from ..config import settings

log = logging.getLogger(__name__)

# IDENTICAL options on EVERY chat call. Changing num_ctx between calls makes Ollama reload the model, which made early runs take 30-40 s.
OPTS = {"temperature": 0, "num_ctx": 2048}

client = ollama.Client(host=settings.ollama_host, timeout=settings.llm_timeout_s)


def health() -> dict:
    try:
        names = [m.model for m in client.list().models]
        return {"mode": "llm", "ollama": "ok", "model": settings.ollama_model, "model_installed": any(n.startswith(settings.ollama_model) for n in names)}
    except Exception as e:
        return {"mode": "llm", "ollama": "unreachable", "model": settings.ollama_model, "error": str(e)}


def warm_up() -> None:
    """Load the model into RAM so the first student request isn't slow."""
    try:
        log.warning("Warming up Ollama model %s: %s", settings.ollama_model, settings.ollama_host)
        client.chat(model=settings.ollama_model, messages=[{"role": "user", "content": "hi"}], options={**OPTS, "num_predict": 1}, keep_alive="30m")
        log.info("Ollama model %s warmed up", settings.ollama_model)
    except Exception as e:
        log.warning("Ollama warm-up failed: %s", e)
