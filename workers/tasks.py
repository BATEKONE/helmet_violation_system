from datetime import datetime
from pathlib import Path

from core.event_sink import MemoryEventSink
from core.pipeline import VideoPipeline
from core.settings import get_settings
from storage.database import _get_session_factory, init_db
from storage.models import Job
from storage.repositories import JobRepository


def process_job(job_id: str) -> dict:
    init_db()
    settings = get_settings()
    session = _get_session_factory()()

    try:
        repo = JobRepository(session)
        job = repo.get(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        repo.mark_running(job)
        session.commit()

        input_path = Path(job.input_path)
        output_path = repo.files.output_video_path(job_id)

        sink = MemoryEventSink(settings.event_cooldown_sec)
        pipeline = VideoPipeline(event_sink=sink)

        def on_progress(value: float):
            job_row = session.get(Job, job_id)
            if job_row:
                job_row.progress = min(max(value, 0.0), 1.0)
                session.commit()

        result = pipeline.run(input_path, output_path, progress_callback=on_progress)

        job = repo.get(job_id)
        repo.mark_completed(job, result.output_path, result.violations)
        session.commit()

        return {
            "job_id": job_id,
            "status": "completed",
            "violations": len(result.violations),
            "output": str(result.output_path),
        }
    except Exception as exc:
        session.rollback()
        session2 = _get_session_factory()()
        try:
            repo = JobRepository(session2)
            job = repo.get(job_id)
            if job:
                repo.mark_failed(job, str(exc))
                session2.commit()
        finally:
            session2.close()
        raise
    finally:
        session.close()
