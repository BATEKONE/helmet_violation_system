import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from core.association import associate_objects
from core.cooldown import reset_cooldowns
from core.detection_parser import parse_detections
from core.event_sink import EventSink, MemoryEventSink, ViolationRecord
from core.inference_utils import (
    configure_cpu_threads,
    prepare_inference_frame,
    resolve_device,
    scale_detections,
    use_half_precision,
)
from core.settings import get_settings
from core.temporal import reset_history
from core.tracker import reset_tracks, update_tracks
from core.violation import detect_violations
from core.video_export import finalize_video_for_web
from core.visualization import draw_scene

_model = None
_model_device = None


def get_model() -> YOLO:
    global _model, _model_device
    if _model is None:
        settings = get_settings()
        configure_cpu_threads(settings.torch_num_threads)

        model_path = settings.resolve_model_path()
        if not model_path.exists():
            raise FileNotFoundError(
                f"Файл модели не найден: {model_path}. "
                "Сначала обучите модель: python training/train_yolo.py"
            )

        device = resolve_device(settings.inference_device)
        _model_device = device
        _model = YOLO(str(model_path))

        half = use_half_precision(device, settings.inference_half)
        dummy = np.zeros((settings.inference_imgsz, settings.inference_imgsz, 3), dtype=np.uint8)
        _model.predict(
            dummy,
            conf=settings.conf_threshold,
            imgsz=settings.inference_imgsz,
            device=device,
            half=half,
            verbose=False,
        )
    return _model


def reset_model() -> None:
    global _model, _model_device
    _model = None
    _model_device = None


@dataclass
class PipelineResult:
    output_path: Path | None
    violations: list[ViolationRecord]
    frames_processed: int
    frames_inferred: int
    avg_fps: float


class VideoPipeline:
    def __init__(self, event_sink: EventSink | None = None):
        settings = get_settings()
        self.settings = settings
        self.conf_threshold = settings.conf_threshold
        self.event_sink = event_sink or MemoryEventSink(settings.event_cooldown_sec)

    def _run_inference(self, model: YOLO, frame: np.ndarray) -> list[dict]:
        infer_frame, scale_back = prepare_inference_frame(
            frame, self.settings.inference_max_width
        )
        device = _model_device if _model_device is not None else resolve_device(
            self.settings.inference_device
        )
        half = use_half_precision(device, self.settings.inference_half)

        results = model.predict(
            infer_frame,
            conf=self.conf_threshold,
            imgsz=self.settings.inference_imgsz,
            device=device,
            half=half,
            verbose=False,
        )[0]

        detections = parse_detections(results)
        return scale_detections(detections, scale_back)

    def run(
        self,
        input_path: Path,
        output_path: Path,
        progress_callback=None,
    ) -> PipelineResult:
        reset_cooldowns()
        reset_history()
        reset_tracks()
        self.event_sink.reset()

        input_path = Path(input_path)
        output_path = Path(output_path)
        export_video = self.settings.export_annotated_video
        if export_video:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        model = get_model()
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {input_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_video = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        stride = max(1, self.settings.process_every_n_frames)

        writer = None
        if export_video:
            writer = cv2.VideoWriter(
                str(output_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps_video,
                (width, height),
            )

        prev = time.time()
        started = time.time()
        frame_idx = 0
        frames_inferred = 0

        last_scene_objects: list = []
        last_violations: list = []

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                run_infer = frame_idx % stride == 0
                if run_infer:
                    detections = self._run_inference(model, frame)
                    detections = update_tracks(detections)
                    last_scene_objects = associate_objects(detections)
                    last_violations = detect_violations(last_scene_objects)
                    frames_inferred += 1

                    for violation in last_violations:
                        self.event_sink.emit(frame, violation)

                if export_video and writer is not None:
                    now = time.time()
                    fps = 1 / max(now - prev, 1e-6)
                    prev = now
                    display = draw_scene(
                        frame,
                        last_scene_objects,
                        last_violations,
                        fps,
                    )
                    writer.write(display)

                frame_idx += 1
                if progress_callback and total_frames > 0:
                    progress_callback(frame_idx / total_frames)
        finally:
            cap.release()
            if writer is not None:
                writer.release()

        if export_video and output_path.exists() and self.settings.video_web_optimize:
            finalize_video_for_web(output_path)

        elapsed = max(time.time() - started, 1e-6)
        avg_fps = frame_idx / elapsed

        return PipelineResult(
            output_path=output_path if export_video else None,
            violations=self.event_sink.get_records(),
            frames_processed=frame_idx,
            frames_inferred=frames_inferred,
            avg_fps=avg_fps,
        )
