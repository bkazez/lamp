#!/usr/bin/env python3
"""
Generate a printable accordion fold pattern for a Klint-style lampshade.

Reads lamp_config.toml for all parameters.

In "actual" mode: outputs a single page at the exact pattern size,
suitable for plotters or large-format printers.

In tiled mode ("letter", "tabloid", or custom [w, h]): outputs multiple
pages with overlap and registration marks for taping together.

Usage:
  python3 lamp_pattern.py [--base NAME]
"""

import argparse
import math
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color

from lamp_config_loader import load_config, get_ratios, get_polygon_spec, get_diamond_config
from lamp_geometry import compute_polygon, compute_shade, compute_paper, compute_diamond_grid

OUTPUT_DIR = Path(__file__).parent

NAMED_PAGE_SIZES = {
    "letter": (8.5, 11.0),
    "tabloid": (11.0, 17.0),
    "a4": (8.27, 11.69),
    "a3": (11.69, 16.54),
}

MOUNTAIN_COLOR = Color(0.7, 0, 0, alpha=0.6)
VALLEY_COLOR = Color(0, 0, 0.7, alpha=0.6)
MOUNTAIN_DIAG_COLOR = Color(0.8, 0.3, 0, alpha=0.5)
VALLEY_DIAG_COLOR = Color(0, 0.3, 0.8, alpha=0.5)
MOUNTAIN_HORIZ_COLOR = Color(0.6, 0, 0.3, alpha=0.5)
VALLEY_HORIZ_COLOR = Color(0, 0.2, 0.6, alpha=0.5)
OUTLINE_COLOR = Color(0, 0, 0)
LABEL_COLOR = Color(0.4, 0.4, 0.4)
FOLD_LINE_WIDTH_PT = 0.5
DIAG_LINE_WIDTH_PT = 0.4
CUT_LINE_WIDTH_PT = 1.0
OVERLAP_INCHES = 0.5
REGISTRATION_INCHES = 0.15


# ============================================================================
# Page size resolution
# ============================================================================

def resolve_page_size(pattern_cfg, strip_w_in, strip_h_in):
    """
    Return (page_w_in, page_h_in, is_actual) from the config.

    "actual" mode: page = pattern size + small border for labels.
    Named sizes or [w, h]: tiled mode.
    """
    raw = pattern_cfg["page_size"]

    if raw == "actual":
        border = 0.6
        return strip_w_in + border, strip_h_in + border + 0.8, True

    if isinstance(raw, str):
        if raw.lower() not in NAMED_PAGE_SIZES:
            raise ValueError(f"Unknown page_size '{raw}'. "
                             f"Options: {list(NAMED_PAGE_SIZES.keys())} or 'actual'")
        return (*NAMED_PAGE_SIZES[raw.lower()], False)

    if isinstance(raw, list) and len(raw) == 2:
        return (raw[0], raw[1], False)

    raise ValueError(f"Invalid page_size: {raw}")


# ============================================================================
# Drawing helpers
# ============================================================================

def draw_fold_lines(c, n_pleats, fold_w_pts, strip_h_pts, strip_w_pts,
                    x_off, y_off, view_w, view_h):
    """Draw mountain/valley fold lines within the visible region."""
    for i in range(n_pleats + 1):
        x_abs = i * fold_w_pts
        x_local = x_abs - x_off

        if x_local < -fold_w_pts or x_local > view_w + fold_w_pts:
            continue

        y_lo = max(0, -y_off)
        y_hi = min(view_h, strip_h_pts - y_off)
        if y_lo >= y_hi:
            continue

        if i == 0 or i == n_pleats:
            c.setStrokeColor(OUTLINE_COLOR)
            c.setLineWidth(CUT_LINE_WIDTH_PT)
            c.setDash([])
        elif i % 2 == 1:
            c.setStrokeColor(MOUNTAIN_COLOR)
            c.setLineWidth(FOLD_LINE_WIDTH_PT)
            c.setDash([6, 3])
        else:
            c.setStrokeColor(VALLEY_COLOR)
            c.setLineWidth(FOLD_LINE_WIDTH_PT)
            c.setDash([2, 2])

        c.line(x_local, y_lo, x_local, y_hi)


def draw_cut_lines(c, strip_w_pts, strip_h_pts, x_off, y_off,
                   view_w, view_h):
    """Draw horizontal (top/bottom) cut lines."""
    c.setStrokeColor(OUTLINE_COLOR)
    c.setLineWidth(CUT_LINE_WIDTH_PT)
    c.setDash([])

    x_lo = max(0, -x_off)
    x_hi = min(view_w, strip_w_pts - x_off)
    if x_lo >= x_hi:
        return

    # Bottom edge
    y_bot = -y_off
    if 0 <= y_bot <= view_h:
        c.line(x_lo, y_bot, x_hi, y_bot)

    # Top edge
    y_top = strip_h_pts - y_off
    if 0 <= y_top <= view_h:
        c.line(x_lo, y_top, x_hi, y_top)


