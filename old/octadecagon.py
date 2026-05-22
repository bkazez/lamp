#!/usr/bin/env python3
"""
Lamp silhouette generator (18-gon style).
- Top 2 and bottom 2 edges are invisible (but vertices exist)
- All visible side edges have equal length
- Top/bottom (invisible) edge lengths are adjustable
- Side vertex angles are adjustable
- Top/bottom vertex angles adjust automatically to close the polygon
"""

import math
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.widgets import Slider

# Configuration
INITIAL_NUM_SIDES = 18
INITIAL_SIDE_ANGLE = 160  # degrees
INITIAL_GAP_EDGE_RATIO = 0.5  # ratio of gap edge length to side edge length
MISSING_TOP_EDGES = 2
MISSING_BOTTOM_EDGES = 2
FIGURE_SIZE = (10, 10)
LINE_WIDTH = 2
LINE_COLOR = "black"
VERTEX_COLOR = "blue"
VERTEX_SIZE = 30

# Slider configuration
SLIDER_COLOR = "lightgoldenrodyellow"
SLIDER_HEIGHT = 0.03

# Constraints
MIN_NUM_SIDES = 8
MAX_NUM_SIDES = 36


def generate_lamp_polygon(num_sides, side_angle_deg, gap_edge_ratio):
    """
    Generate a symmetric polygon where:
    - Side vertices have the specified interior angle
    - Top/bottom (gap) vertices have angles computed to close the polygon
    - Side edges all have length 1
    - Gap edges have length = gap_edge_ratio
    """
    if num_sides % 2 != 0:
        num_sides += 1

    half_n = num_sides // 2

    num_top_edges_per_side = MISSING_TOP_EDGES // 2
    num_bottom_edges_per_side = MISSING_BOTTOM_EDGES // 2

    # Calculate gap vertex angle from total angle sum
    total_angle_sum = (num_sides - 2) * 180
    num_gap_vertices = (MISSING_TOP_EDGES + 1) + (MISSING_BOTTOM_EDGES + 1)
    num_side_vertices = num_sides - num_gap_vertices

    side_angle_sum = num_side_vertices * side_angle_deg
    remaining_angle_sum = total_angle_sum - side_angle_sum
    gap_vertex_angle = remaining_angle_sum / num_gap_vertices

    # Build right half from top to bottom
    right_vertices = [(0.0, 0.0)]

    direction = -math.pi/2 + math.radians(gap_vertex_angle / 2)
    x, y = 0.0, 0.0

    for i in range(half_n):
        # Determine edge length
        if i < num_top_edges_per_side:
            edge_len = gap_edge_ratio
        elif i >= half_n - num_bottom_edges_per_side:
            edge_len = gap_edge_ratio
        else:
            edge_len = 1.0

        x += edge_len * math.cos(direction)
        y += edge_len * math.sin(direction)
        right_vertices.append((x, y))

        vertex_index = i + 1

        if vertex_index <= num_top_edges_per_side:
            interior_angle = gap_vertex_angle
        elif vertex_index >= half_n - num_bottom_edges_per_side:
            interior_angle = gap_vertex_angle
        else:
            interior_angle = side_angle_deg

        exterior_angle = 180 - interior_angle
        direction -= math.radians(exterior_angle)

    # Mirror to create left half
    left_vertices = [(-v[0], v[1]) for v in reversed(right_vertices[1:-1])]
    vertices = right_vertices + left_vertices

    # Center and normalize
    cx = sum(v[0] for v in vertices) / len(vertices)
    cy = sum(v[1] for v in vertices) / len(vertices)
    vertices = [(v[0] - cx, v[1] - cy) for v in vertices]

    max_coord = max(max(abs(v[0]), abs(v[1])) for v in vertices)
    if max_coord > 0:
        vertices = [(v[0] / max_coord, v[1] / max_coord) for v in vertices]

    return vertices, gap_vertex_angle


