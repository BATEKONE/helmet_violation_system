import argparse
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.association import associate_objects
from core.config import CONF_THRESHOLD, get_model_path
from core.detection_parser import parse_detections
from core.tracker import update_tracks
from core.violation import detect_violations
from core.visualization import draw_scene


def parse_args():
    parser = argparse.ArgumentParser(description="Анализ изображения или кадра видео")
    parser.add_argument("--source", type=Path, required=True, help="Путь к изображению")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "result.jpg",
        help="Путь для сохранения результата",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    model_path = get_model_path()
    if not model_path.exists():
        raise FileNotFoundError(f"Модель не найдена: {model_path}")

    model = YOLO(str(model_path))
    frame = cv2.imread(str(args.source))
    if frame is None:
        raise ValueError(f"Не удалось прочитать изображение: {args.source}")

    results = model(frame, conf=CONF_THRESHOLD, verbose=False)[0]
    detections = parse_detections(results)
    detections = update_tracks(detections)
    scene_objects = associate_objects(detections)
    violations = detect_violations(scene_objects)
    output = draw_scene(frame.copy(), scene_objects, violations, fps=0.0)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output), output)
    print(f"Нарушений: {len(violations)}. Результат: {args.output.resolve()}")


if __name__ == "__main__":
    main()
