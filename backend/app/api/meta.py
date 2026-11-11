"""GET /api/health - is the app up, and can it reach Ollama"""
from fastapi import APIRouter

from ..agent import agent_health

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "agent": agent_health()}
