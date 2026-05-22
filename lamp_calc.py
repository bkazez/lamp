#!/usr/bin/env python3
"""
Compute and display shade dimensions from lamp_config.toml.

Usage: python3 lamp_calc.py
"""

from lamp_config_loader import load_config, get_active_base, get_ratios, get_polygon_spec, get_diamond_config
from lamp_geometry import compute_polygon, compute_shade, compute_paper, compute_diamond_grid


def print_polygon_info(poly, spec):
    print(f"  18-gon (unit side length s = 1):")
    print(f"    Side angle:    {spec.side_angle_deg} deg ({spec.n_sides - 6} vertices)")
    print(f"    Gap angle:     {poly.gap_angle_deg:.0f} deg (6 vertices)")
    print(f"    Width:         {poly.width:.4f} s")
    print(f"    Height:        {poly.height:.4f} s")
    print(f"    Perimeter:     {poly.perimeter:.1f} s")
    print(f"    Edges:         {spec.n_regular_edges} regular + {spec.n_gap_edges} gap")


def print_base_results(name, base, shade, paper_list, diamond_grid=None):
    print()
    print(f"  {'=' * 61}")
    print(f"  {name.upper()} BASE: {base['diameter']}\" diam, {base['height']}\" tall")
    print(f"  {'=' * 61}")

    print(f"    Polygon side length:   {shade.side_length:.3f}\"")
    print(f"    Polygon perimeter:     {shade.polygon_perimeter:.2f}\"")
    print()
    print(f"    Shade height:          {shade.shade_height:.1f}\"")
    print(f"    Shade max diameter:    {shade.shade_diameter:.1f}\"")
    print(f"    Shade max circumf:     {shade.shade_circumference:.1f}\"")
    print(f"    Total lamp height:     {shade.total_lamp_height:.1f}\"")
    print()
    print(f"    Paper height:          {shade.shade_height:.1f}\"")

    if diamond_grid is not None:
        print(f"    Diamond row height:    {diamond_grid.row_height:.2f}\"")
        print(f"    Diagonal angle:        {diamond_grid.diagonal_angle_deg:.1f} deg")
        print(f"    Diagonal length:       {diamond_grid.diagonal_length:.2f}\"")

    print()
    hdr = f"    {'Pleats':>6}  {'Fold W':>8}  {'Strip':>12}  {'Base compress':>14}"
    print(hdr)
    print(f"    {'------':>6}  {'------':>8}  {'-----':>12}  {'-----------':>14}")
    for p in paper_list:
        ft = p.strip_length / 12
        print(
            f"    {p.n_pleats:>6}  {p.fold_width:>7.2f}\"  "
            f"{p.strip_length:>6.1f}\" ({ft:.1f}')  "
            f"{p.base_compression:>13.0%}"
        )


def main():
    cfg = load_config()
    spec = get_polygon_spec(cfg)
    poly = compute_polygon(spec)
    bsh_ratio, swh_ratio = get_ratios(cfg)

    p = cfg["proportions"]
    print("KLINT LAMPSHADE GEOMETRY CALCULATOR")
    print("=" * 65)
    print()
    print_polygon_info(poly, spec)
    print()
    print(f"  Target proportions:")
    print(f"    Base : shade height   = {p['base_to_shade_height'][0]}:{p['base_to_shade_height'][1]}"
          f" (1:{1/bsh_ratio:.1f})")
    print(f"    Shade width : height  = {p['shade_width_to_height'][0]}:{p['shade_width_to_height'][1]}"
          f" ({swh_ratio:.3f}:1)")

    pleat_counts = [18, 24, 36, 48, 54, 72]
    opening = cfg["accordion"]["opening_fraction"]
    diamond_cfg = get_diamond_config(cfg)
    n_diamond_rows = diamond_cfg["n_rows"] if diamond_cfg else None

    for name, base in cfg["bases"].items():
        shade = compute_shade(base["diameter"], base["height"], bsh_ratio, swh_ratio, poly)
        papers = [compute_paper(shade, n, opening) for n in pleat_counts]
        active_paper = compute_paper(shade, cfg["accordion"]["n_pleats"], opening)
        dgrid = compute_diamond_grid(active_paper, n_diamond_rows) if n_diamond_rows else None
        print_base_results(name, base, shade, papers, diamond_grid=dgrid)

    print()
    print("  " + "-" * 61)
    print("  Verify base heights. shade_height = base_height *"
          f" {1/bsh_ratio:.1f},")
    print("  so small measurement errors compound.")
    print("  " + "-" * 61)


if __name__ == "__main__":
    main()
