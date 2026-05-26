import numpy as np
import supervision as sv
from supervision.tracker.byte_tracker.core import ByteTrack

tracker = ByteTrack()


def reset_tracks() -> None:
    global tracker
    tracker = ByteTrack()


def update_tracks(detections):
    boxes = []
    confidences = []
    class_ids = []

    for det in detections:
        boxes.append(det["bbox"])
        confidences.append(det["confidence"])
        class_ids.append(det["class_id"])

    if len(boxes) == 0:
        return detections

    detections_sv = sv.Detections(
        xyxy=np.array(boxes, dtype=np.float32),
        confidence=np.array(confidences, dtype=np.float32),
        class_id=np.array(class_ids, dtype=np.int32),
    )

    tracked = tracker.update_with_detections(detections_sv)

    output = []
    for i, det in enumerate(detections):
        track_id = -1
        if tracked.tracker_id is not None and i < len(tracked.tracker_id):
            track_id = int(tracked.tracker_id[i])
        det["track_id"] = track_id
        output.append(det)

    return output
