"""
Core geometry for Klint-style accordion lampshade.

Pure functions, no I/O. All lengths are in inches unless noted.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PolygonSpec:
    n_sides: int
    side_angle_deg: float
    gap_edge_ratio: float
    n_regular_edges: int
    n_gap_edges: int


@dataclass(frozen=True)
class Polygon:
    """18-gon geometry results for unit side length (s = 1)."""
    width: float
    height: float
    perimeter: float
    gap_angle_deg: float
    vertices: tuple


@dataclass(frozen=True)
class ShadeDimensions:
    side_length: float
    polygon_perimeter: float
    shade_height: float
    shade_diameter: float
    shade_circumference: float
    total_lamp_height: float
    base_diameter: float
    base_height: float


@dataclass(frozen=True)
class PaperDimensions:
    n_pleats: int
    fold_width: float
    strip_length: float
    paper_height: float
    base_compression: float


@dataclass(frozen=True)
class DiamondGrid:
    n_rows: int
    row_height: float
    diagonal_angle_deg: float
    diagonal_length: float


def compute_polygon(spec: PolygonSpec) -> Polygon:
    """
    Compute the N-gon cross-section for unit side length.

    The polygon has two groups of vertices:
      "side" vertices with the specified interior angle (typically 150 deg)
      "gap" vertices whose angle is computed to close the polygon (typically 180 deg)

    With 12 side vertices at 150 deg, each contributes 30 deg of exterior angle,
    totaling 360 deg. The 6 gap vertices at 180 deg contribute 0 deg (straight).
    """
    n = spec.n_sides
    n_gap_verts = spec.n_gap_edges + 2
    n_side_verts = n - n_gap_verts
    total_angle = (n - 2) * 180
    gap_angle = (total_angle - n_side_verts * spec.side_angle_deg) / n_gap_verts

    half_n = n // 2
    # 4 gap edges total, split between 2 gaps (top/bottom), each gap
    # spanning both halves. Per half, per end = n_gap_edges / 4.
    n_gap_per_half_end = spec.n_gap_edges // 4

    direction = math.radians(-90 + gap_angle / 2)
    x, y = 0.0, 0.0
    right = [(x, y)]

    for i in range(half_n):
        is_gap_edge = (i < n_gap_per_half_end) or (i >= half_n - n_gap_per_half_end)
        edge_len = spec.gap_edge_ratio if is_gap_edge else 1.0

        x += edge_len * math.cos(direction)
        y += edge_len * math.sin(direction)
        right.append((x, y))

        vi = i + 1
        is_gap_vert = (vi <= n_gap_per_half_end) or (vi >= half_n - n_gap_per_half_end)
        interior = gap_angle if is_gap_vert else spec.side_angle_deg
        direction -= math.radians(180 - interior)

    left = [(-v[0], v[1]) for v in reversed(right[1:-1])]
    verts = right + left

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]

    perimeter = spec.n_regular_edges * 1.0 + spec.n_gap_edges * spec.gap_edge_ratio

    return Polygon(
        width=max(xs) - min(xs),
        height=max(ys) - min(ys),
        perimeter=perimeter,
        gap_angle_deg=gap_angle,
        vertices=tuple(verts),
    )


def compute_shade(
    base_diameter: float,
    base_height: float,
    base_to_shade_ratio: float,
    shade_width_to_height: float,
    polygon: Polygon,
) -> ShadeDimensions:
    """Compute physical shade dimensions from base measurements and proportions."""
    side_length = base_diameter / polygon.width
    perimeter = polygon.perimeter * side_length
    shade_height = base_height / base_to_shade_ratio
    shade_diameter = shade_height * shade_width_to_height

    return ShadeDimensions(
        side_length=side_length,
        polygon_perimeter=perimeter,
        shade_height=shade_height,
        shade_diameter=shade_diameter,
        shade_circumference=math.pi * shade_diameter,
        total_lamp_height=base_height + shade_height,
        base_diameter=base_diameter,
        base_height=base_height,
    )


def compute_paper(
    shade: ShadeDimensions,
    n_pleats: int,
    opening_fraction: float,
) -> PaperDimensions:
    """
    Compute paper strip dimensions for a given number of pleats.

    At the widest point of the shade, each pleat is open to opening_fraction
    of its fold width. At the base, pleats are much more compressed.
    """
    fold_width = shade.shade_circumference / (n_pleats * opening_fraction)
    strip_length = n_pleats * fold_width
    base_per_pleat = shade.polygon_perimeter / n_pleats
    compression = base_per_pleat / fold_width

    return PaperDimensions(
        n_pleats=n_pleats,
        fold_width=fold_width,
        strip_length=strip_length,
        paper_height=shade.shade_height,
        base_compression=compression,
    )


def compute_diamond_grid(paper: PaperDimensions, n_rows: int) -> DiamondGrid:
    """Compute diamond fold grid parameters from paper dimensions."""
    row_height = paper.paper_height / n_rows
    half_fold = paper.fold_width / 2
    diagonal_length = math.sqrt(row_height ** 2 + half_fold ** 2)
    diagonal_angle_deg = math.degrees(math.atan2(row_height, half_fold))

    return DiamondGrid(
        n_rows=n_rows,
        row_height=row_height,
        diagonal_angle_deg=diagonal_angle_deg,
        diagonal_length=diagonal_length,
    )
