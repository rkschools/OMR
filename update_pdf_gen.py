import re

with open('/Users/kirankumarreddy/OMr/pdf_generator.py', 'r') as f:
    content = f.read()

new_logic = """    def _draw_sections(self):
        self.c.setLineWidth(0.5)
        
        sections_by_id = {s["section_id"]: s for s in self.config.get("sections", [])}
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
                if sec_id == prev_sec_id:
                    title += " (CONT.)"
                    
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
                self.c.circle(self._tr_x(cx), self._tr_y(cy), r*2.8346472, stroke=1, fill=0)"""

pattern = re.compile(r'    def _draw_sections\(self\):.*?r\*mm, stroke=1, fill=0\)', re.DOTALL)
content = pattern.sub(new_logic, content)

with open('/Users/kirankumarreddy/OMr/pdf_generator.py', 'w') as f:
    f.write(content)
print("Updated pdf_generator.py")
