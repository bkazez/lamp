#!/usr/bin/env python3
"""
Generate a printable PDF pattern for an accordion-fold origami lampshade.
Le Klint style fold pattern - outputs at actual size for printing.
"""

import math
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import gray

# Configuration
OUTPUT_FILE = "/Users/bkazez/Projects/lamp/lamp_pattern.pdf"

# Pattern geometry matching the example image exactly:
# - 1" = half-width of each diamond (horizontal distance from vertical line to peak)
# - 2.36" = triangle height (vertical distance from horizontal line to diagonal peak)
# - 2.56" = diagonal line length
# - 67° = angle of diagonal from horizontal
#
# The pattern has:
# - Vertical lines every 2" (at diamond corners, where pleats fold)
# - Horizontal lines every 2.56" (at diamond top/bottom points)
# - Diagonals connecting vertical-line/horizontal-line intersections
#   to the midpoints between vertical lines on adjacent horizontals

DIAMOND_HALF_WIDTH = 1.0  # inches - "1in" from example
DIAMOND_WIDTH = 2 * DIAMOND_HALF_WIDTH  # 2" between vertical lines
ROW_HEIGHT = 2.56  # inches between horizontal lines

# Target dimensions from example: 36" x 17.14"
NUM_COLUMNS = 18  # 36" / 2" = 18 diamond widths
NUM_ROWS = 7  # gives ~17.92" height

TOTAL_WIDTH = NUM_COLUMNS * DIAMOND_WIDTH  # 36"
TOTAL_HEIGHT = NUM_ROWS * ROW_HEIGHT  # 17.92"

LINE_COLOR = gray


def create_pattern_pdf():
    """Create actual-size lampshade pattern PDF."""
    # Page size = pattern size (for actual-size printing)
    page_width = TOTAL_WIDTH * inch
    page_height = TOTAL_HEIGHT * inch

    c = canvas.Canvas(OUTPUT_FILE, pagesize=(page_width, page_height))

    col_w = DIAMOND_WIDTH * inch
    row_h = ROW_HEIGHT * inch
    half_col = col_w / 2

    c.setLineWidth(0.5)
    c.setStrokeColor(LINE_COLOR)
    c.setDash([])

    # Draw horizontal lines
    for row in range(NUM_ROWS + 1):
        y = row * row_h
        c.line(0, y, page_width, y)

    # Draw vertical lines
    for col in range(NUM_COLUMNS + 1):
        x = col * col_w
        c.line(x, 0, x, page_height)

    # Draw diagonals
    # Pattern: from vertical/horizontal intersections, diagonals go to
    # midpoints on adjacent horizontal lines
    # Alternating pattern creates the diamond shapes

    for row in range(NUM_ROWS):
        y_bot = row * row_h
        y_top = (row + 1) * row_h

        for col in range(NUM_COLUMNS + 1):
            x_vert = col * col_w

            # Alternate based on (col + row) to create interlocking diamonds
            if (col + row) % 2 == 0:
                # This vertex has diagonals going UP to midpoints
                if col > 0:
                    x_mid_left = (col - 0.5) * col_w
                    c.line(x_vert, y_bot, x_mid_left, y_top)
                if col < NUM_COLUMNS:
                    x_mid_right = (col + 0.5) * col_w
                    c.line(x_vert, y_bot, x_mid_right, y_top)
            else:
                # This vertex has diagonals going DOWN to midpoints
                if col > 0:
                    x_mid_left = (col - 0.5) * col_w
                    c.line(x_vert, y_top, x_mid_left, y_bot)
                if col < NUM_COLUMNS:
                    x_mid_right = (col + 0.5) * col_w
                    c.line(x_vert, y_top, x_mid_right, y_bot)

    c.save()
    print(f"PDF saved to: {OUTPUT_FILE}")
    print(f"Pattern size: {TOTAL_WIDTH:.1f}\" x {TOTAL_HEIGHT:.2f}\"")
    print(f"Columns: {NUM_COLUMNS}, Rows: {NUM_ROWS}")
    print(f"Print at 100% scale on 36\"+ wide paper")


if __name__ == "__main__":
    create_pattern_pdf()
