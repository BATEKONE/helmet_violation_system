from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.event_sink import ViolationRecord
from storage.file_storage import JobFileStorage
from storage.models import Job, JobStatus, ViolationEvent


class JobRepository:
    def __init__(self, session: Session):
        self.session = session
        self.files = JobFileStorage()

    def create(self, original_filename: str, input_path: Path) -> Job:
        job = Job(
            original_filename=original_filename,
            input_path=str(input_path),
            status=JobStatus.QUEUED.value,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get(self, job_id: str) -> Job | None:
        return self.session.get(Job, job_id)

    def list_recent(self, limit: int = 50) -> list[Job]:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def mark_running(self, job: Job) -> None:
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.utcnow()
        job.progress = 0.0
        self.session.flush()

    def update_progress(self, job: Job, progress: float) -> None:
        job.progress = min(max(progress, 0.0), 1.0)
        self.session.flush()

    def mark_completed(
        self,
        job: Job,
        output_path: Path,
        violations: list[ViolationRecord],
    ) -> None:
        job.status = JobStatus.COMPLETED.value
        job.output_path = str(output_path)
        job.finished_at = datetime.utcnow()
        job.progress = 1.0
        job.violation_count = len(violations)

        for record in violations:
            if not record.image_bytes:
                continue
            image_path = self.files.save_event_image(
                job.id,
                record.image_name or f"{record.track_id}.jpg",
                record.image_bytes,
            )
            event = ViolationEvent(
                job_id=job.id,
                track_id=record.track_id,
                violation=record.violation,
                timestamp=record.timestamp,
                confidence=record.confidence,
                bbox=record.bbox,
                image_path=str(image_path),
            )
            self.session.add(event)

        self.session.flush()

    def mark_failed(self, job: Job, error: str) -> None:
        job.status = JobStatus.FAILED.value
        job.error_message = error[:4000]
        job.finished_at = datetime.utcnow()
        self.session.flush()

    def list_events(self, job_id: str) -> list[ViolationEvent]:
        job = self.get(job_id)
        if job is None:
            return []
        return list(job.events)
