def box_area(box):
    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def compute_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])

    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)

    area1 = box_area(box1)
    area2 = box_area(box2)

    union = area1 + area2 - inter

    if union == 0:
        return 0

    return inter / union


def box_center(box):
    x1, y1, x2, y2 = box
    return (
        (x1 + x2) / 2,
        (y1 + y2) / 2
    )


def point_inside_box(point, box):
    px, py = point
    x1, y1, x2, y2 = box

    return x1 <= px <= x2 and y1 <= py <= y2