def draw_horizontal_folds(c, n_rows, row_h_pts, strip_w_pts, strip_h_pts,
                          x_off, y_off, view_w, view_h, scheme):
    """Draw internal horizontal fold lines (between rows)."""
    for r in range(1, n_rows):
        y_abs = r * row_h_pts
        y_local = y_abs - y_off
        if y_local < 0 or y_local > view_h:
            continue

        x_lo = max(0, -x_off)
        x_hi = min(view_w, strip_w_pts - x_off)
        if x_lo >= x_hi:
            continue

        if scheme == "standard":
            is_mountain = (r % 2 == 1)
        else:
            is_mountain = (r % 2 == 0)

        if is_mountain:
            c.setStrokeColor(MOUNTAIN_HORIZ_COLOR)
            c.setDash([6, 3])
        else:
            c.setStrokeColor(VALLEY_HORIZ_COLOR)
            c.setDash([2, 2])
        c.setLineWidth(FOLD_LINE_WIDTH_PT)
        c.line(x_lo, y_local, x_hi, y_local)


def _draw_one_diagonal(c, x1, y1, x2, y2, is_mountain):
    """Draw a single diagonal fold line with the appropriate style."""
    if is_mountain:
        c.setStrokeColor(MOUNTAIN_DIAG_COLOR)
        c.setDash([6, 3])
    else:
        c.setStrokeColor(VALLEY_DIAG_COLOR)
        c.setDash([2, 2])
    c.setLineWidth(DIAG_LINE_WIDTH_PT)
    c.line(x1, y1, x2, y2)


def draw_diagonal_folds(c, n_pleats, n_rows, fold_w_pts, row_h_pts,
                        strip_w_pts, strip_h_pts,
                        x_off, y_off, view_w, view_h, scheme):
    """
    Draw diagonal fold lines using the (col + row) % 2 alternation.

    At each grid intersection (col, row), if (col + row) % 2 == 0,
    diagonals go UP to midpoints on the next row. Otherwise DOWN.
    """
    for row in range(n_rows):
        y_bot = row * row_h_pts
        y_top = (row + 1) * row_h_pts

        for col in range(n_pleats + 1):
            x_vert = col * fold_w_pts
            goes_up = (col + row) % 2 == 0
            y_from = y_bot if goes_up else y_top
            y_to = y_top if goes_up else y_bot

            segments = []
            if col > 0:
                slope = "neg_slope" if goes_up else "pos_slope"
                segments.append(((col - 0.5) * fold_w_pts, y_to, slope))
            if col < n_pleats:
                slope = "pos_slope" if goes_up else "neg_slope"
                segments.append(((col + 0.5) * fold_w_pts, y_to, slope))

            for tx, ty, slope in segments:
                x1 = x_vert - x_off
                y1 = y_from - y_off
                x2 = tx - x_off
                y2 = ty - y_off

                if (max(x1, x2) < 0 or min(x1, x2) > view_w or
                        max(y1, y2) < 0 or min(y1, y2) > view_h):
                    continue

                is_mountain = (slope == "pos_slope") == (scheme == "standard")
                _draw_one_diagonal(c, x1, y1, x2, y2, is_mountain)


def draw_registration(c, col, row, n_cols, n_rows, view_w, view_h):
    """Draw alignment crosshairs at page edges for tiled output."""
    reg = REGISTRATION_INCHES * inch
    c.setStrokeColor(OUTLINE_COLOR)
    c.setLineWidth(0.5)
    c.setDash([])

    if col > 0:
        c.line(0, view_h / 2 - reg, 0, view_h / 2 + reg)
        c.line(-reg, view_h / 2, reg, view_h / 2)

    if col < n_cols - 1:
        c.line(view_w, view_h / 2 - reg, view_w, view_h / 2 + reg)
        c.line(view_w - reg, view_h / 2, view_w + reg, view_h / 2)

    if row > 0:
        c.line(view_w / 2 - reg, 0, view_w / 2 + reg, 0)
        c.line(view_w / 2, -reg, view_w / 2, reg)

    if row < n_rows - 1:
        c.line(view_w / 2 - reg, view_h, view_w / 2 + reg, view_h)
        c.line(view_w / 2, view_h - reg, view_w / 2, view_h + reg)


