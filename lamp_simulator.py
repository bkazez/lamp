#!/usr/bin/env python3
"""
3D fold simulator for Klint-style accordion lampshade.

Builds a mesh of rigid faces from the diamond fold pattern, places vertices
on dome-profile rings, replicates one pleat around the ring, and visualizes
with matplotlib.

Usage:
  python3 lamp_simulator.py [--base NAME] [--save FILE]
"""

import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import plotly.graph_objects as go

OUTPUT_DIR = Path(__file__).parent

from lamp_config_loader import load_config, get_ratios, get_polygon_spec, get_diamond_config
from lamp_geometry import (
    compute_polygon, compute_shade, compute_paper, compute_diamond_grid,
)


# ============================================================================
# Dome profile
# ============================================================================

def dome_profile(shade, n_rows):
    """
    Compute heights and circumferences for n_rows+1 row lines.

    Parametrizes the dome as an ellipse and samples at uniform angle
    intervals. This clusters rows near the poles (where curvature is
    highest), giving a much better piecewise-linear approximation than
    uniform height spacing.

    Returns (heights, circumferences) arrays of length n_rows+1.
    """
    base_R = shade.polygon_perimeter / (2 * np.pi)
    max_R = shade.shade_circumference / (2 * np.pi)
    half_h = shade.shade_height / 2

    theta = np.linspace(-np.pi / 2, np.pi / 2, n_rows + 1)
    heights = half_h + half_h * np.sin(theta)
    radii = base_R + (max_R - base_R) * np.cos(theta)
    return heights, 2 * np.pi * radii


# ============================================================================
# Mesh: one pleat placed on the dome
# ============================================================================

def build_pleat_3d(paper, shade, n_rows):
    """
    Build 3D vertices and faces for one pleat on the dome.

    3 vertices per row (left edge, midpoint, right edge), 4 triangles per
    row band (2 per half-pleat). Vertices placed on circular rings whose
    radii follow the dome profile.
    """
    fw = paper.fold_width
    half_fw = fw / 2.0
    n_pleats = paper.n_pleats
    sector = 2 * np.pi / n_pleats

    heights, circs = dome_profile(shade, n_rows)

    verts = np.zeros(((n_rows + 1) * 3, 3))

    for i in range(n_rows + 1):
        circ = circs[i]
        chord = circ / n_pleats
        R_edge = chord / (2 * np.sin(np.pi / n_pleats))
        ha = np.arcsin(np.clip(circ / paper.strip_length, -1, 1))
        R_mid = R_edge - half_fw * np.cos(ha)

        b = i * 3
        verts[b + 0] = [R_edge * np.cos(-sector / 2), heights[i],
                        R_edge * np.sin(-sector / 2)]
        verts[b + 1] = [R_mid, heights[i], 0.0]
        verts[b + 2] = [R_edge * np.cos(sector / 2), heights[i],
                        R_edge * np.sin(sector / 2)]

    faces = []
    for i in range(n_rows):
        b = i * 3
        t = (i + 1) * 3
        faces.append((b, b + 1, t + 1))
        faces.append((b, t + 1, t))
        faces.append((b + 1, b + 2, t + 2))
        faces.append((b + 1, t + 2, t + 1))

    return verts, faces


# ============================================================================
# Ring replication
# ============================================================================

def replicate_around_ring(verts_3d, faces, n_pleats):
    """Replicate one pleat n_pleats times around the Y axis."""
    n_verts = len(verts_3d)
    all_verts = []
    all_faces = []

    for i in range(n_pleats):
        angle = i * 2 * np.pi / n_pleats
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        rot = np.array([[cos_a, 0, sin_a], [0, 1, 0], [-sin_a, 0, cos_a]])
        all_verts.append(verts_3d @ rot.T)
        offset = i * n_verts
        for face in faces:
            all_faces.append(tuple(v + offset for v in face))

    return np.vstack(all_verts), all_faces


# ============================================================================
# Visualization
# ============================================================================

def save_cross_section(shade, n_rows, save_path):
    """Save a side-profile cross-section plot showing the dome shape."""
    heights, circs = dome_profile(shade, n_rows)
    radii = circs / (2 * np.pi)

    base_R = shade.polygon_perimeter / (2 * np.pi)
    max_R = shade.shade_circumference / (2 * np.pi)
    half_h = shade.shade_height / 2
    theta_smooth = np.linspace(-np.pi / 2, np.pi / 2, 200)
    t_smooth = half_h + half_h * np.sin(theta_smooth)
    r_smooth = base_R + (max_R - base_R) * np.cos(theta_smooth)

    fig, ax = plt.subplots(figsize=(6, 8))
    ax.plot(r_smooth, t_smooth, "k-", alpha=0.3, label="Ellipse (continuous)")
    ax.plot(-r_smooth, t_smooth, "k-", alpha=0.3)
    ax.plot(radii, heights, "ro-", markersize=5, label="Edge vertices")
    ax.plot(-radii, heights, "ro-", markersize=5)
    ax.set_xlabel("Radius (inches)")
    ax.set_ylabel("Height (inches)")
    ax.set_title("Dome Cross Section (side view)")
    ax.set_aspect("equal")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Cross section: {save_path}")


def compute_face_colors(all_verts, all_faces, light_dir=None):
    """Compute per-face colors using basic diffuse shading."""
    if light_dir is None:
        light_dir = np.array([0.3, 1.0, 0.2])
    light_dir = light_dir / np.linalg.norm(light_dir)

    colors = []
    base = np.array([0.96, 0.90, 0.78])
    for face in all_faces:
        v0, v1, v2 = all_verts[face[0]], all_verts[face[1]], all_verts[face[2]]
        normal = np.cross(v1 - v0, v2 - v0)
        norm_len = np.linalg.norm(normal)
        if norm_len > 1e-10:
            normal /= norm_len
        brightness = 0.4 + 0.6 * max(0, np.dot(normal, light_dir))
        colors.append(base * brightness)
    return colors


