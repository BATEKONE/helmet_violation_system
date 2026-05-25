"""Обратная совместимость: локальный запуск pipeline без API."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import EVENT_IMAGES_DIR, EVENT_JSON_DIR, OUTPUT_VIDEO, ensure_dirs
from core.event_sink import FileEventSink
from core.pipeline import VideoPipeline
from core.settings import get_settings


def process_video(input_path, output_path=None, progress_callback=None):
    ensure_dirs()
    settings = get_settings()
    sink = FileEventSink(
        EVENT_IMAGES_DIR,
        EVENT_JSON_DIR,
        settings.event_cooldown_sec,
    )
    pipeline = VideoPipeline(event_sink=sink)
    result = pipeline.run(
        Path(input_path),
        Path(output_path or OUTPUT_VIDEO),
        progress_callback=progress_callback,
    )
    return str(result.output_path)
