#!/usr/bin/env python3
import cv2
import pytesseract
import sys
import json

def estimate_font_color(image, rect):
    x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
    roi = image[y:y+h, x:x+w]
    avg_color = cv2.mean(roi)[:3]
    return tuple(map(int, avg_color))

def estimate_font_weight(image, rect):
    x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
    roi = image[y:y+h, x:x+w]
    
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    edges = cv2.Canny(gray_roi, 100, 200)
    
    inverted = cv2.bitwise_not(edges)
    
    dist_transform = cv2.distanceTransform(inverted, cv2.DIST_L2, 3)
    
    non_zero = dist_transform[dist_transform > 0]
    if non_zero.size == 0:
        return 0
    stroke_width = float(np.median(non_zero))
    return stroke_width


def detect_text(image_path, title):
    image = cv2.imread(image_path)
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    custom_config = r'--oem 3 --psm 6'
    ocr_data = pytesseract.image_to_data(gray, config=custom_config, output_type=pytesseract.Output.DICT)

    words = []
    n_boxes = len(ocr_data['text'])
    for i in range(n_boxes):
        try:
            conf = int(ocr_data['conf'][i])
        except ValueError:
            conf = -1
        if conf > 0 and ocr_data['text'][i].strip() != "":
            word_text = ocr_data['text'][i].strip()
            left = int(ocr_data['left'][i])
            top = int(ocr_data['top'][i])
            width = int(ocr_data['width'][i])
            height = int(ocr_data['height'][i])
            font_size = height

            rect = {
                "x": left,
                "y": top,
                "width": width,
                "height": height
            }
            color = estimate_font_color(image, rect)
            weight = estimate_font_weight(image, rect)

            words.append({
                "title": title,
                "word": word_text,
                "x": left,
                "y": top,
                "width": width,
                "height": height,
                "font_size": font_size,
                "font_color": color,
                "font_weight": weight
            })

    return words

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: detect_text.py <image_path> <title>"}))
        sys.exit(1)
    
    image_path = sys.argv[1]
    title = sys.argv[2]
    detected_words = detect_text(image_path, title)
    print(json.dumps(detected_words))