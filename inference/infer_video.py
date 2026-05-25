import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import EVENT_IMAGES_DIR, EVENT_JSON_DIR, ensure_dirs
from core.event_sink import FileEventSink
from core.pipeline import VideoPipeline
from core.settings import get_settings


def parse_args():
    parser = argparse.ArgumentParser(description="Анализ видео: детекция отсутствия шлема")
    parser.add_argument("--source", type=Path, required=True, help="Путь к входному видео")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "processed.mp4",
        help="Путь к выходному видео",
    )
    parser.add_argument("--show", action="store_true", help="Показывать окно предпросмотра")
    return parser.parse_args()


def main():
    import cv2

    args = parse_args()
    ensure_dirs()
    settings = get_settings()

    sink = FileEventSink(
        EVENT_IMAGES_DIR,
        EVENT_JSON_DIR,
        settings.event_cooldown_sec,
    )
    pipeline = VideoPipeline(event_sink=sink)

    if args.show:
        cap = cv2.VideoCapture(str(args.source))
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {args.source}")
        cap.release()

    result = pipeline.run(args.source, args.output)
    print(f"Готово. Результат: {result.output_path.resolve()}")
    print(f"Нарушений: {len(result.violations)}")


if __name__ == "__main__":
    main()
