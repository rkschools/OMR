import os
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black
from omr_layout_engine import OMRLayoutEngine

class PDFGenerator:
    def __init__(self, config_path=None, output_path="output.pdf", config_dict=None):
        self.engine = OMRLayoutEngine(config_path=config_path, config_dict=config_dict)
        self.config = self.engine.config
        self.output_path = output_path
        
        dir_name = os.path.dirname(self.output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        self.c = canvas.Canvas(self.output_path, pagesize=A4)
        self.pdf_height = 297.0 * mm
        self.pdf_width = 210.0 * mm
        
        brand = self.config.get("brand_colors", {})
        self.primary_color = HexColor(brand.get("primary", "#123E7C"))
        self.accent_color = HexColor(brand.get("accent", "#E8720C"))
        self.section_bg = HexColor("#F8FAFC") # Very subtle background, almost white-gray
        
    def _tr_y(self, y_mm):
        return self.pdf_height - (y_mm * mm)

    def _tr_x(self, x_mm):
        return x_mm * mm
        
    def _draw_rect_mm(self, x, y, w, h, fill=0, stroke=1):
        self.c.rect(self._tr_x(x), self._tr_y(y+h), w*mm, h*mm, fill=fill, stroke=stroke)
        
    def _draw_line_mm(self, x1, y1, x2, y2):
        self.c.line(self._tr_x(x1), self._tr_y(y1), self._tr_x(x2), self._tr_y(y2))

    def generate(self):
        self._draw_registration_marks()
        self._draw_header()
        self._draw_student_info()
        self._draw_sections()
        
        self.c.showPage()
        self.c.save()
        print(f"Generated PDF at {self.output_path}")

    def _draw_registration_marks(self):
        self.c.setFillColor(black)
        self.c.setStrokeColor(black)
        for mark in self.engine.reg_marks:
            x = mark['x_mm']
            y = mark['y_mm']
            s = mark['size_mm']
            self._draw_rect_mm(x, y, s, s, fill=1, stroke=0)

    def _draw_header(self):
        y = self.engine.header_y
        h = self.engine.header_height
        x = self.engine.usable_left
        w = self.engine.usable_width
        
        header_conf = self.config.get("header", {})
        
        # Logo placeholder
        logo_size = 20
        self.c.setStrokeColor(self.primary_color)
        self.c.setLineWidth(1)
        self._draw_rect_mm(x, y + 2, logo_size, logo_size, fill=0, stroke=1)
        self.c.setFont("Helvetica-Bold", 6)
        self.c.setFillColor(self.primary_color)
        self.c.drawCentredString(self._tr_x(x + logo_size/2), self._tr_y(y + 12), "LOGO")

        # Text Block
        text_x = x + logo_size + 15
        
        self.c.setFillColor(self.primary_color)
        self.c.setFont("Helvetica-Bold", 18)
        self.c.drawString(self._tr_x(text_x), self._tr_y(y + 8), header_conf.get("school_name", "").upper())
        
        self.c.setFillColor(black)
        self.c.setFont("Helvetica-Bold", 16)
        self.c.drawString(self._tr_x(text_x), self._tr_y(y + 16), self.config.get("exam_name", "").upper())
        
        self.c.setFillColor(self.accent_color)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(self._tr_x(text_x), self._tr_y(y + 22), f"{self.config.get('exam_title_long', '').upper()} - {header_conf.get('subtitle', '').upper()}")

    def _draw_student_info(self):
        y = self.engine.student_info_y
        h = self.engine.student_info_height
        x = self.engine.usable_left
        w = self.engine.usable_width
        
        # Box around the student info for structure
        self.c.setStrokeColor(HexColor("#E2E8F0"))
        self.c.setLineWidth(1)
        self._draw_rect_mm(x, y, w, h, fill=0, stroke=1)
        
        self.c.setFillColor(black)
        
        # We split the box logically without harsh lines, just whitespace and a subtle divider
        left_w = w * 0.55
        right_x = x + left_w + 10
        
        # Subtle vertical divider
        self.c.setStrokeColor(HexColor("#F1F5F9"))
        self._draw_line_mm(x + left_w, y + 2, x + left_w, y + h - 2)
        
        # -----------------------------
        # LEFT: Student Info
        # -----------------------------
        # Row 1: Name
        row1_y = y + 8
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(self._tr_x(x + 5), self._tr_y(row1_y), "STUDENT NAME")
        self.c.setStrokeColor(black)
        self.c.setLineWidth(0.5)
        self._draw_line_mm(x + 35, row1_y, x + left_w - 5, row1_y)
        
        # Row 2: Class & Section
        row2_y = y + 18
        self.c.drawString(self._tr_x(x + 5), self._tr_y(row2_y), "CLASS")
        self._draw_line_mm(x + 20, row2_y, x + 50, row2_y)
        
        self.c.drawString(self._tr_x(x + 55), self._tr_y(row2_y), "SECTION")
        self._draw_line_mm(x + 75, row2_y, x + 105, row2_y)
        
        # Row 3: Phone & Date
        row3_y = y + 28
        self.c.drawString(self._tr_x(x + 5), self._tr_y(row3_y), "PHONE NUMBER")
        self._draw_line_mm(x + 35, row3_y, x + 65, row3_y)
        
        self.c.drawString(self._tr_x(x + 70), self._tr_y(row3_y), "DATE")
        self._draw_line_mm(x + 82, row3_y, x + 105, row3_y)
        
        # -----------------------------
        # RIGHT: Reg Number & Paper Set
        # -----------------------------
        # Registration Number
        reg = self.config.get("registration_number", {})
        bw = 6.0
        bh = 7.5
        gap = 1.5
        
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(self._tr_x(right_x + 5), self._tr_y(y + 8), "REGISTRATION NUMBER")
        
        self.c.setLineWidth(1)
        self.c.setStrokeColor(black)
        reg_start_x = right_x + 5
        for i in range(6):
            self._draw_rect_mm(reg_start_x + i*(bw+gap), y + 12, bw, bh, fill=0, stroke=1)
            
        # Paper Set
        self.c.setFont("Helvetica-Bold", 8)
        self.c.drawString(self._tr_x(right_x + 5), self._tr_y(y + 26), "PAPER SET")
        options = ["A", "B", "C", "D"]
        r = 2.5
        spacing = 8
        set_start_x = right_x + 30
        
        self.c.setLineWidth(0.5)
        for i, opt in enumerate(options):
            bx = set_start_x + i * spacing
            by = y + 27
            self.c.circle(self._tr_x(bx + r), self._tr_y(by - r), r*mm, stroke=1, fill=0)
            self.c.setFont("Helvetica", 6)
            self.c.drawCentredString(self._tr_x(bx + r), self._tr_y(by - r) - 2.5, opt)


    def _draw_sections(self):
        self.c.setLineWidth(0.5)
        
        sections = getattr(self.engine, 'sections', self.config.get("sections", []))
        sections_by_id = {s["section_id"]: s for s in sections}
        options = ["A", "B", "C", "D", "E"]
        
        prev_qx = -1
        prev_sec_id = None
        
        sorted_qs = sorted(self.engine.question_coordinates.items(), key=lambda x: int(x[0]))
        for q_num, data in sorted_qs:
            qx = data['q_x']
            qy = data['q_y']
            sec_id = data['section']
            
            if sec_id != prev_sec_id or (sec_id == prev_sec_id and qx != prev_qx):
                sec_info = sections_by_id.get(sec_id, {})
                sy = qy - self.engine.section_header_bottom_gap - self.engine.section_header_height
                
                self.c.setFillColor(self.section_bg)
                self.c.setStrokeColor(self.section_bg)
                self._draw_rect_mm(qx, sy, self.engine.col_width, self.engine.section_header_height - 1, fill=1, stroke=0)
                
                self.c.setFillColor(self.accent_color)
                self._draw_rect_mm(qx, sy, 2, self.engine.section_header_height - 1, fill=1, stroke=0)
                
                title = sec_info.get("name", "").upper()
                    
                self.c.setFillColor(self.primary_color)
                self.c.setFont("Helvetica-Bold", 8)
                self.c.drawString(self._tr_x(qx + 4), self._tr_y(sy + 5), title)
                
            prev_qx = qx
            prev_sec_id = sec_id
            
            self.c.setFillColor(black)
            self.c.setFont("Helvetica-Bold", 7)
            self.c.drawRightString(self._tr_x(qx + 7), self._tr_y(qy + self.engine.bubble_diameter/2 + 2), f"Q.{int(q_num):02d}")
            
            self.c.setStrokeColor(black)
            self.c.setLineWidth(0.5)
            for i, b in enumerate(data['bubbles']):
                cx, cy, r = b
                self.c.circle(self._tr_x(cx), self._tr_y(cy), r*2.8346472, stroke=1, fill=0)
                if i < len(options):
                    opt = options[i]
                    self.c.setFont("Helvetica-Bold", 6)
                    self.c.drawCentredString(self._tr_x(cx), self._tr_y(cy) - 2.0, opt)
                
if __name__ == "__main__":
    gen = PDFGenerator('rise_omr_template.json', 'output/RISE_2027_OMR.pdf')
    gen.generate()
