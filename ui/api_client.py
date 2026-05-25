import os
import time
from pathlib import Path

import httpx

DEFAULT_API_URL = os.getenv("HELMET_API_URL", "http://127.0.0.1:8000")


class HelmetApiClient:
    def __init__(self, base_url: str = DEFAULT_API_URL, timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> dict:
        with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
            response = client.get("/health")
            response.raise_for_status()
            return response.json()

    def create_job(self, file_path: Path, filename: str) -> dict:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            with open(file_path, "rb") as f:
                response = client.post(
                    "/api/v1/jobs",
                    files={"file": (filename, f, "application/octet-stream")},
                )
            response.raise_for_status()
            return response.json()

    def get_job(self, job_id: str) -> dict:
        with httpx.Client(base_url=self.base_url, timeout=30.0) as client:
            response = client.get(f"/api/v1/jobs/{job_id}")
            response.raise_for_status()
            return response.json()

    def list_events(self, job_id: str) -> list:
        with httpx.Client(base_url=self.base_url, timeout=30.0) as client:
            response = client.get(f"/api/v1/jobs/{job_id}/events")
            response.raise_for_status()
            return response.json()

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: float = 1.0,
        progress_callback=None,
    ) -> dict:
        while True:
            job = self.get_job(job_id)
            if progress_callback:
                progress_callback(job.get("progress", 0.0), job.get("status"))

            if job["status"] in ("completed", "failed"):
                return job

            time.sleep(poll_interval)

    def download_video(self, job_id: str) -> bytes:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.get(f"/api/v1/jobs/{job_id}/video")
            response.raise_for_status()
            return response.content

    def download_image(self, image_url: str) -> bytes:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(image_url)
            response.raise_for_status()
            return response.content
