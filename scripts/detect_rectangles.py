#!/usr/bin/env python3
import cv2
import numpy as np
import sys
import json

def detect_rectangles(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    rectangles = []

    for contour in contours:
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            rectangles.append({
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            })

    return rectangles

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: process_image.py <image_path> <title>"}))
        sys.exit(1)

    image_path = sys.argv[1]
    title = sys.argv[2]

    rects = detect_rectangles(image_path)
    
    result = {
        "title": title,
        "rectangles": rects
    }

    print(json.dumps(result))