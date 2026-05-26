from __future__ import annotations

import cv2
import numpy as np


def resolve_device(device_setting: str) -> str | int:
    """auto → cuda:0 если есть, иначе cpu."""
    value = (device_setting or "auto").strip().lower()
    if value != "auto":
        return device_setting

    try:
        import torch

        if torch.cuda.is_available():
            return 0
    except ImportError:
        pass
    return "cpu"


def use_half_precision(device, enabled: bool) -> bool:
    if not enabled:
        return False
    try:
        import torch

        if isinstance(device, int) or (isinstance(device, str) and device.startswith("cuda")):
            return torch.cuda.is_available()
    except ImportError:
        pass
    return False


def configure_cpu_threads(num_threads: int) -> None:
    if num_threads <= 0:
        return
    try:
        import torch

        torch.set_num_threads(num_threads)
    except ImportError:
        pass


def prepare_inference_frame(frame: np.ndarray, max_width: int) -> tuple[np.ndarray, float]:
    """
    Уменьшает кадр для инференса. Возвращает (кадр, scale_back):
    координаты bbox × scale_back → исходный кадр.
    """
    height, width = frame.shape[:2]
    if max_width <= 0 or width <= max_width:
        return frame, 1.0

    scale_back = width / max_width
    new_height = int(height / scale_back)
    resized = cv2.resize(
        frame,
        (max_width, new_height),
        interpolation=cv2.INTER_LINEAR,
    )
    return resized, scale_back


def scale_detections(detections: list[dict], scale_back: float) -> list[dict]:
    if scale_back == 1.0:
        return detections

    scaled = []
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        scaled.append({
            **det,
            "bbox": [
                x1 * scale_back,
                y1 * scale_back,
                x2 * scale_back,
                y2 * scale_back,
            ],
        })
    return scaled
