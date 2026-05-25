from core.temporal import get_stable_decision, update_history


def detect_violations(scene_objects):
    violations = []

    for obj in scene_objects:
        track_id = obj["track_id"]
        if track_id == -1:
            continue

        update_history(track_id, obj["has_helmet"])

        stable = get_stable_decision(track_id)
        if stable is False:
            violations.append({
                "track_id": track_id,
                "bbox": obj["bbox"],
                "confidence": obj["scene_confidence"],
            })

    return violations
