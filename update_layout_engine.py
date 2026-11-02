import re

with open('/Users/kirankumarreddy/OMr/omr_layout_engine.py', 'r') as f:
    content = f.read()

# Replace everything from "        # Mathematical partition" to the end of the file.
new_logic = """        # Evaluate a continuous flow layout for K=3
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
"""

import sys

parts = content.split("        # Mathematical partition into K columns minimizing max height")
if len(parts) == 2:
    with open('/Users/kirankumarreddy/OMr/omr_layout_engine.py', 'w') as f:
        f.write(parts[0] + new_logic)
    print("Updated layout engine successfully!")
else:
    print("Could not find split point")
    sys.exit(1)

