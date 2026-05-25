from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2

from core.cooldown import can_create_event


@dataclass
class ViolationRecord:
    track_id: int
    violation: str
    timestamp: datetime
    confidence: float
    bbox: list[int]
    image_bytes: bytes | None = None
    image_name: str | None = None


class EventSink(ABC):
    @abstractmethod
    def emit(self, frame, violation: dict) -> ViolationRecord | None:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    def get_records(self) -> list[ViolationRecord]:
        return []


class MemoryEventSink(EventSink):
    def __init__(self, cooldown_sec: float):
        self._cooldown_sec = cooldown_sec
        self._records: list[ViolationRecord] = []

    def reset(self) -> None:
        self._records.clear()

    def emit(self, frame, violation: dict) -> ViolationRecord | None:
        track_id = violation["track_id"]
        if not can_create_event(track_id):
            return None

        x1, y1, x2, y2 = map(int, violation["bbox"])
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        timestamp = datetime.now()
        file_time = timestamp.strftime("%Y%m%d_%H%M%S")
        image_name = f"{track_id}_{file_time}.jpg"

        ok, encoded = cv2.imencode(".jpg", crop)
        image_bytes = encoded.tobytes() if ok else None

        record = ViolationRecord(
            track_id=track_id,
            violation="NO_HELMET",
            timestamp=timestamp,
            confidence=round(float(violation.get("confidence", 0)), 3),
            bbox=[x1, y1, x2, y2],
            image_bytes=image_bytes,
            image_name=image_name,
        )
        self._records.append(record)
        return record

    def get_records(self) -> list[ViolationRecord]:
        return list(self._records)


class FileEventSink(EventSink):
    def __init__(self, images_dir: Path, json_dir: Path, cooldown_sec: float):
        self.images_dir = images_dir
        self.json_dir = json_dir
        self._cooldown_sec = cooldown_sec
        self._records: list[ViolationRecord] = []
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)

    def reset(self) -> None:
        self._records.clear()
        for folder in (self.images_dir, self.json_dir):
            for item in folder.iterdir():
                if item.is_file():
                    item.unlink()

    def emit(self, frame, violation: dict) -> ViolationRecord | None:
        import json

        track_id = violation["track_id"]
        if not can_create_event(track_id):
            return None

        x1, y1, x2, y2 = map(int, violation["bbox"])
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        timestamp = datetime.now()
        file_time = timestamp.strftime("%Y%m%d_%H%M%S")
        image_name = f"{track_id}_{file_time}.jpg"
        json_name = f"{track_id}_{file_time}.json"

        image_path = self.images_dir / image_name
        json_path = self.json_dir / json_name
        cv2.imwrite(str(image_path), crop)

        data = {
            "track_id": track_id,
            "violation": "NO_HELMET",
            "timestamp": timestamp.isoformat(),
            "confidence": round(float(violation.get("confidence", 0)), 3),
            "bbox": [x1, y1, x2, y2],
            "image": image_name,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        record = ViolationRecord(
            track_id=track_id,
            violation="NO_HELMET",
            timestamp=timestamp,
            confidence=data["confidence"],
            bbox=data["bbox"],
            image_name=image_name,
        )
        self._records.append(record)
        return record

    def get_records(self) -> list[ViolationRecord]:
        return list(self._records)
