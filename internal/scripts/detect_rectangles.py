#!/usr/bin/env python3
import cv2
import numpy as np
import sys
import json

def is_inside(inner, outer):
    """Check if `inner` rectangle is fully inside `outer`."""
    return (
        inner["x"] >= outer["x"]
        and inner["y"] >= outer["y"]
        and (inner["x"] + inner["width"]) <= (outer["x"] + outer["width"])
        and (inner["y"] + inner["height"]) <= (outer["y"] + outer["height"])
    )

def iou(rect1, rect2):
    """Compute Intersection over Union (IoU) of two rectangles."""
    x1 = max(rect1["x"], rect2["x"])
    y1 = max(rect1["y"], rect2["y"])
    x2 = min(rect1["x"] + rect1["width"], rect2["x"] + rect2["width"])
    y2 = min(rect1["y"] + rect1["height"], rect2["y"] + rect2["height"])
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = rect1["width"] * rect1["height"]
    area2 = rect2["width"] * rect2["height"]
    union_area = area1 + area2 - inter_area
    return inter_area / union_area if union_area > 0 else 0

def non_max_suppression(rectangles, iou_threshold=0.9):
    """
    Remove duplicate or nearly identical rectangles by suppressing
    those with high overlap.
    """
    if not rectangles:
        return []
    
    # Sort rectangles by area (largest first)
    rectangles = sorted(rectangles, key=lambda r: r["width"] * r["height"], reverse=True)
    kept = []
    
    while rectangles:
        current = rectangles.pop(0)
        kept.append(current)
        new_rects = []
        for rect in rectangles:
            if iou(current, rect) < iou_threshold:
                new_rects.append(rect)
        rectangles = new_rects
    
    return kept

def group_rectangles(rectangles):
    """Sort rectangles & assign parents/children."""
    rectangles.sort(key=lambda r: r["width"] * r["height"])
    assigned = [False] * len(rectangles)
    hierarchy = []

    for i, rect in enumerate(rectangles):
        if assigned[i]:
            continue

        for j in range(i + 1, len(rectangles)):
            if is_inside(rect, rectangles[j]):
                if "children" not in rectangles[j]:
                    rectangles[j]["children"] = []
                rectangles[j]["children"].append(rect)
                assigned[i] = True
                break

        if not assigned[i]:
            hierarchy.append(rect)

    return hierarchy

def detect_rectangles(image_path, title):
    image = cv2.imread(image_path)
    if image is None:
        return []
    
    img_height, img_width = image.shape[:2]

    # Convert to grayscale and threshold
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Apply morphological closing to reduce noise
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Use RETR_TREE to detect all contours, including nested ones
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    rectangles = []
    min_area = (img_width * img_height) * 0.001  # adjust threshold as needed

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        # Increase epsilon to simplify contours more aggressively
        epsilon = 0.05 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            if x == 0 and y == 0 and w == img_width and h == img_height:
                continue  # Ignore full image bounding box

            # Optionally filter by aspect ratio if needed
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.2 or aspect_ratio > 5:
                continue

            rectangles.append({
                "title": title,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            })

    # Remove near-duplicate rectangles using non-maximum suppression
    rectangles = non_max_suppression(rectangles, iou_threshold=0.9)
    structured_rectangles = group_rectangles(rectangles)
    return structured_rectangles

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: process_image.py <image_path> <title>"}))
        sys.exit(1)

    image_path = sys.argv[1]
    title = sys.argv[2]

    rects = detect_rectangles(image_path, title)
    print(json.dumps(rects, indent=2))