def draw_legend(c, x, y, diamond=False):
    """Draw the fold type legend. Returns the Y position after the last entry."""
    c.setFont("Helvetica", 7)
    c.setFillColor(LABEL_COLOR)
    line_len = 28
    text_offset = 33
    spacing = 12

    entries = [
        (MOUNTAIN_COLOR, FOLD_LINE_WIDTH_PT, [6, 3], "Mountain vertical"),
        (VALLEY_COLOR, FOLD_LINE_WIDTH_PT, [2, 2], "Valley vertical"),
    ]

    if diamond:
        entries.extend([
            (MOUNTAIN_DIAG_COLOR, DIAG_LINE_WIDTH_PT, [6, 3], "Mountain diagonal"),
            (VALLEY_DIAG_COLOR, DIAG_LINE_WIDTH_PT, [2, 2], "Valley diagonal"),
            (MOUNTAIN_HORIZ_COLOR, FOLD_LINE_WIDTH_PT, [6, 3], "Mountain horizontal"),
            (VALLEY_HORIZ_COLOR, FOLD_LINE_WIDTH_PT, [2, 2], "Valley horizontal"),
        ])

    entries.append((OUTLINE_COLOR, CUT_LINE_WIDTH_PT, [], "Cut line"))

    for color, width, dash, label in entries:
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setDash(dash)
        c.line(x, y, x + line_len, y)
        c.setFillColor(LABEL_COLOR)
        c.drawString(x + text_offset, y - 3, label)
        y -= spacing

    return y


# ============================================================================
# PDF generation
# ============================================================================

def generate_actual_size(paper, base_name, output_path, margin_in,
                         grid=None, diamond_cfg=None):
    """Single page at exact pattern size, for plotters."""
    margin = margin_in * inch
    strip_w = paper.strip_length * inch
    strip_h = paper.paper_height * inch
    has_diamond = grid is not None and diamond_cfg is not None
    legend_lines = 7 if has_diamond else 3
    label_space = (legend_lines * 12 + 20) / 72.0 * inch

    page_w = strip_w + 2 * margin
    page_h = strip_h + 2 * margin + label_space

    c = canvas.Canvas(str(output_path), pagesize=(page_w, page_h))
    c.saveState()
    c.translate(margin, margin)

    draw_fold_lines(c, paper.n_pleats, paper.fold_width * inch,
                    strip_h, strip_w, 0, 0, strip_w, strip_h)
    draw_cut_lines(c, strip_w, strip_h, 0, 0, strip_w, strip_h)

    if has_diamond:
        scheme = diamond_cfg.get("fold_scheme", "standard")
        row_h_pts = grid.row_height * inch
        draw_horizontal_folds(c, grid.n_rows, row_h_pts, strip_w, strip_h,
                              0, 0, strip_w, strip_h, scheme)
        draw_diagonal_folds(c, paper.n_pleats, grid.n_rows,
                            paper.fold_width * inch, row_h_pts,
                            strip_w, strip_h,
                            0, 0, strip_w, strip_h, scheme)

    c.setFont("Helvetica", 9)
    c.setFillColor(LABEL_COLOR)
    c.drawString(0, strip_h + 8,
                 f"{base_name} base  |  Fold: {paper.fold_width:.2f}\"  |  "
                 f"Pleats: {paper.n_pleats}  |  "
                 f"Strip: {paper.strip_length:.1f}\" x {paper.paper_height:.1f}\"")

    draw_legend(c, 0, strip_h + label_space - 4, diamond=has_diamond)

    c.restoreState()
    c.showPage()
    c.save()


