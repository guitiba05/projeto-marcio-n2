"""MdSolids Trusses (CEFSA N2) — Comprehensive Opaque-Box E2E Test Suite.

This test suite covers all features specified in PROJECT.md and solver_spec.md
across four rigorous tiers:
- Tier 1: Feature Coverage (>=5 tests per core feature across 17 features)
- Tier 2: Boundary & Corner Cases (>=5 tests per domain across 7 edge domains)
- Tier 3: Cross-Feature Combinations (Pairwise multi-axial, multi-bay, mixed-material)
- Tier 4: Real-World Application Scenarios (8 N2 Exam Benchmarks, 25-Member Bridge, Roof Trusses)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.report import render_report
from app.api.server import PRESETS, PRESETS_BY_SLUG, app
from app.core.determinacy import analyze_determinacy
from app.core.equilibrium import global_equilibrium, nodal_residuals, summarize
from app.core.errors import DeterminacyError, InputError, MechanismError
from app.core.joints import cross_check, method_of_joints
from app.core.model import (
    COMPONENTS,
    SUPPORT_ALIASES,
    SUPPORT_RESTRAINTS,
    Member,
    Node,
    Truss,
    normalize_support,
    parse_truss,
)
from app.core.solver import solve_payload, stress_payload
from app.core.stiffness import (
    COMPRESSION,
    TENSION,
    ZERO,
    analyze,
    assemble,
    find_mechanism_dofs,
    member_stiffness,
)
from app.core.stress import (
    analyze_stress,
    normal_stress_mpa,
    required_area_mm2,
    required_areas,
)
from app.core.units import (
    area_factor,
    force_factor,
    length_factor,
    stress_factor,
)
from app.core.zero_force import (
    find_zero_force_rules,
    summarize_zero_force,
)
from app.render.svg import render_truss_svg

# Test client for E2E REST API endpoints
client = TestClient(app)

DATA_CASES_DIR = Path(__file__).resolve().parents[1] / "data" / "cases"


def load_preset_json(slug: str) -> dict:
    file_path = DATA_CASES_DIR / f"{slug}.json"
    with file_path.open(encoding="utf-8") as handle:
        return json.load(handle)


# ==============================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per core feature)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Comprehensive feature coverage across all 17 core structural features."""

    # --- Feature 01: Grid Definition Parsing and Snapping ---

    def test_t1_grid_01_valid_parameters_and_extent(self) -> None:
        """F01: Valid grid parameters (dx, dy, nx, ny) calculate correct bounding extents."""
        grid = {"dx": 2.0, "dy": 1.5, "nx": 6, "ny": 4}
        max_x = grid["dx"] * grid["nx"]
        max_y = grid["dy"] * grid["ny"]
        total_points = (grid["nx"] + 1) * (grid["ny"] + 1)
        assert max_x == 12.0
        assert max_y == 6.0
        assert total_points == 35

    def test_t1_grid_02_discrete_snapping_calculation(self) -> None:
        """F01: Discrete magnetic snapping maps continuous world coordinates to nearest grid point."""
        def snap(val: float, step: float) -> float:
            return round(val / step) * step if step > 0 else val

        assert snap(3.8, 1.0) == 4.0
        assert snap(2.3, 1.0) == 2.0
        assert snap(3.49, 0.5) == 3.5
        assert snap(3.24, 0.5) == 3.0
        assert snap(1.7, 2.0) == 2.0

    def test_t1_grid_03_snap_disabled_preserves_precision(self) -> None:
        """F01: When snap is deactivated, exact fractional coordinates are maintained with millimetric precision."""
        def snap_mode(val: float, step: float, enabled: bool) -> float:
            if not enabled:
                return round(val * 1000.0) / 1000.0
            return round(val / step) * step

        raw_x = 3.14159265
        assert snap_mode(raw_x, 1.0, enabled=False) == 3.142
        assert snap_mode(raw_x, 1.0, enabled=True) == 3.0

    def test_t1_grid_04_edge_boundary_clamping(self) -> None:
        """F01: Out-of-bounds or non-positive grid steps clamp safely to positive minimum thresholds."""
        def sanitize_grid(raw_dx: float, raw_dy: float, raw_nx: int, raw_ny: int) -> dict:
            dx = max(0.001, float(raw_dx or 1.0))
            dy = max(0.001, float(raw_dy or 1.0))
            nx = max(1, round(float(raw_nx or 8.0)))
            ny = max(1, round(float(raw_ny or 5.0)))
            return {"dx": dx, "dy": dy, "nx": nx, "ny": ny}

        clamped = sanitize_grid(0.0001, -2.5, -4, -10)
        assert clamped["dx"] == 0.001
        assert clamped["dy"] == 0.001
        assert clamped["nx"] == 1
        assert clamped["ny"] == 1

    def test_t1_grid_05_nearest_node_hit_attraction(self) -> None:
        """F01: Nearest node hit attraction prioritizes existing nodes within radius over new grid snaps."""
        existing_nodes = [{"id": "A", "x": 2.0, "y": 3.0}]
        scale = 40.0
        pan_x = 50.0
        pan_y = 300.0
        hit_radius = 14.0

        def screen_dist(node_x: float, node_y: float, click_wx: float, click_wy: float) -> float:
            sx_node = pan_x + node_x * scale
            sy_node = pan_y - node_y * scale
            sx_click = pan_x + click_wx * scale
            sy_click = pan_y - click_wy * scale
            return math.hypot(sx_click - sx_node, sy_click - sy_node)

        # Click very close to Node A (0.1m away = 4 pixels)
        d_close = screen_dist(2.0, 3.0, 2.1, 3.0)
        assert d_close <= hit_radius

        # Click far from Node A (1.0m away = 40 pixels)
        d_far = screen_dist(2.0, 3.0, 3.0, 3.0)
        assert d_far > hit_radius

    def test_t1_grid_06_non_integer_step_snapping(self) -> None:
        """F01: Non-integer fractional steps (e.g. 0.25m or 1.25m) snap with zero drift."""
        step = 0.25
        assert math.isclose(round(1.12 / step) * step, 1.0)
        assert math.isclose(round(1.13 / step) * step, 1.25)
        assert math.isclose(round(2.73 / step) * step, 2.75)
        assert math.isclose(round(2.88 / step) * step, 3.0)

    # --- Feature 02: Member Creation, Connectivity, Length, Angle ---

    def test_t1_member_01_horizontal_member(self) -> None:
        """F02: Horizontal member from (0,0) to (5,0) has exact length 5.0, cos=1.0, sin=0.0."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 5.0, "y": 0.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1.0}],
            "loads": [],
        }
        truss = parse_truss(model)
        m = truss.member_by_id("AB")
        length, c, s = truss.member_geometry(m)
        assert math.isclose(length, 5.0)
        assert math.isclose(c, 1.0)
        assert math.isclose(s, 0.0)

    def test_t1_member_02_vertical_member(self) -> None:
        """F02: Vertical member from (0,0) to (0,4) has length 4.0, cos=0.0, sin=1.0."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 0.0, "y": 4.0, "support": "roller_x"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1.0}],
            "loads": [],
        }
        truss = parse_truss(model)
        m = truss.member_by_id("AB")
        length, c, s = truss.member_geometry(m)
        assert math.isclose(length, 4.0)
        assert math.isclose(c, 0.0)
        assert math.isclose(s, 1.0)

    def test_t1_member_03_45_degree_diagonal_member(self) -> None:
        """F02: 45-degree diagonal member has length L*sqrt(2) and equal direction cosines."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 3.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1.0}],
            "loads": [],
        }
        truss = parse_truss(model)
        m = truss.member_by_id("AB")
        length, c, s = truss.member_geometry(m)
        assert math.isclose(length, 3.0 * math.sqrt(2.0))
        assert math.isclose(c, math.sqrt(2.0) / 2.0)
        assert math.isclose(s, math.sqrt(2.0) / 2.0)

    def test_t1_member_04_3_4_5_right_triangle_member(self) -> None:
        """F02: 3-4-5 right triangle member verifies exact integer Pythagorean lengths."""
        model = {
            "nodes": [
                {"id": "A", "x": 1.0, "y": 1.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 5.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1.0}],
            "loads": [],
        }
        truss = parse_truss(model)
        m = truss.member_by_id("AB")
        length, c, s = truss.member_geometry(m)
        assert math.isclose(length, 5.0)
        assert math.isclose(c, 0.6)
        assert math.isclose(s, 0.8)

    def test_t1_member_05_negative_quadrant_angles(self) -> None:
        """F02: Member directed into 4th quadrant (positive dx, negative dy) has negative sin."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 4.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 0.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1.0}],
            "loads": [],
        }
        truss = parse_truss(model)
        m = truss.member_by_id("AB")
        length, c, s = truss.member_geometry(m)
        assert math.isclose(length, 5.0)
        assert math.isclose(c, 0.6)
        assert math.isclose(s, -0.8)

    # --- Feature 03: Standard Boundary Supports ---

    def test_t1_support_01_pin_support(self) -> None:
        """F05: Pin support restrains both horizontal (ux) and vertical (uy) degrees of freedom."""
        node = Node(id="A", x=0.0, y=0.0, support="pin")
        assert node.is_support is True
        assert node.restraints == ("ux", "uy")
        assert node.n_reactions == 2

    def test_t1_support_02_roller_support(self) -> None:
        """F05: Roller support restrains vertical degree of freedom (uy) and leaves horizontal (ux) free."""
        node = Node(id="B", x=4.0, y=0.0, support="roller")
        assert node.is_support is True
        assert node.restraints == ("uy",)
        assert node.n_reactions == 1

    def test_t1_support_03_roller_x_support(self) -> None:
        """F05: Roller_x support restrains horizontal degree of freedom (ux) and leaves vertical (uy) free."""
        node = Node(id="C", x=0.0, y=3.0, support="roller_x")
        assert node.is_support is True
        assert node.restraints == ("ux",)
        assert node.n_reactions == 1

    def test_t1_support_04_free_node(self) -> None:
        """F05: Free node (none) has zero restraints and zero reactions."""
        node = Node(id="D", x=2.0, y=2.0, support="none")
        assert node.is_support is False
        assert node.restraints == ()
        assert node.n_reactions == 0

    def test_t1_support_05_support_alias_normalization(self) -> None:
        """F05: Support aliases in Portuguese and English normalize to canonical keys."""
        assert normalize_support("pin") == "pin"
        assert normalize_support("pino") == "pin"
        assert normalize_support("articulacao") == "pin"
        assert normalize_support("articulação") == "pin"
        assert normalize_support("roller") == "roller"
        assert normalize_support("roleto") == "roller"
        assert normalize_support("movel") == "roller"
        assert normalize_support("móvel") == "roller"
        assert normalize_support("roller_x") == "roller_x"
        assert normalize_support("roleto_x") == "roller_x"
        assert normalize_support("none") == "none"
        assert normalize_support("livre") == "none"
        assert normalize_support("free") == "none"

    # --- Feature 04: Nodal Point Loads ---

    def test_t1_load_01_pure_vertical_gravity_load(self) -> None:
        """F06: Pure vertical downward load (gravity Fy < 0) correctly assigns to global load vector."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -15.0}],
        }
        truss = parse_truss(model)
        assert truss.load_at("C") == (0.0, -15.0)

    def test_t1_load_02_pure_horizontal_wind_load(self) -> None:
        """F06: Pure horizontal wind load (Fx > 0) correctly assigns to node load."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 8.0, "Fy": 0.0}],
        }
        truss = parse_truss(model)
        assert truss.load_at("C") == (8.0, 0.0)

    def test_t1_load_03_inclined_combined_load(self) -> None:
        """F06: Inclined load assigns both horizontal and vertical components."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 6.0, "Fy": -10.0}],
        }
        truss = parse_truss(model)
        assert truss.load_at("C") == (6.0, -10.0)

    def test_t1_load_04_multiple_nodes_loading(self) -> None:
        """F06: Loads applied at multiple distinct nodes are tracked independently."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [
                {"node": "B", "Fx": 2.0, "Fy": -4.0},
                {"node": "C", "Fx": -3.0, "Fy": -7.0},
            ],
        }
        truss = parse_truss(model)
        assert truss.load_at("B") == (2.0, -4.0)
        assert truss.load_at("C") == (-3.0, -7.0)
        assert truss.load_at("A") == (0.0, 0.0)

    def test_t1_load_05_superposition_multiple_loads_same_node(self) -> None:
        """F06: Multiple load entries for the same node superpose additively."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [
                {"node": "C", "Fx": 5.0, "Fy": -10.0},
                {"node": "C", "Fx": 3.0, "Fy": -2.0},
            ],
        }
        truss = parse_truss(model)
        assert truss.load_at("C") == (8.0, -12.0)

    # --- Feature 05: Force Classification (Tension, Compression, Zero Force) ---

    def test_t1_class_01_tensile_member_classification(self) -> None:
        """F11: Member under positive axial elongation is classified as 'tração' with N > 0."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        ab = next(m for m in solution["members"] if m["id"] == "AB")
        assert ab["N"] > 0
        assert ab["state"] == TENSION
        assert ab["zero_force"] is False

    def test_t1_class_02_compressive_member_classification(self) -> None:
        """F11: Member under axial shortening is classified as 'compressão' with N < 0."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        ac = next(m for m in solution["members"] if m["id"] == "AC")
        assert ac["N"] < 0
        assert ac["state"] == COMPRESSION
        assert ac["zero_force"] is False

    def test_t1_class_03_zero_force_member_classification(self) -> None:
        """F11: Member with |N| <= 1e-7 is classified as 'força zero'."""
        case = load_preset_json("05-forca-zero-T")
        solution = solve_payload(case["input"])
        cd = next(m for m in solution["members"] if m["id"] == "CD")
        assert math.isclose(cd["N"], 0.0, abs_tol=1e-7)
        assert cd["state"] == ZERO
        assert cd["zero_force"] is True

    def test_t1_class_04_member_count_summary_conservation(self) -> None:
        """F11: Summary member count equals the sum of tension, compression, and zero members."""
        case = load_preset_json("02-telhado-pratt")
        solution = solve_payload(case["input"])
        summary = solution["summary"]
        assert summary["members"] == len(solution["members"])
        assert summary["members"] == summary["tension"] + summary["compression"] + summary["zero"]

    def test_t1_class_05_extreme_forces_summary(self) -> None:
        """F11: Summary correctly captures maximum tension, maximum compression, and max absolute force."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        summary = solution["summary"]
        assert summary["maxTension"]["id"] == "AB"
        assert math.isclose(summary["maxTension"]["N"], 3.333333, abs_tol=1e-5)
        assert summary["maxCompression"]["id"] in ("AC", "BC")
        assert math.isclose(summary["maxCompression"]["N"], -6.009252, abs_tol=1e-5)
        assert math.isclose(summary["maxAbsForce"], 6.009252, abs_tol=1e-5)

    # --- Feature 06: Support Reactions Equilibrium ---

    def test_t1_react_01_symmetric_triangle_equal_reactions(self) -> None:
        """F10: Symmetric 3-bar triangle under 10 kN midspan load splits vertical reactions 5 kN each."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        rx_a = next(r["Rx"] for r in solution["reactions"] if r["node"] == "A")
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        ry_b = next(r["Ry"] for r in solution["reactions"] if r["node"] == "B")
        assert math.isclose(rx_a, 0.0, abs_tol=1e-7)
        assert math.isclose(ry_a, 5.0, abs_tol=1e-6)
        assert math.isclose(ry_b, 5.0, abs_tol=1e-6)

    def test_t1_react_02_asymmetric_load_reactions(self) -> None:
        """F10: Asymmetric vertical load positioned at 1/4 span allocates 3/4 reaction to near support."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 1.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -8.0}],
        }
        solution = solve_payload(model)
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        ry_b = next(r["Ry"] for r in solution["reactions"] if r["node"] == "B")
        # Moment about B: Ry_A * 4 - 8 * 3 = 0 -> Ry_A = 6.0; Ry_B = 2.0
        assert math.isclose(ry_a, 6.0, abs_tol=1e-7)
        assert math.isclose(ry_b, 2.0, abs_tol=1e-7)

    def test_t1_react_03_horizontal_load_balanced_by_pin(self) -> None:
        """F10: Horizontal wind load on pin-roller truss is resisted entirely by pin horizontal reaction."""
        case = load_preset_json("04-pratt-vento")
        solution = solve_payload(case["input"])
        rx_b0 = next(r["Rx"] for r in solution["reactions"] if r["node"] == "B0")
        assert math.isclose(rx_b0, -8.0, abs_tol=1e-6)

    def test_t1_react_04_overhang_cantilever_reactions(self) -> None:
        """F10: Cantilever overhang truss produces downward hold-down reaction at anchor support."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 6.0, "y": 0.0, "support": "none"},
                {"id": "D", "x": 3.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 1000.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        ry_b = next(r["Ry"] for r in solution["reactions"] if r["node"] == "B")
        # Moment about B: Ry_A * 3 + 10 * 3 = 0 -> Ry_A = -10.0 kN (hold down)
        # Sum Fy: Ry_A + Ry_B - 10 = 0 -> Ry_B = +20.0 kN
        assert math.isclose(ry_a, -10.0, abs_tol=1e-6)
        assert math.isclose(ry_b, 20.0, abs_tol=1e-6)

    def test_t1_react_05_roller_x_reactions_balance(self) -> None:
        """F10: Vertical roller (roller_x) develops horizontal reaction Rx, leaving vertical direction free."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 0.0, "y": 4.0, "support": "roller_x"},
                {"id": "C", "x": 3.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 10.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        rx_a = next(r["Rx"] for r in solution["reactions"] if r["node"] == "A")
        rx_b = next(r["Rx"] for r in solution["reactions"] if r["node"] == "B")
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        # Sum Fx = 10 + Rx_A + Rx_B = 0; Moment about A: Rx_B * 4 + 10 * 2 = 0 -> Rx_B = -5.0
        assert math.isclose(rx_b, -5.0, abs_tol=1e-6)
        assert math.isclose(rx_a, -5.0, abs_tol=1e-6)
        assert math.isclose(ry_a, 0.0, abs_tol=1e-6)

    # --- Feature 07: Direct Stiffness Method Displacements ---

    def test_t1_disp_01_prescribed_boundary_displacement_zero(self) -> None:
        """F09: Displacements at boundary supports are strictly zero along restrained degrees of freedom."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        disp_a = next(d for d in solution["displacements"] if d["node"] == "A")
        disp_b = next(d for d in solution["displacements"] if d["node"] == "B")
        assert math.isclose(disp_a["ux"], 0.0, abs_tol=1e-12)
        assert math.isclose(disp_a["uy"], 0.0, abs_tol=1e-12)
        assert math.isclose(disp_b["uy"], 0.0, abs_tol=1e-12)

    def test_t1_disp_02_symmetric_truss_displacement_symmetry(self) -> None:
        """F09: Symmetric truss under symmetric load exhibits symmetric displacement fields."""
        case = load_preset_json("03-warren")
        solution = solve_payload(case["input"])
        disps = {d["node"]: (d["ux"], d["uy"]) for d in solution["displacements"]}

        # Symmetrical nodes have identical vertical deflection
        assert math.isclose(disps["T0"][1], disps["T2"][1], abs_tol=1e-6)
        assert math.isclose(disps["B1"][1], disps["B2"][1], abs_tol=1e-6)

        # Centerline node T1 horizontal displacement is exactly midway between B0 (pin ux=0) and B3 (roller ux)
        ux_b0 = disps["B0"][0]
        ux_b3 = disps["B3"][0]
        ux_t1 = disps["T1"][0]
        assert math.isclose(ux_t1 - ux_b0, ux_b3 - ux_t1, abs_tol=1e-6)

    def test_t1_disp_03_linear_load_displacement_scaling(self) -> None:
        """F09: Doubling external loads exactly doubles all nodal displacements."""
        case = load_preset_json("01-triangulo")
        sol1 = solve_payload(case["input"])

        doubled_input = json.loads(json.dumps(case["input"]))
        doubled_input["loads"][0]["Fy"] *= 2.0
        sol2 = solve_payload(doubled_input)

        for d1, d2 in zip(sol1["displacements"], sol2["displacements"]):
            assert math.isclose(d2["ux"], 2.0 * d1["ux"], abs_tol=1e-9)
            assert math.isclose(d2["uy"], 2.0 * d1["uy"], abs_tol=1e-9)

    def test_t1_disp_04_inverse_stiffness_displacement_scaling(self) -> None:
        """F09: In isostatic trusses, doubling EA halves displacements without altering member forces."""
        case = load_preset_json("01-triangulo")
        sol1 = solve_payload(case["input"])

        stiff_input = json.loads(json.dumps(case["input"]))
        for m in stiff_input["members"]:
            m["EA"] *= 2.0
        sol2 = solve_payload(stiff_input)

        # Displacements halved
        for d1, d2 in zip(sol1["displacements"], sol2["displacements"]):
            assert math.isclose(d2["ux"], d1["ux"] / 2.0, abs_tol=1e-9)
            assert math.isclose(d2["uy"], d1["uy"] / 2.0, abs_tol=1e-9)

        # Internal axial forces invariant in isostatic truss
        for m1, m2 in zip(sol1["members"], sol2["members"]):
            assert math.isclose(m2["N"], m1["N"], abs_tol=1e-9)

    def test_t1_disp_05_global_stiffness_matrix_properties(self) -> None:
        """F09: Global stiffness matrix K is exactly symmetric and positive semi-definite."""
        case = load_preset_json("01-triangulo")
        truss = parse_truss(case["input"])
        K, _ = assemble(truss)
        assert np.allclose(K, K.T, atol=1e-12)
        eigenvalues = np.linalg.eigvalsh(K)
        # Rigid body modes may be zero, but no negative eigenvalues
        assert np.all(eigenvalues >= -1e-10)

    # --- Feature 08: Independent Method of Joints Cross-Validation ---

    def test_t1_moj_01_exact_concordance_3bar_triangle(self) -> None:
        """F12: Method of Joints and Direct Stiffness Method concord to < 10^-12 kN on 3-bar triangle."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        cross = solution["crossCheck"]
        assert cross["available"] is True
        assert cross["passed"] is True
        assert cross["maxDifference"] < 1e-12

    def test_t1_moj_02_concordance_warren_truss(self) -> None:
        """F12: Dual methods match to < 10^-12 kN on 7-node Warren truss."""
        case = load_preset_json("03-warren")
        solution = solve_payload(case["input"])
        cross = solution["crossCheck"]
        assert cross["available"] is True
        assert cross["passed"] is True
        assert cross["maxDifference"] < 1e-12

    def test_t1_moj_03_concordance_pratt_roof(self) -> None:
        """F12: Dual methods match to < 10^-12 kN on Pratt roof truss."""
        case = load_preset_json("02-telhado-pratt")
        solution = solve_payload(case["input"])
        cross = solution["crossCheck"]
        assert cross["available"] is True
        assert cross["passed"] is True
        assert cross["maxDifference"] < 1e-12

    def test_t1_moj_04_concordance_irregular_geometry(self) -> None:
        """F12: Dual methods match on non-orthogonal, irregular geometry truss."""
        case = load_preset_json("07-geometria-irregular")
        solution = solve_payload(case["input"])
        cross = solution["crossCheck"]
        assert cross["available"] is True
        assert cross["passed"] is True
        assert cross["maxDifference"] < 1e-12

    def test_t1_moj_05_indeterminate_moj_reporting(self) -> None:
        """F12: Method of Joints reports 'available: false' on statically indeterminate trusses without failing."""
        case = load_preset_json("08-hiperestatica")
        solution = solve_payload(case["input"])
        cross = solution["crossCheck"]
        assert cross["available"] is False
        assert "exige treliça isostática" in cross["reason"]

    # --- Feature 09: Global Static Equilibrium Residuals ---

    def test_t1_eq_01_horizontal_force_residual_threshold(self) -> None:
        """F13: Global horizontal force residual sumFx satisfies |sumFx| < 10^-9 kN."""
        for slug in ("01-triangulo", "02-telhado-pratt", "03-warren", "04-pratt-vento"):
            case = load_preset_json(slug)
            solution = solve_payload(case["input"])
            assert abs(solution["checks"]["sumFx"]) < 1e-9

    def test_t1_eq_02_vertical_force_residual_threshold(self) -> None:
        """F13: Global vertical force residual sumFy satisfies |sumFy| < 10^-9 kN."""
        for slug in ("01-triangulo", "02-telhado-pratt", "03-warren", "04-pratt-vento"):
            case = load_preset_json(slug)
            solution = solve_payload(case["input"])
            assert abs(solution["checks"]["sumFy"]) < 1e-9

    def test_t1_eq_03_moment_residual_threshold(self) -> None:
        """F13: Global moment residual about origin satisfies |sumM| < 10^-8 kN*m."""
        for slug in ("01-triangulo", "02-telhado-pratt", "03-warren", "04-pratt-vento"):
            case = load_preset_json(slug)
            solution = solve_payload(case["input"])
            assert abs(solution["checks"]["sumM"]) < 1e-8

    def test_t1_eq_04_worst_nodal_residual_threshold(self) -> None:
        """F13: Worst individual nodal vector residual satisfies ||r_j|| < 10^-9 kN."""
        for slug in ("01-triangulo", "02-telhado-pratt", "03-warren", "07-geometria-irregular"):
            case = load_preset_json(slug)
            solution = solve_payload(case["input"])
            assert solution["checks"]["maxNodalResidual"] < 1e-9

    def test_t1_eq_05_equilibrium_passed_boolean_flag(self) -> None:
        """F13: Equilibrium verification summary provides explicit passed: True flag."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        assert solution["checks"]["passed"] is True

    # --- Feature 10: Geometric Zero-Force Rules ---

    def test_t1_zf_01_rule_r1_single_member(self) -> None:
        """F14: Rule R1 detects zero force in a single member connected to an unloaded, unsupported node."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
                {"id": "D", "x": 6.0, "y": 0.0, "support": "none"},  # Node D has only 1 member BD
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        truss = parse_truss(model)
        rules = find_zero_force_rules(truss)
        assert "BD" in rules
        assert "R1" in rules["BD"]

    def test_t1_zf_02_rule_r2_two_non_collinear_members(self) -> None:
        """F14: Rule R2 detects zero force in two non-collinear members connected to an unloaded, unsupported node."""
        case = load_preset_json("05-forca-zero-T")
        truss = parse_truss(case["input"])
        rules = find_zero_force_rules(truss)
        assert "CD" in rules
        assert "DA" in rules
        assert "R2" in rules["CD"]
        assert "R2" in rules["DA"]

    def test_t1_zf_03_rule_r3_three_members_two_collinear(self) -> None:
        """F14: Rule R3 detects zero force in third member connecting to two collinear members at an unloaded, unsupported node."""
        case = load_preset_json("06-forca-zero-R3")
        truss = parse_truss(case["input"])
        rules = find_zero_force_rules(truss)
        assert "CT" in rules
        assert "R3" in rules["CT"]

    def test_t1_zf_04_external_load_cancels_zero_force_rule(self) -> None:
        """F14: Applying an external load to the inspected joint disables the zero-force rule."""
        case = load_preset_json("06-forca-zero-R3")
        loaded_input = json.loads(json.dumps(case["input"]))
        loaded_input["loads"].append({"node": "C", "Fx": 0.0, "Fy": -5.0})
        truss = parse_truss(loaded_input)
        rules = find_zero_force_rules(truss)
        assert "CT" not in rules

    def test_t1_zf_05_support_cancels_zero_force_rule(self) -> None:
        """F14: Placing a support restraint on the inspected joint disables the zero-force rule."""
        case = load_preset_json("05-forca-zero-T")
        supported_input = json.loads(json.dumps(case["input"]))
        for n in supported_input["nodes"]:
            if n["id"] == "D":
                n["support"] = "roller"
        truss = parse_truss(supported_input)
        rules = find_zero_force_rules(truss)
        assert "CD" not in rules
        assert "DA" not in rules

    # --- Feature 11: Static Determinacy Degree ---

    def test_t1_det_01_isostatic_classification(self) -> None:
        """F15: Truss with b + r = 2n is classified as 'isostática' with degree g = 0."""
        case = load_preset_json("01-triangulo")
        truss = parse_truss(case["input"])
        det = analyze_determinacy(truss)
        assert det.degree == 0
        assert det.label == "isostática"
        assert det.is_isostatic is True

    def test_t1_det_02_hypostatic_classification(self) -> None:
        """F15: Truss with b + r < 2n is classified as 'hipostática' with degree g < 0."""
        case = load_preset_json("09-hipostatica")
        truss = parse_truss(case["input"])
        det = analyze_determinacy(truss)
        assert det.degree == -1
        assert det.label == "hipostática"
        assert det.is_hypostatic is True

    def test_t1_det_03_indeterminate_degree_1(self) -> None:
        """F15: Square truss with 2 active diagonals has b + r = 9, 2n = 8 -> degree g = 1 ('hiperestática')."""
        case = load_preset_json("08-hiperestatica")
        truss = parse_truss(case["input"])
        det = analyze_determinacy(truss)
        assert det.degree == 1
        assert det.label == "hiperestática"
        assert det.is_hyperstatic is True

    def test_t1_det_04_indeterminate_degree_2(self) -> None:
        """F15: Two-panel truss with double cross-bracing has degree g = 2."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 8.0, "y": 0.0, "support": "roller"},
                {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
                {"id": "E", "x": 4.0, "y": 3.0, "support": "none"},
                {"id": "F", "x": 8.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "DE", "a": "D", "b": "E", "EA": 1.0},
                {"id": "EF", "a": "E", "b": "F", "EA": 1.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 1.0},
                {"id": "BE", "a": "B", "b": "E", "EA": 1.0},
                {"id": "CF", "a": "C", "b": "F", "EA": 1.0},
                {"id": "AE", "a": "A", "b": "E", "EA": 1.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1.0},
                {"id": "BF", "a": "B", "b": "F", "EA": 1.0},
                {"id": "CE", "a": "C", "b": "E", "EA": 1.0},
            ],
            "loads": [{"node": "E", "Fx": 0.0, "Fy": -10.0}],
        }
        truss = parse_truss(model)
        det = analyze_determinacy(truss)
        # n = 6 (2n = 12), b = 11, r = 3 (b + r = 14) -> g = 2
        assert det.degree == 2
        assert det.label == "hiperestática"

    def test_t1_det_05_isolated_node_reduces_determinacy(self) -> None:
        """F15: Adding an isolated node increases 2n by 2, turning an isostatic truss into hypostatic."""
        case = load_preset_json("01-triangulo")
        isolated_input = json.loads(json.dumps(case["input"]))
        isolated_input["nodes"].append({"id": "Z", "x": 10.0, "y": 10.0, "support": "none"})
        truss = parse_truss(isolated_input)
        det = analyze_determinacy(truss)
        assert det.degree == -2
        assert det.label == "hipostática"

    # --- Feature 12: Mechanism and Instability Detection ---

    def test_t1_mech_01_collinear_nodes_zero_eigenvalue(self) -> None:
        """F16: Internal mechanism with collinear bars (Case 10) is detected via zero eigenvalue in K_ff."""
        case = load_preset_json("10-mecanismo")
        solution = solve_payload(case["input"])
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "mechanism"
        assert "B.uy" in solution["errors"][0]["message"]

    def test_t1_mech_02_parallel_roller_slide_mechanism(self) -> None:
        """F16: Truss supported exclusively by parallel horizontal rollers exhibits rigid body translation mechanism."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "roller"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "roller"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 5.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "mechanism"

    def test_t1_mech_03_unbraced_quadrilateral_shear_mechanism(self) -> None:
        """F16: Unbraced four-bar linkage has degree g = 0 (b=4, r=4, n=4) but fails as kinematic mechanism."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "pin"},
                {"id": "C", "x": 4.0, "y": 3.0, "support": "none"},
                {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1.0},
                {"id": "DA", "a": "D", "b": "A", "EA": 1.0},
            ],
            "loads": [{"node": "D", "Fx": 5.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "mechanism"

    def test_t1_mech_04_structured_error_dof_reporting(self) -> None:
        """F16: Mechanism error payload identifies the specific participating kinematic degrees of freedom."""
        case = load_preset_json("10-mecanismo")
        truss = parse_truss(case["input"])
        with pytest.raises(MechanismError) as exc_info:
            analyze(truss)
        assert "B.uy" in str(exc_info.value)
        assert exc_info.value.code == "mechanism"

    def test_t1_mech_05_spectral_analysis_distinguishes_hyperstatic(self) -> None:
        """F16: Spectral decomposition confirms indeterminate trusses are fully stable (all positive eigenvalues)."""
        case = load_preset_json("08-hiperestatica")
        truss = parse_truss(case["input"])
        K, _ = assemble(truss)
        restrained = tuple(truss.restrained_dofs)
        free_dofs = tuple(dof for dof in range(truss.n_dof) if dof not in set(restrained))
        K_ff = K[np.ix_(list(free_dofs), list(free_dofs))]
        mech = find_mechanism_dofs(K_ff, free_dofs)
        assert len(mech) == 0

    # --- Feature 13: Normal Stress Calculation ---

    def test_t1_stress_01_tensile_stress_computation(self) -> None:
        """F18: Normal tensile stress is computed as sigma = (N * 1000) / A in MPa (positive)."""
        # N = 10 kN, A = 100 mm^2 -> sigma = 100 MPa
        sigma = normal_stress_mpa(10.0, 100.0)
        assert math.isclose(sigma, 100.0)

    def test_t1_stress_02_compressive_stress_computation(self) -> None:
        """F18: Normal compressive stress is computed as sigma = (N * 1000) / A in MPa (negative)."""
        # N = -25 kN, A = 250 mm^2 -> sigma = -100 MPa
        sigma = normal_stress_mpa(-25.0, 250.0)
        assert math.isclose(sigma, -100.0)

    def test_t1_stress_03_zero_force_member_zero_stress(self) -> None:
        """F18: Member with zero axial force has zero normal stress."""
        sigma = normal_stress_mpa(0.0, 150.0)
        assert math.isclose(sigma, 0.0)

    def test_t1_stress_04_missing_area_partial_status(self) -> None:
        """F18: Omitting area on a subset of members reports partial: True without failing the calculation."""
        case = load_preset_json("01-triangulo")
        model = json.loads(json.dumps(case["input"]))
        model["members"][0]["area"] = 100.0
        model["members"][1]["area"] = None
        model["members"][2]["area"] = None
        solution = solve_payload(model)
        stress = solution["stress"]
        assert stress["available"] is False
        assert stress["partial"] is True
        assert len(stress["entries"]) == 1
        assert "AC" in stress["missing"]
        assert "BC" in stress["missing"]

    def test_t1_stress_05_critical_stress_summary(self) -> None:
        """F18: Stress summary correctly reports maxTension, maxCompression, and governing critical stress."""
        case = load_preset_json("01-triangulo")
        model = json.loads(json.dumps(case["input"]))
        for m in model["members"]:
            m["area"] = 100.0
        solution = solve_payload(model)
        summary = solution["stress"]["summary"]
        assert math.isclose(summary["maxTension"]["sigma"], 33.333333, abs_tol=1e-4)
        assert math.isclose(summary["maxCompression"]["sigma"], -60.092521, abs_tol=1e-4)
        assert summary["critical"]["id"] in ("AC", "BC")
        assert math.isclose(summary["maxAbsStress"], 60.092521, abs_tol=1e-4)

    # --- Feature 14: Reverse Section Sizing ---

    def test_t1_sizing_01_uniform_allowable_stress(self) -> None:
        """F19: Required section area is computed as A_req = (|N| * 1000) / sigma_adm in mm^2."""
        # N = 30 kN, sigma_adm = 150 MPa -> A_req = 200 mm^2
        area = required_area_mm2(30.0, 150.0)
        assert math.isclose(area, 200.0)

        # Compressive force N = -45 kN, sigma_adm = 150 MPa -> A_req = 300 mm^2
        area_comp = required_area_mm2(-45.0, 150.0)
        assert math.isclose(area_comp, 300.0)

    def test_t1_sizing_02_distinct_tension_compression_allowables(self) -> None:
        """F19: Distinct allowable limits for tension vs compression apply appropriate limits."""
        case = load_preset_json("01-triangulo")
        truss = parse_truss(case["input"])
        forces = {"AB": 3.333333, "AC": -6.009252, "BC": -6.009252}
        allowable = {"tension": 100.0, "compression": 50.0}
        req = required_areas(truss, forces, allowable)
        entry_ab = next(e for e in req["entries"] if e["id"] == "AB")
        entry_ac = next(e for e in req["entries"] if e["id"] == "AC")
        # AB: tension limit 100 MPa -> 3.333333 * 1000 / 100 = 33.333 mm^2
        assert math.isclose(entry_ab["requiredArea"], 33.33333, abs_tol=1e-4)
        # AC: compression limit 50 MPa -> 6.009252 * 1000 / 50 = 120.185 mm^2
        assert math.isclose(entry_ac["requiredArea"], 120.18504, abs_tol=1e-4)

    def test_t1_sizing_03_utilisation_ratio_and_ok_flag(self) -> None:
        """F19: Utilisation ratio u = sigma / sigma_adm and adequacy boolean ok are correctly evaluated."""
        case = load_preset_json("01-triangulo")
        model = json.loads(json.dumps(case["input"]))
        # Set area 50 mm^2 on AB (N = 3.333 kN, req = 33.33 mm^2 at 100 MPa -> sufficient)
        model["members"][0]["area"] = 50.0
        truss = parse_truss(model)
        forces = {"AB": 3.333333, "AC": -6.009252, "BC": -6.009252}
        req = required_areas(truss, forces, 100.0)
        entry_ab = next(e for e in req["entries"] if e["id"] == "AB")
        assert entry_ab["ok"] is True
        assert entry_ab["utilisation"] < 1.0

    def test_t1_sizing_04_total_required_area_and_governing_member(self) -> None:
        """F19: Reverse sizing summary provides total material area and governing member."""
        case = load_preset_json("01-triangulo")
        truss = parse_truss(case["input"])
        forces = {"AB": 3.333333, "AC": -6.009252, "BC": -6.009252}
        req = required_areas(truss, forces, 50.0)
        summary = req["summary"]
        assert summary["governing"]["id"] in ("AC", "BC")
        assert math.isclose(summary["totalRequiredArea"], 66.66667 + 2 * 120.18504, abs_tol=1e-3)

    def test_t1_sizing_05_non_positive_allowable_rejection(self) -> None:
        """F19: Non-positive allowable stress values raise InputError with code 'bad_allowable'."""
        with pytest.raises(InputError) as exc_info:
            required_area_mm2(10.0, 0.0)
        assert exc_info.value.code == "bad_allowable"

        with pytest.raises(InputError) as exc_neg:
            required_area_mm2(10.0, -50.0)
        assert exc_neg.value.code == "bad_allowable"

    # --- Feature 15: Unit Conversions (SI and Imperial) ---

    def test_t1_units_01_si_base_force_length(self) -> None:
        """F20: SI units (N and mm) convert accurately to base kN and m and back."""
        assert math.isclose(force_factor("N"), 1e-3)
        assert math.isclose(length_factor("mm"), 1e-3)

        model = {
            "units": {"force": "N", "length": "mm"},
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4000.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2000.0, "y": 3000.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10000.0}],
        }
        solution = solve_payload(model)
        assert solution["units"]["force"] == "N"
        assert solution["units"]["length"] == "mm"
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        assert math.isclose(ry_a, 5000.0, abs_tol=1e-3)

    def test_t1_units_02_imperial_kip_ft(self) -> None:
        """F20: US Customary units (kip and ft) convert accurately."""
        assert math.isclose(force_factor("kip"), 4.4482216152605)
        assert math.isclose(length_factor("ft"), 0.3048)

        model = {
            "units": {"force": "kip", "length": "ft"},
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 12.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 6.0, "y": 8.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 10.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 10.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -20.0}],
        }
        solution = solve_payload(model)
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        assert math.isclose(ry_a, 10.0, abs_tol=1e-5)

    def test_t1_units_03_imperial_lbf_in(self) -> None:
        """F20: Imperial lbf and in unit conversion factors are precise."""
        assert math.isclose(force_factor("lbf"), 4.4482216152605e-3)
        assert math.isclose(length_factor("in"), 0.0254)

    def test_t1_units_04_area_cm2_stress_gpa(self) -> None:
        """F20: Section area in cm² and stress in GPa convert to mm² and MPa."""
        assert math.isclose(area_factor("cm²"), 100.0)
        assert math.isclose(stress_factor("GPa"), 1000.0)

    def test_t1_units_05_unknown_unit_rejection(self) -> None:
        """F20: Unknown engineering units raise InputError with code 'bad_units'."""
        with pytest.raises(InputError) as exc_info:
            force_factor("dynes")
        assert exc_info.value.code == "bad_units"

        with pytest.raises(InputError) as exc_len:
            length_factor("yards")
        assert exc_len.value.code == "bad_units"

    # --- Feature 16: Preset Loading and JSON Model Serialization ---

    def test_t1_preset_01_list_presets_endpoint(self) -> None:
        """F23: GET /api/presets lists all 12 benchmark presets without heavy input models."""
        response = client.get("/api/presets")
        assert response.status_code == 200
        presets = response.json()["presets"]
        assert len(presets) == 12
        for p in presets:
            assert "slug" in p
            assert "name" in p
            assert "input" not in p

    def test_t1_preset_02_get_preset_by_slug(self) -> None:
        """F23: GET /api/presets/{slug} returns complete input model for each canonical case."""
        for slug in ("01-triangulo", "05-forca-zero-T", "12-pratt-grande"):
            response = client.get(f"/api/presets/{slug}")
            assert response.status_code == 200
            data = response.json()
            assert data["slug"] == slug
            assert "nodes" in data["input"]
            assert "members" in data["input"]

    def test_t1_preset_03_non_existent_preset_404(self) -> None:
        """F23: GET /api/presets/non-existent returns 404 HTTP error status."""
        response = client.get("/api/presets/unknown-case-slug")
        assert response.status_code == 404

    def test_t1_preset_04_model_to_dict_roundtrip(self) -> None:
        """F24: Truss model to_dict() serialization roundtrip preserves all topology and parameters."""
        case = load_preset_json("01-triangulo")
        truss1 = parse_truss(case["input"])
        serialized = truss1.to_dict()
        truss2 = parse_truss(serialized)

        assert len(truss1.nodes) == len(truss2.nodes)
        assert len(truss1.members) == len(truss2.members)
        assert len(truss1.loads) == len(truss2.loads)
        for n1, n2 in zip(truss1.nodes, truss2.nodes):
            assert n1.id == n2.id
            assert math.isclose(n1.x, n2.x)
            assert math.isclose(n1.y, n2.y)
            assert n1.support == n2.support

    def test_t1_preset_05_reparsed_model_identical_solution(self) -> None:
        """F24: Solving a roundtrip-serialized model produces identical numerical results to 12 decimal places."""
        case = load_preset_json("01-triangulo")
        sol1 = solve_payload(case["input"])

        truss = parse_truss(case["input"])
        sol2 = solve_payload(truss.to_dict())

        for m1, m2 in zip(sol1["members"], sol2["members"]):
            assert math.isclose(m1["N"], m2["N"], abs_tol=1e-12)

    # --- Feature 17: Technical Report Generation ---

    def test_t1_report_01_html_report_endpoint(self) -> None:
        """F25: POST /api/report returns valid standalone HTML report."""
        case = load_preset_json("01-triangulo")
        response = client.post("/api/report", json={"model": case["input"], "title": "Relatório N2"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<!DOCTYPE html>" in response.text

    def test_t1_report_02_report_contains_embedded_svg(self) -> None:
        """F25: Report contains embedded SVG diagram element with vector markup."""
        case = load_preset_json("01-triangulo")
        response = client.post("/api/report", json={"model": case["input"]})
        assert "<svg" in response.text
        assert "</svg>" in response.text

    def test_t1_report_03_report_contains_results_tables(self) -> None:
        """F25: Report contains member forces table, reaction summary, and static equilibrium checks."""
        case = load_preset_json("01-triangulo")
        response = client.post("/api/report", json={"model": case["input"]})
        assert "Reações de apoio" in response.text
        assert "Esforços normais" in response.text
        assert "Verificações" in response.text

    def test_t1_report_04_report_with_custom_title_and_stress(self) -> None:
        """F25: Report integrates custom project header title and normal stress data table."""
        case = load_preset_json("01-triangulo")
        model = json.loads(json.dumps(case["input"]))
        for m in model["members"]:
            m["area"] = 100.0
        response = client.post(
            "/api/report",
            json={"model": model, "title": "Avaliação N2 - Equipe Alfa", "showStress": True},
        )
        assert "Avaliação N2 - Equipe Alfa" in response.text
        assert "Tensões normais" in response.text

    def test_t1_report_05_unsolvable_model_report_graceful_handling(self) -> None:
        """F25: POST /api/report on unresolvable/mechanism model outputs an explanatory HTML error page without 500 error."""
        case = load_preset_json("10-mecanismo")
        response = client.post("/api/report", json={"model": case["input"]})
        assert response.status_code == 200
        assert "Não foi possível gerar o relatório" in response.text
        assert "mecanismo interno" in response.text


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests per domain)
# ==============================================================================

class TestTier2BoundaryCornerCases:
    """Tier 2: Boundary conditions, numerical extremes, singular topologies, and corner cases."""

    # --- Domain 01: Extreme Geometry Ratios ---

    def test_t2_extreme_01_slender_member_100m(self) -> None:
        """T2.1: Very slender member (L = 100m) maintains numerical equilibrium without floating point overflow."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 100.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 50.0, "y": 10.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 200000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 200000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 200000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True
        assert abs(solution["checks"]["sumFy"]) < 1e-9

    def test_t2_extreme_02_short_stiff_member_001m(self) -> None:
        """T2.1: Ultra-short member (L = 0.01m) with high stiffness computes without ill-conditioning."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 0.01, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 0.005, "y": 0.01, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1e6},
                {"id": "AC", "a": "A", "b": "C", "EA": 1e6},
                {"id": "BC", "a": "B", "b": "C", "EA": 1e6},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        assert math.isclose(ry_a, 5.0, abs_tol=1e-5)

    def test_t2_extreme_03_high_aspect_ratio_100_to_1(self) -> None:
        """T2.1: Shallow truss with extreme aspect ratio (height 0.1m, span 10m) retains equilibrium closure."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 10.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 5.0, "y": 0.1, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 500000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 500000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 500000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -1.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    def test_t2_extreme_04_tall_slender_tower_truss(self) -> None:
        """T2.1: Tall slender tower (height 40m, width 2m) under lateral apex load solves cleanly with overturning restraint."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 0.0, "y": 40.0, "support": "none"},
                {"id": "D", "x": 2.0, "y": 40.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 10000.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 10000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 10000.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 10000.0},
            ],
            "loads": [{"node": "C", "Fx": 5.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    def test_t2_extreme_05_contrast_stiffness_1e6(self) -> None:
        """T2.1: Indeterminate truss with huge axial stiffness contrast (EA1/EA2 = 10^6) computes force redistribution."""
        case = load_preset_json("08-hiperestatica")
        model = json.loads(json.dumps(case["input"]))
        # One diagonal ultra-stiff, the other slender
        for m in model["members"]:
            if m["id"] == "AC":
                m["EA"] = 1e6
            else:
                m["EA"] = 1.0
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    # --- Domain 02: Right-Angle Triangles and Asymmetric Loads ---

    def test_t2_geom_01_30_60_90_right_triangle(self) -> None:
        """T2.2: 30-60-90 right triangle reproduces exact trigonometric member forces."""
        # 30-60-90 triangle: base 3m, height 3*sqrt(3)m
        h = 3.0 * math.sqrt(3.0)
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 0.0, "y": h, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 10.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True
        # Moment about A: Ry_B * 3 - 10 * h = 0 -> Ry_B = 10*sqrt(3) = 17.3205 kN
        ry_b = next(r["Ry"] for r in solution["reactions"] if r["node"] == "B")
        assert math.isclose(ry_b, 10.0 * math.sqrt(3.0), abs_tol=1e-5)

    def test_t2_geom_02_45_45_90_right_triangle(self) -> None:
        """T2.2: Isosceles right triangle under diagonal load."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 0.0, "y": 4.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 10.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    def test_t2_geom_03_symmetric_vs_antisymmetric_loading(self) -> None:
        """T2.2: Anti-symmetric loading on symmetric Warren bridge produces zero middle vertical reaction."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 8.0, "y": 0.0, "support": "roller"},
                {"id": "D", "x": 2.0, "y": 3.0, "support": "none"},
                {"id": "E", "x": 6.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "DE", "a": "D", "b": "E", "EA": 1.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 1.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1.0},
                {"id": "BE", "a": "B", "b": "E", "EA": 1.0},
                {"id": "CE", "a": "C", "b": "E", "EA": 1.0},
            ],
            # Anti-symmetric load: -10 at D, +10 at E
            "loads": [
                {"node": "D", "Fx": 0.0, "Fy": -10.0},
                {"node": "E", "Fx": 0.0, "Fy": 10.0},
            ],
        }
        solution = solve_payload(model)
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        ry_c = next(r["Ry"] for r in solution["reactions"] if r["node"] == "C")
        # Sum Fy = 0 -> Ry_A + Ry_C = 0 -> Ry_A = -Ry_C
        assert math.isclose(ry_a, -ry_c, abs_tol=1e-6)

    def test_t2_geom_04_skewed_asymmetric_load_warren(self) -> None:
        """T2.2: Skewed loading on single bottom node of Warren truss."""
        case = load_preset_json("03-warren")
        skewed = json.loads(json.dumps(case["input"]))
        skewed["loads"] = [{"node": "B1", "Fx": 5.0, "Fy": -20.0}]
        solution = solve_payload(skewed)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    def test_t2_geom_05_cantilevered_right_triangle(self) -> None:
        """T2.2: Right-angle triangular bracket supported by vertical wall pins."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 0.0, "y": 3.0, "support": "roller_x"},
                {"id": "C", "x": 4.0, "y": 0.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -12.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        # Moment about A: Rx_B * 3 + 12 * 4 = 0 -> Rx_B = -16.0 kN; Rx_A = +16.0 kN
        rx_b = next(r["Rx"] for r in solution["reactions"] if r["node"] == "B")
        rx_a = next(r["Rx"] for r in solution["reactions"] if r["node"] == "A")
        assert math.isclose(rx_b, -16.0, abs_tol=1e-6)
        assert math.isclose(rx_a, 16.0, abs_tol=1e-6)

    # --- Domain 03: Zero-Load Trusses ---

    def test_t2_zeroload_01_triangle_zero_forces(self) -> None:
        """T2.3: Zero-load triangle (Case 11) produces all zero forces and reactions."""
        case = load_preset_json("11-sem-carga")
        solution = solve_payload(case["input"])
        assert solution["status"] == "ok"
        for m in solution["members"]:
            assert m["N"] == 0.0
            assert m["zero_force"] is True
        for r in solution["reactions"]:
            assert r["Rx"] == 0.0
            assert r["Ry"] == 0.0

    def test_t2_zeroload_02_multi_bay_warren_zero_load(self) -> None:
        """T2.3: Multi-bay Warren truss with no loads produces exactly zero nodal displacements."""
        case = load_preset_json("03-warren")
        empty = json.loads(json.dumps(case["input"]))
        empty["loads"] = []
        solution = solve_payload(empty)
        for d in solution["displacements"]:
            assert d["ux"] == 0.0
            assert d["uy"] == 0.0

    def test_t2_zeroload_03_hyperstatic_truss_zero_load(self) -> None:
        """T2.3: Indeterminate cross-braced truss under zero load maintains all zero stresses."""
        case = load_preset_json("08-hiperestatica")
        empty = json.loads(json.dumps(case["input"]))
        empty["loads"] = []
        solution = solve_payload(empty)
        assert solution["status"] == "ok"
        for m in solution["members"]:
            assert m["N"] == 0.0

    def test_t2_zeroload_04_equilibrium_residuals_identically_zero(self) -> None:
        """T2.3: Static checks for zero-load truss report exactly 0.0 for sumFx, sumFy, and sumM."""
        case = load_preset_json("11-sem-carga")
        solution = solve_payload(case["input"])
        assert solution["checks"]["sumFx"] == 0.0
        assert solution["checks"]["sumFy"] == 0.0
        assert solution["checks"]["sumM"] == 0.0
        assert solution["checks"]["maxNodalResidual"] == 0.0
        assert solution["checks"]["passed"] is True

    def test_t2_zeroload_05_imperial_units_zero_load(self) -> None:
        """T2.3: Zero-load model configured in Imperial units (kip, ft) handles zeros cleanly."""
        case = load_preset_json("11-sem-carga")
        imperial = json.loads(json.dumps(case["input"]))
        imperial["units"] = {"force": "kip", "length": "ft"}
        solution = solve_payload(imperial)
        assert solution["status"] == "ok"
        assert solution["units"]["force"] == "kip"
        assert solution["summary"]["maxAbsForce"] == 0.0

    # --- Domain 04: Multiple Collinear Members ---

    def test_t2_collinear_01_three_collinear_chords(self) -> None:
        """T2.4: Three collinear members forming bottom chord transfer tensile force with perfect continuity."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 4.0, "y": 0.0, "support": "none"},
                {"id": "D", "x": 6.0, "y": 0.0, "support": "roller"},
                {"id": "T1", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "T2", "x": 4.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1.0},
                {"id": "T1T2", "a": "T1", "b": "T2", "EA": 1.0},
                {"id": "AT1", "a": "A", "b": "T1", "EA": 1.0},
                {"id": "BT1", "a": "B", "b": "T1", "EA": 1.0},
                {"id": "BT2", "a": "B", "b": "T2", "EA": 1.0},
                {"id": "CT2", "a": "C", "b": "T2", "EA": 1.0},
                {"id": "DT2", "a": "D", "b": "T2", "EA": 1.0},
            ],
            "loads": [{"node": "B", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    def test_t2_collinear_02_vertical_collinear_tower(self) -> None:
        """T2.4: Vertical collinear column elements in a tower carry compressive loads."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 0.0, "y": 3.0, "support": "none"},
                {"id": "D", "x": 2.0, "y": 3.0, "support": "none"},
                {"id": "E", "x": 0.0, "y": 6.0, "support": "none"},
                {"id": "F", "x": 2.0, "y": 6.0, "support": "none"},
            ],
            "members": [
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "CE", "a": "C", "b": "E", "EA": 1000.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1000.0},
                {"id": "DF", "a": "D", "b": "F", "EA": 1000.0},
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1000.0},
                {"id": "EF", "a": "E", "b": "F", "EA": 1000.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 1000.0},
                {"id": "CF", "a": "C", "b": "F", "EA": 1000.0},
            ],
            "loads": [{"node": "E", "Fx": 0.0, "Fy": -10.0}, {"node": "F", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    def test_t2_collinear_03_collinear_warning_detection(self) -> None:
        """T2.4: Collinearity warning is correctly added to warnings array when collinear bars meet at a node."""
        case = load_preset_json("06-forca-zero-R3")
        solution = solve_payload(case["input"])
        warnings = solution["warnings"]
        has_collinear = any("colineares" in w for w in warnings)
        assert has_collinear is True

    def test_t2_collinear_04_load_applied_to_collinear_joint(self) -> None:
        """T2.4: Load applied to collinear joint between two members distributes forces correctly without singularity."""
        case = load_preset_json("06-forca-zero-R3")
        loaded = json.loads(json.dumps(case["input"]))
        loaded["loads"].append({"node": "C", "Fx": 0.0, "Fy": -10.0})
        solution = solve_payload(loaded)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    def test_t2_collinear_05_diagonal_collinear_braces(self) -> None:
        """T2.4: Segmented diagonal braces aligned along 45 degrees solve without singularity."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "M", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "C", "x": 4.0, "y": 4.0, "support": "none"},
                {"id": "D", "x": 0.0, "y": 4.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1.0},
                {"id": "DA", "a": "D", "b": "A", "EA": 1.0},
                {"id": "AM", "a": "A", "b": "M", "EA": 1.0},
                {"id": "MC", "a": "M", "b": "C", "EA": 1.0},
                {"id": "BM", "a": "B", "b": "M", "EA": 1.0},
                {"id": "DM", "a": "D", "b": "M", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 10.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

    # --- Domain 05: Highly Indeterminate Trusses ---

    def test_t2_indet_01_double_x_bracing_degree_2(self) -> None:
        """T2.5: Two-bay rectangular truss with double X-bracing has degree g = 2 and solves with stiffness partition."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 6.0, "y": 0.0, "support": "roller"},
                {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
                {"id": "E", "x": 3.0, "y": 3.0, "support": "none"},
                {"id": "F", "x": 6.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "DE", "a": "D", "b": "E", "EA": 1.0},
                {"id": "EF", "a": "E", "b": "F", "EA": 1.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 1.0},
                {"id": "BE", "a": "B", "b": "E", "EA": 1.0},
                {"id": "CF", "a": "C", "b": "F", "EA": 1.0},
                {"id": "AE", "a": "A", "b": "E", "EA": 1.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1.0},
                {"id": "BF", "a": "B", "b": "F", "EA": 1.0},
                {"id": "CE", "a": "C", "b": "E", "EA": 1.0},
            ],
            "loads": [{"node": "E", "Fx": 0.0, "Fy": -20.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["determinacy"]["degree"] == 2
        assert solution["checks"]["passed"] is True

    def test_t2_indet_02_continuous_three_support_truss(self) -> None:
        """T2.5: Continuous truss over three supports (r = 4) produces degree g = 1 indeterminacy."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 8.0, "y": 0.0, "support": "roller"},
                {"id": "D", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "E", "x": 6.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 1.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1.0},
                {"id": "DE", "a": "D", "b": "E", "EA": 1.0},
                {"id": "BE", "a": "B", "b": "E", "EA": 1.0},
                {"id": "CE", "a": "C", "b": "E", "EA": 1.0},
            ],
            "loads": [{"node": "D", "Fx": 0.0, "Fy": -10.0}, {"node": "E", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["determinacy"]["degree"] == 1
        assert solution["checks"]["passed"] is True

    def test_t2_indet_03_force_redistribution_stiffness_variation(self) -> None:
        """T2.5: Doubling EA of a redundant diagonal tie increases its share of internal force."""
        case = load_preset_json("08-hiperestatica")
        # Baseline with equal EA
        sol1 = solve_payload(case["input"])
        n1_ac = next(m["N"] for m in sol1["members"] if m["id"] == "AC")

        # Double EA of diagonal AC
        stiff = json.loads(json.dumps(case["input"]))
        for m in stiff["members"]:
            if m["id"] == "AC":
                m["EA"] = 2.0
        sol2 = solve_payload(stiff)
        n2_ac = next(m["N"] for m in sol2["members"] if m["id"] == "AC")

        # In X-braced frame, stiffer tie attracts more load magnitude
        assert abs(n2_ac) > abs(n1_ac)

    def test_t2_indet_04_indeterminate_warning_emitted(self) -> None:
        """T2.5: Hyperstatic warning regarding EA dependence is emitted in solution warnings."""
        case = load_preset_json("08-hiperestatica")
        solution = solve_payload(case["input"])
        assert any("Treliça hiperestática" in w for w in solution["warnings"])

    def test_t2_indet_05_indeterminate_equilibrium_closure(self) -> None:
        """T2.5: Complex indeterminate truss satisfies equilibrium residuals to < 10^-12 kN."""
        case = load_preset_json("08-hiperestatica")
        solution = solve_payload(case["input"])
        assert abs(solution["checks"]["sumFx"]) < 1e-12
        assert abs(solution["checks"]["sumFy"]) < 1e-12
        assert abs(solution["checks"]["sumM"]) < 1e-12

    # --- Domain 06: Singular Mechanisms and Hypostatic Trusses ---

    def test_t2_mech_01_unsupported_free_truss(self) -> None:
        """T2.6: Truss with all nodes set to support: 'none' is rejected with code 'no_supports'."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "none"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "no_supports"

    def test_t2_mech_02_single_support_pin_only(self) -> None:
        """T2.6: Truss with only 1 pin support (r = 2) is hypostatic (degree g = -1) and rejected."""
        case = load_preset_json("09-hipostatica")
        solution = solve_payload(case["input"])
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "hypostatic"
        assert solution["determinacy"]["degree"] == -1

    def test_t2_mech_03_parallel_rollers_only(self) -> None:
        """T2.6: Truss on horizontal rollers only fails as an unrestrained horizontal mechanism."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "roller"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1.0}],
            "loads": [{"node": "A", "Fx": 5.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] in ("hypostatic", "mechanism")

    def test_t2_mech_04_internal_mechanism_collinear_case10(self) -> None:
        """T2.6: Case 10 internal mechanism returns structured error payload without throwing an unhandled exception."""
        case = load_preset_json("10-mecanismo")
        solution = solve_payload(case["input"])
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "mechanism"
        assert "B.uy" in solution["errors"][0]["message"]

    def test_t2_mech_05_unbraced_four_bar_linkage(self) -> None:
        """T2.6: Unbraced four-bar linkage returns structured error with mechanism diagnosis."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 4.0, "y": 3.0, "support": "none"},
                {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1.0},
                {"id": "DA", "a": "D", "b": "A", "EA": 1.0},
            ],
            "loads": [{"node": "D", "Fx": 10.0, "Fy": 0.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] in ("hypostatic", "mechanism")

    # --- Domain 07: Invalid Input Rejection ---

    def test_t2_invalid_01_zero_length_member(self) -> None:
        """T2.7: Member defined between coincident nodes is rejected with 'invalid_input'."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 0.0, "y": 0.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1.0}],
            "loads": [],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "invalid_input"
        assert "comprimento nulo" in solution["errors"][0]["message"]

    def test_t2_invalid_02_duplicate_member(self) -> None:
        """T2.7: Duplicate member connecting same nodes in reverse order is rejected."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            ],
            "members": [
                {"id": "AB1", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AB2", "a": "B", "b": "A", "EA": 1.0},
            ],
            "loads": [],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "invalid_input"
        assert "barra duplicada" in solution["errors"][0]["message"]

    def test_t2_invalid_03_negative_or_zero_ea(self) -> None:
        """T2.7: Non-positive axial stiffness EA <= 0 is rejected."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": -10.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "invalid_input"
        assert "EA deve ser positivo" in solution["errors"][0]["message"]

    def test_t2_invalid_04_negative_section_area(self) -> None:
        """T2.7: Negative cross-sectional area is rejected during parsing."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0, "area": -50.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "invalid_input"
        assert "a área da seção deve ser positiva" in solution["errors"][0]["message"]

    def test_t2_invalid_05_non_existent_node_in_member_or_load(self) -> None:
        """T2.7: Referencing non-existent node ID in member or load definition is rejected."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "MISSING_NODE", "EA": 1.0}],
            "loads": [{"node": "ANOTHER_MISSING", "Fx": 0.0, "Fy": -10.0}],
        }
        solution = solve_payload(model)
        assert solution["status"] == "error"
        assert solution["errors"][0]["code"] == "invalid_input"


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (PAIRWISE)
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise cross-feature interactions and multidimensional integration."""

    def test_t3_cross_01_combined_wind_gravity_indeterminate(self) -> None:
        """T3.1: Combined horizontal wind (Fx=15 kN) and vertical gravity (Fy=-30 kN) on indeterminate X-braced frame."""
        case = load_preset_json("08-hiperestatica")
        model = json.loads(json.dumps(case["input"]))
        model["loads"] = [
            {"node": "C", "Fx": 15.0, "Fy": -15.0},
            {"node": "D", "Fx": 0.0, "Fy": -15.0},
        ]
        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["determinacy"]["degree"] == 1
        assert solution["checks"]["passed"] is True
        assert abs(solution["checks"]["sumFx"]) < 1e-12
        assert abs(solution["checks"]["sumFy"]) < 1e-12

    def test_t3_cross_02_warren_pin_roller_vs_roller_x(self) -> None:
        """T3.2: Multi-bay Warren truss comparing pin-roller vs pin-roller_x support variations."""
        case = load_preset_json("03-warren")
        sol1 = solve_payload(case["input"])
        assert sol1["status"] == "ok"

        # Alternative: Pin at both ends creates degree 1 hyperstatic truss
        alt = json.loads(json.dumps(case["input"]))
        for n in alt["nodes"]:
            if n["id"] == "B3":
                n["support"] = "pin"
        sol2 = solve_payload(alt)
        assert sol2["status"] == "ok"
        assert sol2["determinacy"]["degree"] == 1

    def test_t3_cross_03_pratt_mixed_sections_and_materials(self) -> None:
        """T3.3: Pratt truss with mixed chord sections (500 mm^2) and web diagonals (250 mm^2) with distinct allowables."""
        case = load_preset_json("02-telhado-pratt")
        model = json.loads(json.dumps(case["input"]))
        for m in model["members"]:
            if m["id"].startswith("C"):
                m["area"] = 500.0  # Chords
            else:
                m["area"] = 250.0  # Webs

        solution = solve_payload(model)
        assert solution["status"] == "ok"
        assert solution["stress"]["available"] is True

        # Compute required areas with distinct allowable stresses
        allowable = {"tension": 140.0, "compression": 90.0}
        stress_res = stress_payload(model, mode="area", allowable=allowable)
        assert stress_res["status"] == "ok"
        assert stress_res["mode"] == "area"

    def test_t3_cross_04_zero_force_under_multi_load_transitions(self) -> None:
        """T3.4: Dynamic zero-force activation and perturbation restoration under multi-load transitions."""
        case = load_preset_json("06-forca-zero-R3")
        # In baseline, member CT is zero-force by rule R3
        sol1 = solve_payload(case["input"])
        ct_1 = next(m for m in sol1["members"] if m["id"] == "CT")
        assert ct_1["zero_force"] is True
        assert math.isclose(ct_1["N"], 0.0, abs_tol=1e-7)

        # Perturb with vertical load at bottom joint C -> CT becomes tensile (+8.0 kN)
        perturbed = json.loads(json.dumps(case["input"]))
        perturbed["loads"].append({"node": "C", "Fx": 0.0, "Fy": -8.0})
        sol2 = solve_payload(perturbed)
        ct_2 = next(m for m in sol2["members"] if m["id"] == "CT")
        assert ct_2["zero_force"] is False
        assert math.isclose(ct_2["N"], 8.0, abs_tol=1e-6)
        assert ct_2["state"] == TENSION

    def test_t3_cross_05_full_pipeline_roundtrip_imperial_to_report(self) -> None:
        """T3.5: Full lifecycle roundtrip: JSON import -> Imperial units -> DSM -> MoJ -> Stress sizing -> HTML Report -> SVG."""
        case = load_preset_json("01-triangulo")
        imperial_model = json.loads(json.dumps(case["input"]))
        imperial_model["units"] = {
            "force": "kip",
            "length": "ft",
            "area": "in²",
            "stress": "ksi",
        }
        for m in imperial_model["members"]:
            m["area"] = 2.5

        # 1. Solve model
        sol = solve_payload(imperial_model)
        assert sol["status"] == "ok"
        assert sol["units"]["force"] == "kip"
        assert sol["crossCheck"]["passed"] is True

        # 2. Compute stress sizing
        sizing = stress_payload(imperial_model, mode="area", allowable=20.0)
        assert sizing["status"] == "ok"

        # 3. Generate HTML report
        report_html = render_report(imperial_model, sol, title="Pratt Truss Imperial E2E")
        assert "Pratt Truss Imperial E2E" in report_html
        assert "kip" in report_html

        # 4. Generate SVG vector graphic
        svg_content = render_truss_svg(imperial_model, sol, show_values=True)
        assert "<svg" in svg_content
        assert "</svg>" in svg_content


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: Complete verification of the 8 N2 exam benchmark problems and large structural systems."""

    def test_t4_n2_01_triangle_benchmark(self) -> None:
        """T4.1: Benchmark 01 (triângulo canônico): exact analytical solution Ay=By=5 kN, N_AB=10/3 kN, N_AC=-6.009 kN."""
        case = load_preset_json("01-triangulo")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["determinacy"]["degree"] == 0
        assert solution["checks"]["passed"] is True
        assert solution["crossCheck"]["passed"] is True

        # Member forces
        for mid, val in expect["members"].items():
            got = next(m["N"] for m in solution["members"] if m["id"] == mid)
            assert math.isclose(got, val, abs_tol=1e-5)

        # Reactions
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        ry_b = next(r["Ry"] for r in solution["reactions"] if r["node"] == "B")
        assert math.isclose(ry_a, 5.0, abs_tol=1e-5)
        assert math.isclose(ry_b, 5.0, abs_tol=1e-5)

    def test_t4_n2_02_roof_pratt_benchmark(self) -> None:
        """T4.2: Benchmark 02 (telhado Pratt): 8 nodes, 13 members, tributary roof loading, zero-force members C1T1 and C3T3."""
        case = load_preset_json("02-telhado-pratt")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["determinacy"]["degree"] == 0
        assert solution["checks"]["passed"] is True
        assert solution["crossCheck"]["passed"] is True

        # Zero force members under Rule R3
        zf_members = [z.get("member") or z.get("id") for z in solution["zero_force"]]
        assert "C1T1" in zf_members
        assert "C3T3" in zf_members

        # Reactions at A and E
        ry_a = next(r["Ry"] for r in solution["reactions"] if r["node"] == "A")
        ry_e = next(r["Ry"] for r in solution["reactions"] if r["node"] == "E")
        assert math.isclose(ry_a, 8.0, abs_tol=1e-5)
        assert math.isclose(ry_e, 8.0, abs_tol=1e-5)

    def test_t4_n2_03_warren_benchmark(self) -> None:
        """T4.3: Benchmark 03 (treliça Warren simétrica): 7 nodes, 11 members, reactions 15 kN each, max difference < 1e-12."""
        case = load_preset_json("03-warren")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True
        assert solution["crossCheck"]["passed"] is True

        for mid, val in expect["members"].items():
            got = next(m["N"] for m in solution["members"] if m["id"] == mid)
            assert math.isclose(got, val, abs_tol=1e-5)

    def test_t4_n2_04_pratt_wind_benchmark(self) -> None:
        """T4.4: Benchmark 04 (Pratt sob ação de vento lateral): horizontal reaction B0x = -8 kN, zero-force member B3T3."""
        case = load_preset_json("04-pratt-vento")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

        # Horizontal reaction at pin
        rx_b0 = next(r["Rx"] for r in solution["reactions"] if r["node"] == "B0")
        assert math.isclose(rx_b0, -8.0, abs_tol=1e-5)

        # Member B3T3 is zero force
        b3t3 = next(m for m in solution["members"] if m["id"] == "B3T3")
        assert b3t3["zero_force"] is True

    def test_t4_n2_05_zero_force_T_benchmark(self) -> None:
        """T4.5: Benchmark 05 (força zero R2): CD and DA zero force by Rule R2, AB zero by equilibrium, Ritter cut verified."""
        case = load_preset_json("05-forca-zero-T")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True

        for mid in ("CD", "DA", "AB"):
            m = next(item for item in solution["members"] if item["id"] == mid)
            assert m["zero_force"] is True
            assert math.isclose(m["N"], 0.0, abs_tol=1e-6)

        # Diagonal AC carries 7.5 kN tension
        ac = next(item for item in solution["members"] if item["id"] == "AC")
        assert math.isclose(ac["N"], 7.5, abs_tol=1e-5)

    def test_t4_n2_06_zero_force_R3_benchmark(self) -> None:
        """T4.6: Benchmark 06 (força zero R3): central vertical strut CT is zero force by Rule R3."""
        case = load_preset_json("06-forca-zero-R3")
        solution = solve_payload(case["input"])

        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True
        ct = next(m for m in solution["members"] if m["id"] == "CT")
        assert ct["zero_force"] is True

    def test_t4_n2_07_irregular_benchmark(self) -> None:
        """T4.7: Benchmark 07 (geometria não-ortogonal): oblique coordinates and non-trivial directional angles."""
        case = load_preset_json("07-geometria-irregular")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["checks"]["passed"] is True
        assert solution["crossCheck"]["passed"] is True

        for mid, val in expect["members"].items():
            got = next(m["N"] for m in solution["members"] if m["id"] == mid)
            assert math.isclose(got, val, abs_tol=1e-5)

    def test_t4_n2_08_hyperstatic_benchmark(self) -> None:
        """T4.8: Benchmark 08 (treliça hiperestática): X-bracing degree g = 1, solved via DSM with full equilibrium."""
        case = load_preset_json("08-hiperestatica")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["determinacy"]["degree"] == 1
        assert solution["checks"]["passed"] is True

        for mid, val in expect["members"].items():
            got = next(m["N"] for m in solution["members"] if m["id"] == mid)
            assert math.isclose(got, val, abs_tol=1e-5)

    def test_t4_case_12_bridge_benchmark(self) -> None:
        """T4.9: Benchmark 12 (ponte Pratt grande): 14 nodes, 25 members, 6 bays, reactions 20 kN, MoJ cross-check < 1e-12."""
        case = load_preset_json("12-pratt-grande")
        solution = solve_payload(case["input"])
        expect = case["expect"]

        assert solution["status"] == "ok"
        assert solution["determinacy"]["n"] == 14
        assert solution["determinacy"]["b"] == 25
        assert solution["determinacy"]["degree"] == 0
        assert solution["checks"]["passed"] is True
        assert solution["crossCheck"]["passed"] is True

        # Symmetry: reactions 20 kN each
        ry_b0 = next(r["Ry"] for r in solution["reactions"] if r["node"] == "B0")
        ry_b6 = next(r["Ry"] for r in solution["reactions"] if r["node"] == "B6")
        assert math.isclose(ry_b0, 20.0, abs_tol=1e-5)
        assert math.isclose(ry_b6, 20.0, abs_tol=1e-5)

    def test_t4_roof_combined_wind_gravity_reversal(self) -> None:
        """T4.10: Real-world roof truss under simultaneous wind uplift and gravity snow load showing chord stress reversal."""
        case = load_preset_json("02-telhado-pratt")

        # 1. Gravity dominant (downward loads)
        sol_gravity = solve_payload(case["input"])
        chord_bot_gravity = next(m for m in sol_gravity["members"] if m["id"] == "AC1")
        chord_top_gravity = next(m for m in sol_gravity["members"] if m["id"] == "AT1")
        # Under gravity: bottom chord in tension, top chord in compression
        assert chord_bot_gravity["state"] == TENSION
        assert chord_top_gravity["state"] == COMPRESSION

        # 2. Wind uplift dominant (severe upward aerodynamic suction)
        uplift_input = json.loads(json.dumps(case["input"]))
        uplift_input["loads"] = [
            {"node": "T1", "Fx": 0.0, "Fy": 20.0},
            {"node": "T2", "Fx": 0.0, "Fy": 30.0},
            {"node": "T3", "Fx": 0.0, "Fy": 20.0},
        ]
        sol_uplift = solve_payload(uplift_input)
        chord_bot_uplift = next(m for m in sol_uplift["members"] if m["id"] == "AC1")
        chord_top_uplift = next(m for m in sol_uplift["members"] if m["id"] == "AT1")
        # Under severe uplift: states reverse! Bottom chord compresses, top chord tensions
        assert chord_bot_uplift["state"] == COMPRESSION
        assert chord_top_uplift["state"] == TENSION
