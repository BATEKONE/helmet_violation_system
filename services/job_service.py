import threading
from pathlib import Path

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from core.settings import get_settings
from storage.repositories import JobRepository


class JobService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = JobRepository(session)
        self.settings = get_settings()
        self.queue = Queue(
            self.settings.rq_queue_name,
            connection=Redis.from_url(self.settings.redis_url),
        )

    def _enqueue(self, job_id: str) -> None:
        if self.settings.inline_worker:
            from workers.tasks import process_job

            thread = threading.Thread(target=process_job, args=(job_id,), daemon=True)
            thread.start()
            return

        self.queue.enqueue(
            "workers.tasks.process_job",
            job_id,
            job_timeout="2h",
            result_ttl=86400,
            failure_ttl=86400,
        )

    def create_from_upload(self, filename: str, data: bytes):
        job = self.repo.create(filename, Path("pending"))
        self.session.flush()

        input_path = self.repo.files.save_upload(job.id, filename, data)
        job.input_path = str(input_path)
        self.session.flush()
        self.session.commit()

        self._enqueue(job.id)
        return job

    def get_job(self, job_id: str):
        return self.repo.get(job_id)

    def list_jobs(self, limit: int = 50):
        return self.repo.list_recent(limit)

    def list_events(self, job_id: str):
        return self.repo.list_events(job_id)
