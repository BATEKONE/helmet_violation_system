from collections import defaultdict, deque

from core.config import TEMPORAL_WINDOW

history = defaultdict(lambda: deque(maxlen=TEMPORAL_WINDOW))


def update_history(track_id, has_helmet):
    history[track_id].append(has_helmet)


def get_stable_decision(track_id):
    states = history[track_id]
    if len(states) < 3:
        return None

    positive = sum(states)
    ratio = positive / len(states)

    if ratio >= 0.7:
        return True
    if ratio <= 0.3:
        return False
    return None


def reset_history():
    history.clear()
