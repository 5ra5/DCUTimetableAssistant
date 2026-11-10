"""
App Entrypoint: run with uvicorn backend.app.main:app --reload --port 8080

Adding an endpoint: create api/<name>.py with `router = APIRouter()` and add it to ROUTERS below
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import * # ex: from .api import timetable, weekly
from .config import settings

ROUTERS = [
# example:
#    timetable.router,
#    weekly.router,
]

app = FastAPI(title="DCU Timetable Assistant", version="0.1.0")
for router in ROUTERS:
    app.include_router(router, prefix="/api")
    
    
# Mount frontend on same port as backend
if settings.frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")