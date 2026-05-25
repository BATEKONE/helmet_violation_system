from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
from ultralytics import YOLO

from core.association import associate_objects
from core.cooldown import reset_cooldowns
from core.detection_parser import parse_detections
from core.event_sink import EventSink, MemoryEventSink, ViolationRecord
from core.settings import get_settings
from core.temporal import reset_history
from core.tracker import update_tracks
from core.violation import detect_violations
from core.video_export import finalize_video_for_web
from core.visualization import draw_scene

_model = None


def get_model() -> YOLO:
    global _model
    if _model is None:
        settings = get_settings()
        model_path = settings.resolve_model_path()
        if not model_path.exists():
            raise FileNotFoundError(
                f"Файл модели не найден: {model_path}. "
                "Сначала обучите модель: python training/train_yolo.py"
            )
        _model = YOLO(str(model_path))
    return _model


def reset_model() -> None:
    global _model
    _model = None


@dataclass
class PipelineResult:
    output_path: Path
    violations: list[ViolationRecord]
    frames_processed: int


class VideoPipeline:
    def __init__(self, event_sink: EventSink | None = None):
        settings = get_settings()
        self.conf_threshold = settings.conf_threshold
        self.event_sink = event_sink or MemoryEventSink(settings.event_cooldown_sec)

    def run(
        self,
        input_path: Path,
        output_path: Path,
        progress_callback=None,
    ) -> PipelineResult:
        reset_cooldowns()
        reset_history()
        self.event_sink.reset()

        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        model = get_model()
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {input_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_video = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps_video,
            (width, height),
        )

        prev = time.time()
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                results = model(frame, conf=self.conf_threshold, verbose=False)[0]
                detections = parse_detections(results)
                detections = update_tracks(detections)
                scene_objects = associate_objects(detections)
                violations = detect_violations(scene_objects)

                for violation in violations:
                    self.event_sink.emit(frame, violation)

                now = time.time()
                fps = 1 / max(now - prev, 1e-6)
                prev = now

                frame = draw_scene(frame, scene_objects, violations, fps)
                writer.write(frame)

                frame_idx += 1
                if progress_callback and total_frames > 0:
                    progress_callback(frame_idx / total_frames)
        finally:
            cap.release()
            writer.release()

        finalize_video_for_web(output_path)

        return PipelineResult(
            output_path=output_path,
            violations=self.event_sink.get_records(),
            frames_processed=frame_idx,
        )
