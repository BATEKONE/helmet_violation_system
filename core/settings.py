from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = ROOT / "data"
    database_url: str = f"sqlite:///{ROOT / 'data' / 'helmet.db'}"
    redis_url: str = "redis://127.0.0.1:6379/0"
    rq_queue_name: str = "helmet_jobs"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_public_url: str = "http://127.0.0.1:8000"
    inline_worker: bool = False

    conf_threshold: float = 0.4
    event_cooldown_sec: float = 5.0
    temporal_window: int = 10

    model_candidates: list[str] = [
        "runs/helmet_detector/weights/best.pt",
        "runs/helmet_detector2/weights/best.pt",
        "runs/helmet_detector3/weights/best.pt",
    ]
    default_base_weights: str = "yolov8s.pt"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    def resolve_model_path(self) -> Path:
        for rel in self.model_candidates:
            candidate = ROOT / rel
            if candidate.exists():
                return candidate

        runs_dir = ROOT / "runs"
        if runs_dir.exists():
            for weights in sorted(runs_dir.glob("helmet_detector*/weights/best.pt")):
                return weights

        return ROOT / self.default_base_weights

    def ensure_data_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
