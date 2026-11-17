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
KEEP_ALIVE = settings.keep_alive


def make_client() -> ollama.Client:
    headers = None
    if settings.use_api_key:
        if not settings.api_key:
            raise RuntimeError(
                "OLLAMA_USE_API_KEY is true but OLLAMA_API_KEY is empty")
        headers = {"Authorization": f"Bearer {settings.api_key}"}
    return ollama.Client(host=settings.ollama_host, headers=headers, timeout=settings.llm_timeout_s)


client = make_client()

def chat(messages: list, tools: list | None = None, fmt: dict | None = None, num_predict: int = 256, think: bool = False):
    """The only place that calls the model. 'fmt' is a JSON schema that forces a JSON answer."""
    log.debug("\n===================================\nCalling Ollama model %s with %d messages, %d tools(%s), num_predict=%d, think=%s\n==============================\n", MODEL, len(messages), len(tools) if tools else 0, ", ".join([f"{tool}" for tool in tools]) if tools else "", num_predict, think)
    resp = client.chat(
        model=MODEL,
        messages=messages,
        tools=tools,
        format=fmt,
        options={**OPTS, "num_predict": num_predict},
        keep_alive=KEEP_ALIVE,
        think=think,
    )
    log.debug("\n============================\nModel Response Message: %s:\nFull Response: %s\n===============================\n", resp.message.content, resp)
    return resp


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
