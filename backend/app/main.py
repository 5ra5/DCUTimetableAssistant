"""
App Entrypoint: run with uvicorn backend.app.main:app --reload --port 8080

Adding an endpoint: create api/<name>.py with `router = APIRouter()` and add it to ROUTERS below
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import meta, lecturers # ex: from .api import meta, timetable, weekly
from .agent import agent_startup
from .config import settings

ROUTERS = [
    meta.router,
    lecturers.router
    # timetable.router,
    # weekly.router,
]

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.info("Starting DCU Timetable Assistant backend on port 8080")


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_startup()  # warm up the model in the background.
    yield


app = FastAPI(title="DCU Timetable Assistant",
              version="0.1.0", lifespan=lifespan)
for router in ROUTERS:
    app.include_router(router, prefix="/api")

# Mount frontend on same port as backend
if settings.frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir,
              html=True), name="frontend")
