import cv2
import numpy as np
from scanner_engine import ScannerEngine

scanner = ScannerEngine('rise_omr_template.json')
img = scanner.load_image('output/RISE_2027_OMR.pdf')

_, thresh = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY_INV)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

target_size_px = scanner._mm_to_px(4)
area_expected = target_size_px * target_size_px
print(f"Target size: {target_size_px}px, Expected Area: {area_expected}")

marks = []
for c in contours:
    area = cv2.contourArea(c)
    if area_expected * 0.5 < area < area_expected * 1.5:
        x, y, w, h = cv2.boundingRect(c)
        if 0.8 < w/h < 1.2:
            cx = x + w//2
            cy = y + h//2
            marks.append((cx, cy, area, w, h))

print("Potential marks found:", marks)
