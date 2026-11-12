"""One shared Ollama client + health and warm-up.

Every model call in the app goes through chat() so the options are identical every time.
Changing num_ctx between calls makes Ollama reload the model, which made early runs take 30-40 s.
"""
import logging

import ollama

from ..config import settings

log = logging.getLogger(__name__)

MODEL = settings.ollama_model
OPTS = {"temperature": 0, "num_ctx": 2048}
KEEP_ALIVE = "30m"

client = ollama.Client(host=settings.ollama_host,
                       timeout=settings.llm_timeout_s)


def chat(messages: list, tools: list | None = None, fmt: dict | None = None, num_predict: int = 80):
    """The only place that calls the model. 'fmt' is a JSON schema that forces a JSON answer."""
    return client.chat(
        model=MODEL,
        messages=messages,
        tools=tools,
        format=fmt,
        options={**OPTS, "num_predict": num_predict},
        keep_alive=KEEP_ALIVE,
    )


def health() -> dict:
    try:
        names = [m.model for m in client.list().models]
        return {"ollama": "ok", "host": settings.ollama_host, "model": MODEL, "model_installed": any(n.startswith(MODEL) for n in names)}
    except Exception as e:
        return {"ollama": "unreachable", "host": settings.ollama_host, "model": MODEL, "error": str(e)}


def warm_up() -> None:
    """Load the model into RAM so the first student request isn't slow."""
    try:
        log.info("Warming up Ollama model %s at %s",
                    MODEL, settings.ollama_host)
        chat([{"role": "user", "content": "hi"}], num_predict=1)
        log.info("Ollama model %s warmed up", MODEL)
    except Exception as e:
        log.warning("Ollama warm-up failed: %s", e)
