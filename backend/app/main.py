"""
App Entrypoint: run with uvicorn backend.app.main:app --reload --port 8080

Adding an endpoint: create api/<name>.py with `router = APIRouter()` and add it to ROUTERS below
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import * # ex: from .api import timetable, weekly
from .agent import agent_startup
from .config import settings

ROUTERS = [
# example:
#    timetable.router,
#    weekly.router,
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_startup()  # warm up the model in the background.
    yield


app = FastAPI(title="DCU Timetable Assistant", version="0.1.0", lifespan=lifespan)
for router in ROUTERS:
    app.include_router(router, prefix="/api")

# Mount frontend on same port as backend
if settings.frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")