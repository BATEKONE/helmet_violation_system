import cv2


def draw_scene(frame, scene_objects, violations, fps):
    violation_ids = {v["track_id"] for v in violations}

    for obj in scene_objects:
        track_id = obj["track_id"]
        if track_id == -1:
            continue

        x1, y1, x2, y2 = map(int, obj["bbox"])

        if track_id in violation_ids:
            label = "VIOLATION"
            color = (0, 0, 255)
        elif obj["has_helmet"]:
            label = "HELMET OK"
            color = (0, 255, 0)
        else:
            label = "CHECKING"
            color = (0, 165, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            f"ID:{track_id} {label}",
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2,
    )

    return frame
