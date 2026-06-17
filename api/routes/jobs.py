from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import (
    ApplyFineRequest,
    JobCreateResponse,
    JobListResponse,
    JobObjectsResponse,
    JobResponse,
    ObjectSummary,
    ObjectViolationDetail,
    ViolationEventResponse,
)
from core.settings import get_settings
from services.job_service import JobService
from storage.models import JobStatus, ViolationEvent

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _job_response(job, base_url: str) -> JobResponse:
    video_url = None
    if job.status == JobStatus.COMPLETED.value and job.output_path:
        video_url = f"{base_url}/api/v1/jobs/{job.id}/video"
    return JobResponse(
        id=job.id,
        status=job.status,
        original_filename=job.original_filename,
        progress=job.progress,
        violation_count=job.violation_count,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        video_url=video_url,
    )


@router.post("", response_model=JobCreateResponse, status_code=201)
async def create_job(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "Имя файла обязательно")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Пустой файл")

    service = JobService(db)
    job = service.create_from_upload(file.filename, data)
    db.commit()

    return JobCreateResponse(
        id=job.id,
        status=job.status,
        original_filename=job.original_filename,
        created_at=job.created_at,
    )


@router.get("", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)):
    settings = get_settings()
    service = JobService(db)
    jobs = service.list_jobs()
    return JobListResponse(
        jobs=[_job_response(j, settings.api_public_url) for j in jobs]
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    settings = get_settings()
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")
    return _job_response(job, settings.api_public_url)


@router.get("/{job_id}/events", response_model=list[ViolationEventResponse])
def list_job_events(job_id: str, db: Session = Depends(get_db)):
    settings = get_settings()
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")

    events = service.list_events(job_id)
    return [
        ViolationEventResponse(
            id=e.id,
            job_id=e.job_id,
            track_id=e.track_id,
            violation=e.violation,
            timestamp=e.timestamp,
            confidence=e.confidence,
            bbox=e.bbox,
            image_url=f"{settings.api_public_url}/api/v1/events/{e.id}/image",
            is_fined=e.is_fined,
            fine_amount=e.fine_amount,
        )
        for e in events
    ]


@router.get("/{job_id}/video")
def download_job_video(job_id: str, db: Session = Depends(get_db)):
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(404, "Видео ещё не готово")

    return FileResponse(
        job.output_path,
        media_type="video/mp4",
        filename=f"helmet_analysis_{job_id}.mp4",
    )


@router.get("/{job_id}/objects", response_model=JobObjectsResponse)
def list_job_objects(job_id: str, db: Session = Depends(get_db)):
    """Получить все объекты (людей) с нарушениями, сгруппированные по track_id"""
    settings = get_settings()
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")

    # Получаем все события, сгруппированные по track_id
    events = db.query(ViolationEvent).filter(
        ViolationEvent.job_id == job_id
    ).all()

    if not events:
        return JobObjectsResponse(
            job_id=job_id,
            total_objects=0,
            total_violations=0,
            total_fines=0,
            objects=[],
        )

    # Группируем события по track_id
    objects_dict = {}
    total_fines = 0

    for event in events:
        if event.track_id not in objects_dict:
            objects_dict[event.track_id] = []
        objects_dict[event.track_id].append(event)
        if event.is_fined and event.fine_amount:
            total_fines += event.fine_amount

    # Строим список объектов с их деталями
    objects_list = []
    for track_id, track_events in objects_dict.items():
        violations = [
            ObjectViolationDetail(
                id=e.id,
                timestamp=e.timestamp,
                confidence=e.confidence,
                bbox=e.bbox,
                image_url=f"{settings.api_public_url}/api/v1/events/{e.id}/image",
                is_fined=e.is_fined,
                fine_amount=e.fine_amount,
            )
            for e in track_events
        ]

        confidences = [e.confidence for e in track_events]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        timestamps = [e.timestamp for e in track_events]
        track_total_fines = sum(
            e.fine_amount for e in track_events if e.is_fined and e.fine_amount
        )

        obj = ObjectSummary(
            track_id=track_id,
            violation_count=len(track_events),
            average_confidence=avg_confidence,
            first_violation_time=min(timestamps),
            last_violation_time=max(timestamps),
            total_fines=track_total_fines,
            violations=violations,
        )
        objects_list.append(obj)

    # Сортируем по времени последнего нарушения (новые в начале)
    objects_list.sort(key=lambda x: x.last_violation_time, reverse=True)

    return JobObjectsResponse(
        job_id=job_id,
        total_objects=len(objects_list),
        total_violations=len(events),
        total_fines=total_fines,
        objects=objects_list,
    )


@router.get("/{job_id}/objects/{track_id}", response_model=ObjectSummary)
def get_object_violations(job_id: str, track_id: int, db: Session = Depends(get_db)):
    """Получить все нарушения конкретного объекта (человека) по track_id"""
    settings = get_settings()
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")

    events = db.query(ViolationEvent).filter(
        ViolationEvent.job_id == job_id,
        ViolationEvent.track_id == track_id,
    ).all()

    if not events:
        raise HTTPException(404, f"Объект с track_id={track_id} не найден")

    violations = [
        ObjectViolationDetail(
            id=e.id,
            timestamp=e.timestamp,
            confidence=e.confidence,
            bbox=e.bbox,
            image_url=f"{settings.api_public_url}/api/v1/events/{e.id}/image",
            is_fined=e.is_fined,
            fine_amount=e.fine_amount,
        )
        for e in events
    ]

    confidences = [e.confidence for e in events]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    timestamps = [e.timestamp for e in events]
    total_fines = sum(
        e.fine_amount for e in events if e.is_fined and e.fine_amount
    )

    return ObjectSummary(
        track_id=track_id,
        violation_count=len(events),
        average_confidence=avg_confidence,
        first_violation_time=min(timestamps),
        last_violation_time=max(timestamps),
        total_fines=total_fines,
        violations=violations,
    )


@router.post("/{job_id}/objects/{track_id}/apply-fine")
def apply_fine_to_object(
    job_id: str,
    track_id: int,
    request: ApplyFineRequest,
    db: Session = Depends(get_db),
):
    """Применить штраф ко всем нарушениям объекта"""
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")

    events = db.query(ViolationEvent).filter(
        ViolationEvent.job_id == job_id,
        ViolationEvent.track_id == track_id,
    ).all()

    if not events:
        raise HTTPException(404, f"Объект с track_id={track_id} не найден")

    # Применяем штраф ко всем событиям
    for event in events:
        event.is_fined = True
        event.fine_amount = request.fine_amount

    db.commit()

    return {
        "message": f"Штраф {request.fine_amount}₽ применен к {len(events)} нарушениям",
        "track_id": track_id,
        "violations_fined": len(events),
        "total_fine": request.fine_amount * len(events),
    }
