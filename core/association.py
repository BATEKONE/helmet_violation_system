from core.confidence import compute_scene_confidence
from core.filters import valid_detection


def associate_objects(detections):
    scene_objects = []

    for det in detections:
        class_name = det["class_name"]
        if class_name not in ("helmet", "no_helmet"):
            continue

        bbox = det["bbox"]
        if not valid_detection(bbox):
            continue

        has_helmet = class_name == "helmet"

        scene_objects.append({
            "track_id": det["track_id"],
            "bbox": bbox,
            "confidence": det["confidence"],
            "class_name": class_name,
            "has_helmet": has_helmet,
            "scene_confidence": compute_scene_confidence(det["confidence"]),
        })

    return scene_objects
