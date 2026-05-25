def valid_detection(box, min_width=10, min_height=10):
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    return width >= min_width and height >= min_height
