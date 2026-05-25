CLASS_NAMES = {
    0: "helmet",
    1: "no_helmet",
}


def parse_detections(results):
    detections = []

    if results.boxes is None:
        return detections

    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        detections.append({
            "class_id": cls_id,
            "class_name": CLASS_NAMES.get(cls_id, f"class_{cls_id}"),
            "confidence": conf,
            "bbox": [x1, y1, x2, y2],
        })

    return detections
