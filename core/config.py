from pathlib import Path

from core.settings import ROOT, get_settings

_settings = get_settings()

OUTPUT_DIR = ROOT / "outputs"
EVENTS_DIR = ROOT / "events"
EVENT_JSON_DIR = EVENTS_DIR / "json"
EVENT_IMAGES_DIR = EVENTS_DIR / "images"

OUTPUT_VIDEO = OUTPUT_DIR / "processed.mp4"

CONF_THRESHOLD = _settings.conf_threshold
EVENT_COOLDOWN_SEC = _settings.event_cooldown_sec
TEMPORAL_WINDOW = _settings.temporal_window


def get_model_path() -> Path:
    return _settings.resolve_model_path()


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVENT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    EVENT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    _settings.ensure_data_dirs()
