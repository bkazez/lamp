#!/usr/bin/env python3
"""
18-gon lamp silhouette generator:
- Top 2 and bottom 2 edges are invisible (but vertices exist)
- All visible side edges have equal length
- Top/bottom (invisible) edge lengths are adjustable
- Side vertex angles are adjustable
- Top/bottom vertex angles adjust to close the polygon
"""

import math
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# Parameters
NUM_SIDES = 18
SIDE_VERTEX_ANGLE = 150  # degrees - adjustable angle at side vertices
TOP_BOTTOM_EDGE_RATIO = 0.5  # ratio of top/bottom edge length to side edge length
MISSING_TOP_EDGES = 2
MISSING_BOTTOM_EDGES = 2

OUTPUT_FILE = "/Users/bkazez/Projects/lamp/lamp_silhouette.png"


def generate_lamp_polygon(num_sides, side_angle_deg, top_bottom_edge_ratio):
    """
    Generate a symmetric polygon where:
    - Side vertices have the specified interior angle
    - Top/bottom vertices have angles computed to close the polygon
    - Side edges all have length 1
    - Top/bottom edges have length = top_bottom_edge_ratio

    Build right half from top to bottom, then mirror.
    """
    if num_sides % 2 != 0:
        num_sides += 1

    half_n = num_sides // 2  # vertices on right side including top, excluding bottom

    # On the right half, going from top to bottom:
    # - First edge (from top vertex) is a top edge (length = ratio)
    # - Last edge (to bottom vertex) is a bottom edge (length = ratio)
    # - Middle edges are side edges (length = 1)

    # Number of vertices that use the side_angle:
    # Right side has half_n edges. First and last are top/bottom.
    # So we have (half_n - 2) side edges, and (half_n - 1) interior vertices on right side
    # The interior vertices (not top, not bottom) use side_angle

    num_top_edges_per_side = MISSING_TOP_EDGES // 2  # 1 on each side
    num_bottom_edges_per_side = MISSING_BOTTOM_EDGES // 2  # 1 on each side
    num_side_edges_per_side = half_n - num_top_edges_per_side - num_bottom_edges_per_side

    # Total interior angle sum = (n-2) * 180
    total_angle_sum = (num_sides - 2) * 180

    # We have:
    # - 1 top vertex (shared by left and right)
    # - 1 bottom vertex (shared by left and right)
    # - (half_n - 1) * 2 = num_sides - 2 side vertices
    # Wait, let me recalculate...

    # For 18-gon: 18 vertices total
    # Top region: vertices around top gap (let's say 3 vertices touch the 2 missing top edges)
    # Bottom region: vertices around bottom gap (3 vertices touch the 2 missing bottom edges)
    # Side vertices: 18 - 6 = 12 vertices

    num_gap_vertices = (MISSING_TOP_EDGES + 1) + (MISSING_BOTTOM_EDGES + 1)  # 3 + 3 = 6
    num_side_vertices = num_sides - num_gap_vertices  # 18 - 6 = 12

    # Side vertices use side_angle, gap vertices use computed angle
    side_angle_sum = num_side_vertices * side_angle_deg
    remaining_angle_sum = total_angle_sum - side_angle_sum
    gap_vertex_angle = remaining_angle_sum / num_gap_vertices

    print(f"Side vertices: {num_side_vertices}, angle: {side_angle_deg} deg")
    print(f"Gap vertices: {num_gap_vertices}, angle: {gap_vertex_angle:.1f} deg")
    print(f"Total angle sum: {total_angle_sum} (check: {side_angle_sum + num_gap_vertices * gap_vertex_angle:.1f})")

    # Now build the polygon by walking
    # Start at top vertex (on center line), walk clockwise (right side down, then left side up)

    # Vertex indices:
    # 0 = top center
    # 1 to half_n-1 = right side going down
    # half_n = bottom center
    # half_n+1 to num_sides-1 = left side going up

    # Edge types (for right side, going down from top):
    # Edge 0 (top->1): top edge, length = ratio
    # Edge 1 to half_n-2: side edges, length = 1
    # Edge half_n-1 (to bottom): bottom edge, length = ratio

    # For 18-gon with 2 top edges missing:
    # Top edges are 0->1 and 17->0 (indices 0 and 17)
    # Bottom edges are 8->9 and 9->10 (indices 8 and 9)

    # Let me use a cleaner approach: define which edges are top/bottom
    # and which vertices are gap vertices vs side vertices

    vertices = []
    x, y = 0.0, 0.0  # Start at top

    # Direction: start going down and to the right
    # After top vertex, first edge heads in direction that will be symmetric

    # For symmetric construction, build right half then mirror
    right_vertices = [(0.0, 0.0)]  # top vertex

    # Walking down the right side
    # Initial direction after leaving top vertex
    # The top vertex angle is gap_vertex_angle
    # We leave heading "down-right" at angle -(90 - gap_vertex_angle/2) from vertical

    direction = -math.pi/2 + math.radians(gap_vertex_angle / 2)  # heading right and down

    x, y = 0.0, 0.0

    for i in range(half_n):
        # Determine edge length
        if i < num_top_edges_per_side:
            edge_len = top_bottom_edge_ratio
        elif i >= half_n - num_bottom_edges_per_side:
            edge_len = top_bottom_edge_ratio
        else:
            edge_len = 1.0

        # Move along current direction
        x += edge_len * math.cos(direction)
        y += edge_len * math.sin(direction)
        right_vertices.append((x, y))

        # Determine turn angle at this new vertex
        # Is this a gap vertex or side vertex?
        vertex_index = i + 1  # we just arrived at vertex i+1

        if vertex_index <= num_top_edges_per_side:
            # Still in top gap region
            interior_angle = gap_vertex_angle
        elif vertex_index >= half_n - num_bottom_edges_per_side:
            # In bottom gap region
            interior_angle = gap_vertex_angle
        else:
            # Side vertex
            interior_angle = side_angle_deg

        exterior_angle = 180 - interior_angle
        direction -= math.radians(exterior_angle)

    # right_vertices now has half_n + 1 vertices: top through bottom
    # Mirror to create left half (excluding top and bottom which are on center line)

    # Check that bottom vertex is on center line (x ≈ 0)
    bottom_x = right_vertices[-1][0]
    print(f"Bottom vertex x: {bottom_x:.6f} (should be ~0 for closure)")

    # Mirror: left side vertices are right side vertices (excluding top and bottom) with negated x
    left_vertices = [(-v[0], v[1]) for v in reversed(right_vertices[1:-1])]

    # Full polygon: top, right side, bottom, left side
    vertices = right_vertices + left_vertices

    # Center and normalize
    cx = sum(v[0] for v in vertices) / len(vertices)
    cy = sum(v[1] for v in vertices) / len(vertices)
    vertices = [(v[0] - cx, v[1] - cy) for v in vertices]

    max_coord = max(max(abs(v[0]), abs(v[1])) for v in vertices)
    if max_coord > 0:
        vertices = [(v[0] / max_coord, v[1] / max_coord) for v in vertices]

    return vertices, gap_vertex_angle


