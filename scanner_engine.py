import cv2
import numpy as np
import json
import os
import pymupdf # PyMuPDF
from omr_layout_engine import OMRLayoutEngine

class ScannerEngine:
    def __init__(self, config_path=None, config_dict=None):
        self.engine = OMRLayoutEngine(config_path=config_path, config_dict=config_dict)
        self.config = self.engine.config
        # Target canonical A4 at 300 DPI -> 2480 x 3508 pixels
        self.dpi = self.config.get("scanner_params", {}).get("dpi", 300)
        self.A4_W_PX = int(210 * self.dpi / 25.4)
        self.A4_H_PX = int(297 * self.dpi / 25.4)
        
    def _mm_to_px(self, mm_val):
        return int(mm_val * self.dpi / 25.4)
        
    def load_image(self, file_path):
        """Loads image, handles PDF, PNG, TIFF."""
        ext = file_path.lower().split('.')[-1]
        if ext == 'pdf':
            doc = pymupdf.open(file_path)
            page = doc.load_page(0)
            zoom = self.dpi / 72.0
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        else:
            img = cv2.imread(file_path)
            
        if img is None:
            raise ValueError(f"Could not load image from {file_path}")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray

    def detect_registration_marks(self, gray_img):
        """
        Uses contour detection to find the exact 4 registration marks.
        Filters by size, then selects the ones closest to the 4 corners of the image.
        """
        _, thresh = cv2.threshold(gray_img, 150, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        target_size_px = self._mm_to_px(self.engine.reg_mark_size)
        area_expected = target_size_px * target_size_px
        
        marks = []
        for c in contours:
            area = cv2.contourArea(c)
            if area_expected * 0.4 < area < area_expected * 2.0:
                x, y, w, h = cv2.boundingRect(c)
                if 0.75 < w/h < 1.25:
                    cx = x + w//2
                    cy = y + h//2
                    marks.append((cx, cy))
                    
        if len(marks) >= 4:
            # Find the closest mark to each of the 4 corners
            h, w = gray_img.shape
            corners = [
                (0, 0),         # TL
                (w, 0),         # TR
                (w, h),         # BR
                (0, h)          # BL
            ]
            
            final_marks = []
            for corner_x, corner_y in corners:
                # Find the mark with the minimum euclidean distance to the corner
                best_mark = min(marks, key=lambda p: (p[0]-corner_x)**2 + (p[1]-corner_y)**2)
                final_marks.append(best_mark)
                
            return final_marks
        else:
            marks_conf = {m['id']: m for m in self.engine.reg_marks}
            return [
                (self._mm_to_px(float(marks_conf['tl']['x_mm']) + float(marks_conf['tl']['size_mm'])/2.0),
                 self._mm_to_px(float(marks_conf['tl']['y_mm']) + float(marks_conf['tl']['size_mm'])/2.0)),
                (self._mm_to_px(float(marks_conf['tr']['x_mm']) + float(marks_conf['tr']['size_mm'])/2.0),
                 self._mm_to_px(float(marks_conf['tr']['y_mm']) + float(marks_conf['tr']['size_mm'])/2.0)),
                (self._mm_to_px(float(marks_conf['br']['x_mm']) + float(marks_conf['br']['size_mm'])/2.0),
                 self._mm_to_px(float(marks_conf['br']['y_mm']) + float(marks_conf['br']['size_mm'])/2.0)),
                (self._mm_to_px(float(marks_conf['bl']['x_mm']) + float(marks_conf['bl']['size_mm'])/2.0),
                 self._mm_to_px(float(marks_conf['bl']['y_mm']) + float(marks_conf['bl']['size_mm'])/2.0))
            ]

    def warp_canonical(self, gray_img, src_pts):
        """Correct perspective mapping to exact A4."""
        # Destination points based on JSON configuration
        marks_conf = {m['id']: m for m in self.engine.reg_marks}
        
        def get_center(m_id):
            m = marks_conf[m_id]
            return [float(self._mm_to_px(float(m['x_mm']) + float(m['size_mm'])/2.0)), 
                    float(self._mm_to_px(float(m['y_mm']) + float(m['size_mm'])/2.0))]
                    
        dst_pts = np.array([
            get_center('tl'),
            get_center('tr'),
            get_center('br'),
            get_center('bl')
        ], dtype=np.float32)
        
        src_pts = np.array(src_pts, dtype=np.float32)
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(gray_img, M, (self.A4_W_PX, self.A4_H_PX))
        return warped

    def extract_answers(self, warped_img):
        """Samples bubbles using exactly the same layout engine coordinates."""
        thresh_marked = self.config.get("recognition_thresholds", {}).get("fill_ratio_marked", 0.65)
        thresh_ambig = self.config.get("recognition_thresholds", {}).get("fill_ratio_ambiguous_band", 0.15)
        
        _, thresh = cv2.threshold(warped_img, 150, 255, cv2.THRESH_BINARY_INV)
        
        results = {}
        for q_num, data in self.engine.question_coordinates.items():
            bubble_status = []
            for bx, by, br in data['bubbles']:
                px_x = self._mm_to_px(bx)
                px_y = self._mm_to_px(by)
                px_r = self._mm_to_px(br)
                
                # Sample a small square region inside the bubble
                roi_size = int(px_r * 0.8)
                roi = thresh[px_y - roi_size:px_y + roi_size, px_x - roi_size:px_x + roi_size]
                
                # Calculate fill ratio
                total_pixels = roi.shape[0] * roi.shape[1]
                if total_pixels == 0:
                    fill_ratio = 0
                else:
                    filled_pixels = cv2.countNonZero(roi)
                    fill_ratio = filled_pixels / total_pixels
                    
                if fill_ratio > thresh_marked:
                    bubble_status.append('MARKED')
                elif fill_ratio > (thresh_marked - thresh_ambig):
                    bubble_status.append('AMBIGUOUS')
                else:
                    bubble_status.append('BLANK')
            
            # Classification
            marked_indices = [i for i, s in enumerate(bubble_status) if s == 'MARKED']
            ambig_indices = [i for i, s in enumerate(bubble_status) if s == 'AMBIGUOUS']
            
            if len(ambig_indices) > 0:
                classification = "AMBIGUOUS"
                extracted = "?"
            elif len(marked_indices) == 1:
                classification = "VALID"
                extracted = chr(65 + marked_indices[0]) # A, B, C, D
            elif len(marked_indices) > 1:
                classification = "MULTIPLE / INVALID"
                extracted = "INVALID"
            else:
                classification = "BLANK"
                extracted = "BLANK"
                
            results[q_num] = {
                'classification': classification,
                'extracted': extracted,
                'section': data['section']
            }
            
        return results

if __name__ == "__main__":
    scanner = ScannerEngine('rise_omr_template.json')
    img = scanner.load_image('output/RISE_2027_OMR.pdf')
    marks = scanner.detect_registration_marks(img)
    warped = scanner.warp_canonical(img, marks)
    answers = scanner.extract_answers(warped)
    print("Scanned Q1:", answers[1])
    print("Scanned Q50:", answers[50])