def find_gap_edges(num_vertices):
    """Determine which edge indices are in the top/bottom gaps."""
    half_n = num_vertices // 2

    top_edges = set()
    for i in range(MISSING_TOP_EDGES // 2):
        top_edges.add(i)
        top_edges.add(num_vertices - 1 - i)

    bottom_edges = set()
    for i in range(MISSING_BOTTOM_EDGES // 2):
        bottom_edges.add(half_n - 1 - i)
        bottom_edges.add(half_n + i)

    return top_edges | bottom_edges


class LampViewer:
    """Interactive lamp silhouette viewer with sliders."""

    def __init__(self):
        self.num_sides = INITIAL_NUM_SIDES
        self.side_angle = INITIAL_SIDE_ANGLE
        self.gap_edge_ratio = INITIAL_GAP_EDGE_RATIO
        self.gap_angle = INITIAL_SIDE_ANGLE

        self.fig, self.ax = plt.subplots(figsize=FIGURE_SIZE)
        plt.subplots_adjust(bottom=0.25)

        self.line_collection = None
        self.gap_collection = None
        self.scatter = None

        self._create_sliders()
        self._draw()

    def _create_sliders(self):
        """Create the control sliders."""
        ax_num_sides = plt.axes([0.2, 0.15, 0.6, SLIDER_HEIGHT], facecolor=SLIDER_COLOR)
        ax_side_angle = plt.axes([0.2, 0.10, 0.6, SLIDER_HEIGHT], facecolor=SLIDER_COLOR)
        ax_gap_ratio = plt.axes([0.2, 0.05, 0.6, SLIDER_HEIGHT], facecolor=SLIDER_COLOR)

        self.slider_num_sides = Slider(
            ax_num_sides, "Sides", MIN_NUM_SIDES, MAX_NUM_SIDES,
            valinit=INITIAL_NUM_SIDES, valstep=2
        )
        self.slider_side_angle = Slider(
            ax_side_angle, "Side Angle", 140, 175,
            valinit=INITIAL_SIDE_ANGLE, valstep=1
        )
        self.slider_gap_ratio = Slider(
            ax_gap_ratio, "Gap Edge", 0.1, 2.0,
            valinit=INITIAL_GAP_EDGE_RATIO, valstep=0.05
        )

        self.slider_num_sides.on_changed(self._on_slider_change)
        self.slider_side_angle.on_changed(self._on_slider_change)
        self.slider_gap_ratio.on_changed(self._on_slider_change)

    def _on_slider_change(self, _val):
        """Handle slider value changes."""
        self.num_sides = int(self.slider_num_sides.val)
        self.side_angle = self.slider_side_angle.val
        self.gap_edge_ratio = self.slider_gap_ratio.val
        self._draw()

    def _draw(self):
        """Draw the lamp silhouette with current parameters."""
        if self.line_collection is not None:
            self.line_collection.remove()
        if self.gap_collection is not None:
            self.gap_collection.remove()
        if self.scatter is not None:
            self.scatter.remove()

        vertices, gap_angle = generate_lamp_polygon(
            self.num_sides, self.side_angle, self.gap_edge_ratio
        )
        self.gap_angle = gap_angle

        gap_edges = find_gap_edges(len(vertices))
        num_v = len(vertices)

        # Draw visible edges (solid black)
        lines = []
        for i in range(num_v):
            if i not in gap_edges:
                v1 = vertices[i]
                v2 = vertices[(i + 1) % num_v]
                lines.append([v1, v2])

        self.line_collection = LineCollection(lines, colors=LINE_COLOR, linewidths=LINE_WIDTH)
        self.ax.add_collection(self.line_collection)

        # Draw gap edges (dashed red)
        gap_lines = []
        for i in gap_edges:
            v1 = vertices[i]
            v2 = vertices[(i + 1) % num_v]
            gap_lines.append([v1, v2])

        self.gap_collection = LineCollection(
            gap_lines, colors='red', linewidths=1, linestyles='dashed'
        )
        self.ax.add_collection(self.gap_collection)

        # Draw vertices
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        self.scatter = self.ax.scatter(xs, ys, c=VERTEX_COLOR, s=VERTEX_SIZE, zorder=5)

        self.ax.set_aspect("equal")
        self.ax.set_xlim(-1.3, 1.3)
        self.ax.set_ylim(-1.3, 1.3)
        self.ax.axis("off")

        self.ax.set_title(
            f"{self.num_sides}-gon | "
            f"Side angle: {self.side_angle:.0f} deg | "
            f"Gap angle: {self.gap_angle:.1f} deg | "
            f"Gap edge: {self.gap_edge_ratio:.2f}x"
        )

        self.fig.canvas.draw_idle()

    def show(self):
        """Display the interactive viewer."""
        plt.show()


def main():
    """Launch the interactive lamp viewer."""
    viewer = LampViewer()
    viewer.show()


if __name__ == "__main__":
    main()
