import cv2
import fitz
import numpy as np
from scanner_engine import ScannerEngine
from pdf_generator import PDFGenerator
from omr_layout_engine import OMRLayoutEngine
import json

# 1. First generate a fresh PDF (just in case)
gen = PDFGenerator('rise_omr_template.json', 'output/test_clean.pdf')
gen.generate()

# 2. Add some synthetic marks (simulating a student filling the bubbles)
engine = gen.engine
coords = engine.question_coordinates

import reportlab.pdfgen.canvas
doc = fitz.open('output/test_clean.pdf')
page = doc.load_page(0)

def fill_bubble(q, opt_idx):
    bx, by, r = coords[q]['bubbles'][opt_idx]
    fx = bx * 2.8346472
    fy = by * 2.8346472
    fr = r * 2.8346472
    rect = fitz.Rect(fx - fr, fy - fr, fx + fr, fy + fr)
    page.draw_oval(rect, color=(0,0,0), fill=(0,0,0))
    
# Q1: Option A (index 0)
fill_bubble(1, 0)
# Q2: Option B (index 1)
fill_bubble(2, 1)
# Q3: Option C and D (multiple)
fill_bubble(3, 2)
fill_bubble(3, 3)

# Q4 is left blank

doc.save('output/test_marked_final.pdf')
pix = page.get_pixmap(dpi=300)
pix.save('output/test_marked.png')

# 3. Run scanner
scanner = ScannerEngine('rise_omr_template.json')
gray = scanner.load_image('output/test_marked.png')
src_pts = scanner.detect_registration_marks(gray)
warped = scanner.warp_canonical(gray, src_pts)
results = scanner.extract_answers(warped)

print("--- SCANNER RESULTS ---")
print("Q1:", results.get(1))
print("Q2:", results.get(2))
print("Q3:", results.get(3))
print("Q4:", results.get(4))
print("Q5:", results.get(5))

# check if any other questions triggered false positives
unanswered_count = 0
for k, v in results.items():
    if v == 'UNANSWERED':
        unanswered_count += 1
    elif k not in [1, 2, 3]:
        print(f"WARNING: Q{k} detected as {v} but should be UNANSWERED!")

print(f"Total UNANSWERED correctly: {unanswered_count}")