def save_top_view(all_verts, all_faces, save_path):
    """Save a top-down view of the lampshade with shading."""
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection="3d")

    light_dir = np.array([0.2, 1.0, 0.3])
    face_colors = compute_face_colors(all_verts, all_faces, light_dir)

    polygons = [[all_verts[v] for v in face] for face in all_faces]
    ax.add_collection3d(Poly3DCollection(
        polygons, alpha=0.9, facecolors=face_colors,
        edgecolor="#aaaaaa", linewidth=0.15,
    ))

    xs, ys, zs = all_verts[:, 0], all_verts[:, 1], all_verts[:, 2]
    ranges = [xs.max() - xs.min(), ys.max() - ys.min(), zs.max() - zs.min()]
    max_range = max(ranges) / 2 * 1.1
    mid = [(xs.max() + xs.min()) / 2, (ys.max() + ys.min()) / 2,
           (zs.max() + zs.min()) / 2]
    ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
    ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
    ax.set_zlim(mid[2] - max_range, mid[2] + max_range)
    ax.set_box_aspect([1, 1, 1])
    ax.set_title("Top View", fontsize=9)
    ax.view_init(elev=70, azim=0)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Top view:      {save_path}")


def export_html(all_verts, all_faces, title, html_path):
    """Export an interactive 3D view as a self-contained HTML file."""
    i_idx = [face[0] for face in all_faces]
    j_idx = [face[1] for face in all_faces]
    k_idx = [face[2] for face in all_faces]

    light_dir = np.array([0.3, 1.0, 0.2])
    light_dir /= np.linalg.norm(light_dir)
    intensities = []
    for face in all_faces:
        v0, v1, v2 = all_verts[face[0]], all_verts[face[1]], all_verts[face[2]]
        normal = np.cross(v1 - v0, v2 - v0)
        norm_len = np.linalg.norm(normal)
        if norm_len > 1e-10:
            normal /= norm_len
        intensities.append(0.4 + 0.6 * max(0, float(np.dot(normal, light_dir))))

    fig = go.Figure(data=[go.Mesh3d(
        x=all_verts[:, 0],
        y=all_verts[:, 2],
        z=all_verts[:, 1],
        i=i_idx, j=j_idx, k=k_idx,
        facecolor=[f"rgb({int(v*245)},{int(v*230)},{int(v*200)})" for v in intensities],
        flatshading=True,
        hoverinfo="skip",
    )])

    max_range = max(
        all_verts[:, 0].max() - all_verts[:, 0].min(),
        all_verts[:, 1].max() - all_verts[:, 1].min(),
        all_verts[:, 2].max() - all_verts[:, 2].min(),
    ) / 2 * 1.1

    fig.update_layout(
        title=title,
        scene=dict(
            aspectmode="cube",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.5, y=1.0, z=0.8)),
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    fig.write_html(str(html_path), include_plotlyjs=True)
    print(f"  3D HTML:       {html_path}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="3D fold simulation of Klint lampshade")
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

    diamond_cfg = get_diamond_config(cfg)
    if diamond_cfg is None:
        print("Diamond folds disabled. Set [diamond] enabled = true in config.")
        raise SystemExit(1)

    n_rows = diamond_cfg["n_rows"]
    base = cfg["bases"][base_name]
    shade = compute_shade(base["diameter"], base["height"], bsh_ratio, swh_ratio, poly)
    acc = cfg["accordion"]
    paper = compute_paper(shade, acc["n_pleats"], acc["opening_fraction"])
    grid = compute_diamond_grid(paper, n_rows)

    print("FOLD SIMULATION")
    print(f"  Base:          {base_name}")
    print(f"  Shade:         {shade.shade_height:.1f}\" tall, {shade.shade_diameter:.1f}\" diameter")
    print(f"  Paper:         {paper.strip_length:.1f}\" x {paper.paper_height:.1f}\"")
    print(f"  Pleats:        {paper.n_pleats}, fold width {paper.fold_width:.2f}\"")
    print(f"  Diamond grid:  {n_rows} rows, row height {grid.row_height:.2f}\"")
    print(f"  Diagonal:      {grid.diagonal_angle_deg:.1f} deg, {grid.diagonal_length:.2f}\" long")

    heights, circs = dome_profile(shade, n_rows)
    print(f"\n  Dome profile:")
    for r in range(n_rows + 1):
        R = circs[r] / (2 * np.pi)
        print(f"    Row {r:2d} (h={heights[r]:5.1f}\"): C={circs[r]:6.1f}\"  R={R:5.1f}\"")

    verts_3d, faces = build_pleat_3d(paper, shade, n_rows)
    all_verts, all_faces = replicate_around_ring(verts_3d, faces, paper.n_pleats)
    print(f"\n  Mesh: {len(all_verts)} verts, {len(all_faces)} faces\n")

    cross_section_path = str(OUTPUT_DIR / f"cross_section_{base_name}.png")
    save_cross_section(shade, n_rows, cross_section_path)

    top_view_path = str(OUTPUT_DIR / f"top_view_{base_name}.png")
    save_top_view(all_verts, all_faces, top_view_path)

    title = (f"Klint: {base_name}, {paper.n_pleats} pleats, {n_rows} rows")
    html_path = OUTPUT_DIR / f"lampshade_{base_name}.html"
    export_html(all_verts, all_faces, title, html_path)


if __name__ == "__main__":
    main()
