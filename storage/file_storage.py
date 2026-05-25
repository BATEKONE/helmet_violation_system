import shutil
from pathlib import Path

from core.settings import get_settings


class JobFileStorage:
    def __init__(self):
        settings = get_settings()
        self.jobs_dir = settings.jobs_dir

    def job_dir(self, job_id: str) -> Path:
        path = self.jobs_dir / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_upload(self, job_id: str, filename: str, data: bytes) -> Path:
        job_path = self.job_dir(job_id)
        suffix = Path(filename).suffix or ".mp4"
        input_path = job_path / f"input{suffix}"
        input_path.write_bytes(data)
        return input_path

    def output_video_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "output.mp4"

    def images_dir(self, job_id: str) -> Path:
        path = self.job_dir(job_id) / "images"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_event_image(self, job_id: str, name: str, data: bytes) -> Path:
        path = self.images_dir(job_id) / name
        path.write_bytes(data)
        return path

    def delete_job_files(self, job_id: str) -> None:
        job_path = self.jobs_dir / job_id
        if job_path.exists():
            shutil.rmtree(job_path, ignore_errors=True)
