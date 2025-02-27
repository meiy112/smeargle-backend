#!/usr/bin/env python3
import cv2
import numpy as np
import sys
import json
import uuid

def color_list_to_hex(color):
    """
    Convert a list [B, G, R] to a hex string "#RRGGBB".
    """
    if color is None:
        return None
    return "#{:02x}{:02x}{:02x}".format(color[2], color[1], color[0])

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

def detect_rectangles_recursive(image, title, offset_x=0, offset_y=0, min_size=50):
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
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.2 or aspect_ratio > 5:
                continue
            
            rect = {
                "title": title,
                "x": int(x + offset_x),
                "y": int(y + offset_y),
                "width": int(w),
                "height": int(h)
            }
            
            bw, bcolor, bgcolor = detect_border_and_background(image, {"x": x, "y": y, "width": w, "height": h}, candidate_border=5, transparent_threshold=0.5)
            rect["border_width"] = bw
            rect["border_color"] = bcolor
            rect["background_color"] = bgcolor
            
            if bw > 0:
                rect["x"] += bw
                rect["y"] += bw
                rect["width"] -= 2 * bw
                rect["height"] -= 2 * bw
            
            rectangles.append(rect)
    
    for rect in rectangles:
        if rect["width"] >= min_size and rect["height"] >= min_size:
            inner_x = rect["x"]
            inner_y = rect["y"]
            inner_w = rect["width"]
            inner_h = rect["height"]
            sub_offset_x = inner_x - offset_x
            sub_offset_y = inner_y - offset_y
            inner_image = image[sub_offset_y:sub_offset_y+inner_h, sub_offset_x:sub_offset_x+inner_w]
            children = detect_rectangles_recursive(inner_image, title, offset_x=inner_x, offset_y=inner_y, min_size=min_size)
            if children:
                rect["children"] = children
    return rectangles

def assign_ids(rectangles):
    for rect in rectangles:
        rect["id"] = str(uuid.uuid4())
        if "children" in rect and rect["children"]:
            assign_ids(rect["children"])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: process_image.py <image_path> <title>"}))
        sys.exit(1)
    
    image_path = sys.argv[1]
    title = sys.argv[2]
    
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        print(json.dumps([]))
        sys.exit(0)
    
    rects = detect_rectangles_recursive(image, title, offset_x=0, offset_y=0, min_size=50)
    assign_ids(rects)
    print(json.dumps(rects, indent=2))