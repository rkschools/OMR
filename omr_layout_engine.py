import json
import math

class OMRLayoutEngine:
    def __init__(self, config_path=None, config_dict=None):
        if config_dict is not None:
            self.config = config_dict
        elif config_path is not None:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            
        self._calculate_layout()
        
    def _calculate_layout(self):
        page = self.config.get("page", {})
        self.width_mm = 210.0
        self.height_mm = 297.0
        
        margins = page.get("margins_mm", {})
        self.m_top = margins.get("top", 10)
        self.m_bot = margins.get("bottom", 10)
        self.m_left = margins.get("left", 10)
        self.m_right = margins.get("right", 10)
        
        self.layout = self.config.get("layout", {})
        self.column_gap = self.layout.get("column_gap_mm", 12)
        
        # Authoritative approved registration mark geometry: 4.0mm x 4.0mm
        if self.config.get("reg_marks"):
            self.reg_marks = self.config["reg_marks"]
            self.reg_mark_size = float(self.reg_marks[0].get("size_mm", 4.0))
        elif self.config.get("registration_marks"):
            self.reg_marks = self.config["registration_marks"]
            self.reg_mark_size = float(self.reg_marks[0].get("size_mm", 4.0))
        else:
            self.reg_mark_size = 4.0
            self.reg_marks = [
                {"id": "tl", "x_mm": 5.0, "y_mm": 5.0, "size_mm": 4.0, "shape": "square_filled"},
                {"id": "tr", "x_mm": self.width_mm - 5.0 - 4.0, "y_mm": 5.0, "size_mm": 4.0, "shape": "square_filled"},
                {"id": "bl", "x_mm": 5.0, "y_mm": self.height_mm - 5.0 - 4.0, "size_mm": 4.0, "shape": "square_filled"},
                {"id": "br", "x_mm": self.width_mm - 5.0 - 4.0, "y_mm": self.height_mm - 5.0 - 4.0, "size_mm": 4.0, "shape": "square_filled"}
            ]
        
        self.usable_width = self.width_mm - self.m_left - self.m_right - 10
        self.usable_left = self.m_left + 5
        
        self.header_y = 12.0
        self.header_height = 24
        
        self.student_info_y = self.header_y + self.header_height + 4
        self.student_info_height = 30
        
        self.content_start_y = self.student_info_y + self.student_info_height + 6
        self.content_max_h = self.height_mm - self.content_start_y - self.m_bot - self.reg_mark_size - 4
        
        self.row_spacing = self.layout.get("row_spacing_mm", 7.0)
        self.bubble_diameter = self.layout.get("bubble_diameter_mm", 4.0)
        self.bubble_spacing = self.layout.get("bubble_spacing_mm", 6.0)
        layout_config = self.config.get("layout", {})
        
        self.section_header_height = layout_config.get("section_header_height", 8.0)
        self.section_header_bottom_gap = layout_config.get("section_header_bottom_gap", 5.0)
        self.section_bottom_margin = layout_config.get("section_bottom_margin", 8.0)
        
        # Resolve class-specific sections dynamically if classesConfig exists
        class_key = str(self.config.get("class_id") or self.config.get("class") or "").replace("class_", "")
        classes_config = self.config.get("classesConfig", {})
        if class_key and class_key in classes_config:
            sections = classes_config[class_key].get("sections", self.config.get("sections", []))
        else:
            sections = self.config.get("sections", [])
            
        section_heights = []
        for s in sections:
            q_count = s.get("question_count", 0)
            h = self.section_header_height + self.section_header_bottom_gap + (q_count * self.row_spacing) + self.section_bottom_margin
            section_heights.append(h)
            
        # Evaluate a continuous flow layout for K=3
        self.columns = 3
        self.col_width = (self.usable_width - (self.columns - 1) * self.column_gap) / self.columns
        header_overhead = self.section_header_height + self.section_header_bottom_gap + self.section_bottom_margin
        
        def simulate(target_h):
            coords = {}
            current_col = 0
            current_y = 0
            
            for s in sections:
                q_rem = s.get("question_count", 0)
                if q_rem == 0: continue
                
                start_q = s.get("question_numbering", {}).get("start", 1)
                opt_count = s.get("option_count", 4)
                
                first_part = True
                curr_q = start_q
                
                while q_rem > 0:
                    if current_y + header_overhead >= target_h and current_col < self.columns - 1:
                        current_col += 1
                        current_y = 0
                        first_part = False
                        
                    available_h = target_h - current_y - header_overhead
                    if available_h < self.row_spacing:
                        if current_col < self.columns - 1:
                            current_col += 1
                            current_y = 0
                            first_part = False
                            continue
                        else:
                            return None # Overflowed last column
                            
                    max_q = int(available_h // self.row_spacing)
                    take_q = min(q_rem, max_q)
                    
                    cx = self.usable_left + current_col * (self.col_width + self.column_gap)
                    cy = self.content_start_y + current_y
                    cy += self.section_header_height + self.section_header_bottom_gap
                    
                    for i in range(take_q):
                        qx = cx
                        qy = cy
                        
                        bubbles = []
                        bx_start = qx + 10
                        for opt_idx in range(opt_count):
                            bx = bx_start + opt_idx * self.bubble_spacing
                            bubbles.append((bx + self.bubble_diameter/2, qy + self.bubble_diameter/2, self.bubble_diameter/2))
                            
                        coords[curr_q] = {
                            "q_x": qx,
                            "q_y": qy,
                            "section": s["section_id"],
                            "bubbles": bubbles
                        }
                        
                        cy += self.row_spacing
                        curr_q += 1
                        
                    current_y += header_overhead + take_q * self.row_spacing
                    q_rem -= take_q
                    first_part = False
                    
            return coords

        low = 50.0
        high = self.content_max_h
        best_coords = None
        
        for _ in range(50):
            mid = (low + high) / 2
            res = simulate(mid)
            if res:
                best_coords = res
                high = mid
            else:
                low = mid
                
        if best_coords is None:
            best_coords = simulate(self.content_max_h)
            
        self.question_coordinates = best_coords if best_coords else {}
        self.sections = sections
