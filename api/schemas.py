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
    is_fined: bool = False
    fine_amount: int | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str
    redis: str


class JobListResponse(BaseModel):
    jobs: list[JobResponse] = Field(default_factory=list)


# Новые схемы для фильтрации по объектам
class ObjectViolationDetail(BaseModel):
    """Информация об одном нарушении"""
    id: str
    timestamp: datetime
    confidence: float
    bbox: list[int]
    image_url: str
    is_fined: bool = False
    fine_amount: int | None = None


class ObjectSummary(BaseModel):
    """Сводка по одному объекту (человеку)"""
    track_id: int
    violation_count: int
    average_confidence: float
    first_violation_time: datetime
    last_violation_time: datetime
    total_fines: int = 0
    violations: list[ObjectViolationDetail] = Field(default_factory=list)


class JobObjectsResponse(BaseModel):
    """Список всех объектов с нарушениями в задаче"""
    job_id: str
    total_objects: int
    total_violations: int
    total_fines: int = 0
    objects: list[ObjectSummary] = Field(default_factory=list)


class ApplyFineRequest(BaseModel):
    """Запрос на применение штрафа"""
    fine_amount: int = Field(..., gt=0, description="Размер штрафа в рублях")
