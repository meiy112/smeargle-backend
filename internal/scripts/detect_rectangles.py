#!/usr/bin/env python3
import cv2
import numpy as np
import sys
import json

MARGIN = 10

def color_list_to_hex(color):
    if color is None:
        return None
    return "#{:02x}{:02x}{:02x}".format(color[2], color[1], color[0])

def mode_color(pixels):
    uniques, counts = np.unique(pixels, axis=0, return_counts=True)
    mode_idx = np.argmax(counts)
    return uniques[mode_idx].tolist()

def detect_border_and_background(image, rect, candidate_border=5, background_transparent_threshold=0.5):
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
    
    if subimg.shape[2] >= 3:
        border_pixels_bgr = border_pixels[:, :3]
    else:
        border_pixels_bgr = border_pixels
    
    border_color_val = color_list_to_hex(np.array(mode_color(border_pixels_bgr), dtype=np.uint8).tolist())
    
    inner = subimg[candidate_border:h-candidate_border, candidate_border:w-candidate_border]
    if inner.size == 0:
        return candidate_border, border_color_val, None
    
    inner_pixels = inner.reshape(-1, inner.shape[2])
    if inner.shape[2] >= 3:
        inner_pixels_bgr = inner_pixels[:, :3]
    else:
        inner_pixels_bgr = inner_pixels
    
    if subimg.shape[2] == 4:
        alpha_inner = inner_pixels[:, 3]
        transparent_ratio_inner = np.count_nonzero(alpha_inner < 100) / alpha_inner.size
        if transparent_ratio_inner > background_transparent_threshold:
            background_color_val = "transparent"
        else:
            background_color_val = color_list_to_hex(np.array(mode_color(inner_pixels_bgr), dtype=np.uint8).tolist())
    else:
        background_color_val = color_list_to_hex(np.array(mode_color(inner_pixels_bgr), dtype=np.uint8).tolist())
    
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
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
            
            rect = {
                "title": title,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            }
            rect["inner_x"] = int(x + MARGIN) if w > 2 * MARGIN else x
            rect["inner_y"] = int(y + MARGIN) if h > 2 * MARGIN else y
            rect["inner_width"] = int(w - 2 * MARGIN) if w > 2 * MARGIN else w
            rect["inner_height"] = int(h - 2 * MARGIN) if h > 2 * MARGIN else h
            
            bw, bcolor, bgcolor = detect_border_and_background(image, rect, candidate_border=5, background_transparent_threshold=0.5)
            rect["border_width"] = bw
            rect["border_color"] = bcolor
            rect["background_color"] = bgcolor
            
            rectangles.append(rect)
    
    return rectangles

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: detect_rectangles.py <image_path> <title>"}))
        sys.exit(1)
    
    image_path = sys.argv[1]
    title = sys.argv[2]
    
    rects = detect_rectangles(image_path, title)
    print(json.dumps(rects, indent=2))