import json
from pathlib import Path

from core.config import EVENT_IMAGES_DIR, EVENT_JSON_DIR, ensure_dirs
from core.event_sink import FileEventSink
from core.settings import get_settings

_file_sink: FileEventSink | None = None


def _get_file_sink() -> FileEventSink:
    global _file_sink
    if _file_sink is None:
        settings = get_settings()
        _file_sink = FileEventSink(
            EVENT_IMAGES_DIR,
            EVENT_JSON_DIR,
            settings.event_cooldown_sec,
        )
    return _file_sink


def clear_events():
    ensure_dirs()
    _get_file_sink().reset()


def save_events(frame, violations):
    sink = _get_file_sink()
    for violation in violations:
        sink.emit(frame, violation)


def load_events():
    ensure_dirs()
    events = []

    for json_path in sorted(EVENT_JSON_DIR.glob("*.json")):
        with open(json_path, encoding="utf-8") as f:
            events.append(json.load(f))

    return events
