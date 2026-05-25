from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from api.schemas import HealthResponse
from core.settings import get_settings
from storage.database import _get_engine

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health():
    db_status = "ok"
    redis_status = "ok"
    settings = get_settings()

    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        Redis.from_url(settings.redis_url).ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return HealthResponse(status=overall, database=db_status, redis=redis_status)
