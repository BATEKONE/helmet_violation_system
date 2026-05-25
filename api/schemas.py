from datetime import datetime

from pydantic import BaseModel, Field


class JobCreateResponse(BaseModel):
    id: str
    status: str
    original_filename: str
    created_at: datetime


class JobResponse(BaseModel):
    id: str
    status: str
    original_filename: str
    progress: float
    violation_count: int
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    video_url: str | None = None


class ViolationEventResponse(BaseModel):
    id: str
    job_id: str
    track_id: int
    violation: str
    timestamp: datetime
    confidence: float
    bbox: list[int]
    image_url: str


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str
    redis: str


class JobListResponse(BaseModel):
    jobs: list[JobResponse] = Field(default_factory=list)