def generate_tiled(paper, base_name, output_path, page_w_in, page_h_in,
                   margin_in, grid=None, diamond_cfg=None):
    """Multi-page tiled output with overlap and registration marks."""
    margin = margin_in * inch
    page_w = page_w_in * inch
    page_h = page_h_in * inch
    overlap = OVERLAP_INCHES * inch
    has_diamond = grid is not None and diamond_cfg is not None

    strip_w = paper.strip_length * inch
    strip_h = paper.paper_height * inch

    view_w = page_w - 2 * margin
    view_h = page_h - 2 * margin

    usable_w = view_w - overlap
    usable_h = view_h - overlap
    n_cols = max(1, math.ceil(strip_w / usable_w))
    n_rows = max(1, math.ceil(strip_h / usable_h))

    c = canvas.Canvas(str(output_path), pagesize=(page_w, page_h))

    for row in range(n_rows):
        for col in range(n_cols):
            x_off = col * usable_w
            y_off = row * usable_h

            c.saveState()
            c.translate(margin, margin)

            c.saveState()
            clip = c.beginPath()
            clip.rect(0, 0, view_w, view_h)
            c.clipPath(clip, stroke=0)

            draw_fold_lines(c, paper.n_pleats, paper.fold_width * inch,
                            strip_h, strip_w, x_off, y_off, view_w, view_h)
            draw_cut_lines(c, strip_w, strip_h, x_off, y_off, view_w, view_h)

            if has_diamond:
                scheme = diamond_cfg.get("fold_scheme", "standard")
                row_h_pts = grid.row_height * inch
                draw_horizontal_folds(c, grid.n_rows, row_h_pts,
                                      strip_w, strip_h,
                                      x_off, y_off, view_w, view_h, scheme)
                draw_diagonal_folds(c, paper.n_pleats, grid.n_rows,
                                    paper.fold_width * inch, row_h_pts,
                                    strip_w, strip_h,
                                    x_off, y_off, view_w, view_h, scheme)

            c.restoreState()

            draw_registration(c, col, row, n_cols, n_rows, view_w, view_h)

            page_num = row * n_cols + col + 1
            total_pages = n_cols * n_rows
            c.setFont("Helvetica", 8)
            c.setFillColor(LABEL_COLOR)
            c.drawString(2, view_h + 10,
                         f"Page {page_num}/{total_pages} "
                         f"(col {col + 1}/{n_cols}, row {row + 1}/{n_rows})  |  "
                         f"{base_name} base  |  Fold: {paper.fold_width:.2f}\"  |  "
                         f"Pleats: {paper.n_pleats}")

            if page_num == 1:
                draw_legend(c, 2, view_h + 25, diamond=has_diamond)

            c.restoreState()
            c.showPage()

    c.save()
    print(f"  Pages: {n_cols * n_rows} ({n_cols} cols x {n_rows} rows)")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate accordion fold pattern PDF")
    parser.add_argument("--base", help="Override active_base from config")
    args = parser.parse_args()

    cfg = load_config()
    spec = get_polygon_spec(cfg)
    poly = compute_polygon(spec)
    bsh_ratio, swh_ratio = get_ratios(cfg)

    base_name = args.base or cfg["active_base"]
    if base_name not in cfg["bases"]:
        print(f"Unknown base '{base_name}'. Available: {list(cfg['bases'].keys())}")
        raise SystemExit(1)

    base = cfg["bases"][base_name]
    shade = compute_shade(base["diameter"], base["height"], bsh_ratio, swh_ratio, poly)
    acc = cfg["accordion"]
    paper = compute_paper(shade, acc["n_pleats"], acc["opening_fraction"])

    diamond_cfg = get_diamond_config(cfg)
    grid = None
    if diamond_cfg is not None:
        grid = compute_diamond_grid(paper, diamond_cfg["n_rows"])

    page_w_in, page_h_in, is_actual = resolve_page_size(
        cfg["pattern"], paper.strip_length, paper.paper_height
    )

    filename = f"pattern_{base_name}_{paper.n_pleats}pleats.pdf"
    output_path = OUTPUT_DIR / filename

    print("ACCORDION FOLD PATTERN")
    print(f"  Base:         {base_name} ({base['diameter']}\" diam, {base['height']}\" tall)")
    print(f"  Shade:        {shade.shade_height:.1f}\" tall, {shade.shade_diameter:.1f}\" wide")
    print(f"  Paper:        {paper.strip_length:.1f}\" x {paper.paper_height:.1f}\""
          f" ({paper.strip_length / 12:.1f}' x {paper.paper_height:.1f}\")")
    print(f"  Pleats:       {paper.n_pleats}, fold width {paper.fold_width:.2f}\"")
    print(f"  Compression:  {paper.base_compression:.0%} at base")
    if grid is not None:
        print(f"  Diamond:      {grid.n_rows} rows, row height {grid.row_height:.2f}\","
              f" diagonal {grid.diagonal_angle_deg:.1f} deg")
    print(f"  Mode:         {'actual size (single page)' if is_actual else 'tiled'}")

    if is_actual:
        generate_actual_size(paper, base_name, output_path,
                             cfg["pattern"]["margin"],
                             grid=grid, diamond_cfg=diamond_cfg)
    else:
        generate_tiled(paper, base_name, output_path, page_w_in, page_h_in,
                       cfg["pattern"]["margin"],
                       grid=grid, diamond_cfg=diamond_cfg)

    print(f"\n  Saved: {output_path}")
    if is_actual:
        print(f"  Page size: {page_w_in:.1f}\" x {page_h_in:.1f}\""
              f" (print at 100% on plotter or large-format printer)")
    else:
        print(f"  Print at 100% scale. Cut, align registration marks, tape.")


if __name__ == "__main__":
    main()
