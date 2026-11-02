def _draw_sections(self):
    # ...
    for i, b in enumerate(data['bubbles']):
        cx, cy, r = b
        self.c.circle(self._tr_x(cx), self._tr_y(cy), r*2.8346472, stroke=1, fill=0)
        # Draw option label to the right
        opt_label = options[i]
        self.c.setFont("Helvetica-Bold", 6)
        self.c.drawCentredString(self._tr_x(cx + 3.0), self._tr_y(cy) - 2.0, opt_label)
