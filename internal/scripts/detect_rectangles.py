#!/usr/bin/env python3
import cv2
import numpy as np
import sys
import json

def color_list_to_hex(color):
    """
    Convert a list [B, G, R] to a hex string "#RRGGBB".
    """
    if color is None:
        return None
    return "#{:02x}{:02x}{:02x}".format(color[2], color[1], color[0])


def iou(rect1, rect2):
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
    if not rectangles:
        return []
    
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

def detect_border_and_background(image, rect, candidate_border=5, transparent_threshold=0.7):
    x, y, w, h = rect["x"], rect["y"], rect["width"], rect["height"]
    subimg = image[y:y+h, x:x+w]
    candidate_border = min(candidate_border, w//2, h//2)
    if candidate_border <= 0:
        return 0, None, None

    top = subimg[0:candidate_border, :]
    bottom = subimg[-candidate_border:, :]
    left = subimg[:, 0:candidate_border]
    right = subimg[:, -candidate_border:]
    
    border_pixels = np.concatenate([
        top.reshape(-1, subimg.shape[2]),
        bottom.reshape(-1, subimg.shape[2]),
        left.reshape(-1, subimg.shape[2]),
        right.reshape(-1, subimg.shape[2])
    ], axis=0)
    border_color = np.mean(border_pixels, axis=0)
    
    inner = subimg[candidate_border:h-candidate_border, candidate_border:w-candidate_border]
    if inner.size == 0:
        border_color_hex = color_list_to_hex(border_color.astype(np.uint8).tolist())
        return candidate_border, border_color_hex, None
    
    inner_pixels = inner.reshape(-1, inner.shape[2])
    background_color = np.mean(inner_pixels, axis=0)
    
    if subimg.shape[2] == 4:
        alpha_channel = inner[:, :, 3]
        transparent_ratio = np.count_nonzero(alpha_channel < 100) / alpha_channel.size
        if transparent_ratio > transparent_threshold:
            background_color_val = "transparent"
        else:
            background_color_val = color_list_to_hex(background_color[:3].astype(np.uint8).tolist())
        border_color_val = color_list_to_hex(border_color[:3].astype(np.uint8).tolist())
    else:
        background_color_val = color_list_to_hex(background_color.astype(np.uint8).tolist())
        border_color_val = color_list_to_hex(border_color.astype(np.uint8).tolist())
    
    return candidate_border, border_color_val, background_color_val

def detect_rectangles(image_path, title):
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        return []
    
    img_height, img_width = image.shape[:2]
    
    if image.shape[2] == 4:
        gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    rectangles = []
    min_area = (img_width * img_height) * 0.001
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        
        epsilon = 0.05 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, w, h = cv2.boundingRect(approx)
            if x == 0 and y == 0 and w == img_width and h == img_height:
                continue
            
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.2 or aspect_ratio > 5:
                continue
            
            rect = {
                "title": title,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            }
            rectangles.append(rect)
    
    rectangles = non_max_suppression(rectangles, iou_threshold=0.9)
    
    for rect in rectangles:
        border_width, border_color, background_color = detect_border_and_background(image, rect, candidate_border=5, transparent_threshold=0.5)
        rect["border_width"] = border_width
        rect["border_color"] = border_color
        rect["background_color"] = background_color
        if border_width > 0:
            rect["x"] += border_width
            rect["y"] += border_width
            rect["width"] -= 2 * border_width
            rect["height"] -= 2 * border_width
    
    return rectangles

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: process_image.py <image_path> <title>"}))
        sys.exit(1)
    
    image_path = sys.argv[1]
    title = sys.argv[2]
    
    rects = detect_rectangles(image_path, title)
    print(json.dumps(rects, indent=2))