"""
Load and validate lamp_config.toml.
"""

import sys
import tomllib
from pathlib import Path

from lamp_geometry import PolygonSpec

CONFIG_PATH = Path(__file__).parent / "lamp_config.toml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load and validate the TOML configuration file."""
    if not path.exists():
        print(f"Config not found: {path}", file=sys.stderr)
        raise SystemExit(1)

    with open(path, "rb") as f:
        cfg = tomllib.load(f)

    _validate(cfg)
    return cfg


def _validate(cfg: dict):
    required_sections = ["bases", "proportions", "polygon", "accordion", "pattern"]
    for s in required_sections:
        if s not in cfg:
            print(f"Missing config section: [{s}]", file=sys.stderr)
            raise SystemExit(1)

    active = cfg.get("active_base", "small")
    if active not in cfg["bases"]:
        print(f"active_base '{active}' not found in [bases]", file=sys.stderr)
        raise SystemExit(1)


def get_active_base(cfg: dict) -> tuple[str, dict]:
    """Return (name, base_dict) for the active base."""
    name = cfg["active_base"]
    return name, cfg["bases"][name]


def get_ratios(cfg: dict) -> tuple[float, float]:
    """Return (base_to_shade_height, shade_width_to_height) as floats."""
    p = cfg["proportions"]
    bsh = p["base_to_shade_height"]
    swh = p["shade_width_to_height"]
    return bsh[0] / bsh[1], swh[0] / swh[1]


def get_polygon_spec(cfg: dict) -> PolygonSpec:
    p = cfg["polygon"]
    return PolygonSpec(
        n_sides=p["n_sides"],
        side_angle_deg=p["side_angle_deg"],
        gap_edge_ratio=p["gap_edge_ratio"],
        n_regular_edges=p["n_regular_edges"],
        n_gap_edges=p["n_gap_edges"],
    )


def get_diamond_config(cfg: dict) -> dict | None:
    """Return the [diamond] dict, or None if absent or disabled."""
    diamond = cfg.get("diamond")
    if diamond is None or not diamond.get("enabled", True):
        return None
    return diamond