def find_gap_edges(num_vertices, missing_top, missing_bottom):
    """Determine which edge indices are in the top/bottom gaps."""
    half_n = num_vertices // 2

    # Top edges: around vertex 0
    # For 2 missing top edges: edges 0 (from 0 to 1) and edge n-1 (from n-1 to 0)
    top_edges = set()
    for i in range(missing_top // 2):
        top_edges.add(i)  # edges going right from top
        top_edges.add(num_vertices - 1 - i)  # edges going left from top

    # Bottom edges: around vertex half_n
    # For 2 missing bottom edges: edges half_n-1 and half_n
    bottom_edges = set()
    for i in range(missing_bottom // 2):
        bottom_edges.add(half_n - 1 - i)  # edges arriving at bottom from right
        bottom_edges.add(half_n + i)  # edges leaving bottom to left

    return top_edges | bottom_edges


def verify_edge_lengths(vertices):
    """Return all edge lengths."""
    num_v = len(vertices)
    lengths = []
    for i in range(num_v):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % num_v]
        length = math.sqrt((v2[0] - v1[0])**2 + (v2[1] - v1[1])**2)
        lengths.append(length)
    return lengths


def main():
    vertices, gap_angle = generate_lamp_polygon(NUM_SIDES, SIDE_VERTEX_ANGLE, TOP_BOTTOM_EDGE_RATIO)
    gap_edges = find_gap_edges(len(vertices), MISSING_TOP_EDGES, MISSING_BOTTOM_EDGES)

    print(f"\nNumber of vertices: {len(vertices)}")
    print(f"Gap edges (invisible): {sorted(gap_edges)}")

    # Check edge lengths
    lengths = verify_edge_lengths(vertices)
    print(f"\nEdge lengths:")
    for i, length in enumerate(lengths):
        edge_type = "GAP" if i in gap_edges else "side"
        print(f"  Edge {i}: {length:.4f} ({edge_type})")

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10))

    # Draw visible edges
    lines = []
    num_v = len(vertices)
    for i in range(num_v):
        if i not in gap_edges:
            v1 = vertices[i]
            v2 = vertices[(i + 1) % num_v]
            lines.append([v1, v2])

    line_collection = LineCollection(lines, colors='black', linewidths=2)
    ax.add_collection(line_collection)

    # Draw gap edges as dashed
    gap_lines = []
    for i in gap_edges:
        v1 = vertices[i]
        v2 = vertices[(i + 1) % num_v]
        gap_lines.append([v1, v2])
    gap_collection = LineCollection(gap_lines, colors='red', linewidths=1, linestyles='dashed')
    ax.add_collection(gap_collection)

    # Draw vertices
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    ax.scatter(xs, ys, c='blue', s=30, zorder=5)

    for i, (x, y) in enumerate(vertices):
        ax.annotate(f'{i}', (x, y), textcoords="offset points",
                   xytext=(5, 5), fontsize=8)

    ax.set_aspect('equal')
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.axis('off')

    ax.set_title(f'{NUM_SIDES}-gon | Side angle: {SIDE_VERTEX_ANGLE} deg | '
                 f'Gap angle: {gap_angle:.1f} deg\n'
                 f'Gap edge ratio: {TOP_BOTTOM_EDGE_RATIO}')

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
