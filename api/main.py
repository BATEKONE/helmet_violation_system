import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import events, health, jobs
from core.settings import get_settings
from storage.database import init_db

settings = get_settings()
settings.ensure_data_dirs()
init_db()

app = FastAPI(
    title="Helmet Violation Detection API",
    version="1.0.0",
    description="API для анализа видео и регистрации нарушений (отсутствие шлема)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(events.router)


@app.get("/")
def root():
    return {
        "service": "helmet-violation-api",
        "docs": "/docs",
        "health": "/health",
    }
