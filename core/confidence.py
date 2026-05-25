def compute_scene_confidence(*confidences):
    values = [float(c) for c in confidences if c and float(c) > 0]
    if not values:
        return 0.0
    return sum(values) / len(values)
