import time

from core.config import EVENT_COOLDOWN_SEC

_last_event = {}


def can_create_event(track_id):
    now = time.time()
    last = _last_event.get(track_id)
    if last is not None and now - last < EVENT_COOLDOWN_SEC:
        return False
    _last_event[track_id] = now
    return True


def reset_cooldowns():
    _last_event.clear()
