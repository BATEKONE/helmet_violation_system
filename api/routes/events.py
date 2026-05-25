from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.deps import get_db
from storage.models import ViolationEvent

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/{event_id}/image")
def get_event_image(event_id: str, db: Session = Depends(get_db)):
    event = db.get(ViolationEvent, event_id)
    if event is None:
        raise HTTPException(404, "Событие не найдено")

    path = Path(event.image_path)
    if not path.exists():
        raise HTTPException(404, "Снимок не найден")

    return FileResponse(path, media_type="image/jpeg")
