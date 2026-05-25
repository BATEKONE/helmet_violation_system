from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import JobCreateResponse, JobListResponse, JobResponse, ViolationEventResponse
from core.settings import get_settings
from services.job_service import JobService
from storage.models import JobStatus

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


@router.get("/{job_id}/events", response_model=List[ViolationEventResponse])
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
