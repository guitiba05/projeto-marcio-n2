"""Adversarial stress-test suite for MdSolids Trusses structural mechanics kernel and API.

Probing pathological, singular, ill-conditioned, and boundary conditions:
- Slender vs ultra-stiff elements (high aspect ratio & stiffness contrast)
- Extreme loading magnitudes (mega-loads 10^7+ kN to nano-loads 10^-7 kN)
- Adverse angles (17.3°, 89.9°, 0.01°)
- Kinematic linkages, mechanisms, and unbraced modes
- Collinear nodes and multi-bay redundant ties
- Unsupported / floating / isolated nodes
- API fuzzing, malformed payloads, NaN/Inf injection
- Unit conversions across stress and force boundaries
"""

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.server import app
from app.core.errors import DeterminacyError, InputError, MechanismError, TrussError
from app.core.joints import method_of_joints, cross_check
from app.core.model import parse_truss
from app.core.solver import solve_payload, stress_payload
from app.core.stiffness import analyze, assemble

client = TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# CATEGORY 1: HIGH ASPECT-RATIO MEMBERS & STIFFNESS CONTRAST
# ==============================================================================

class TestHighAspectRatioAndStiffnessContrast:
    """Stress tests for extreme geometry ratios and extreme stiffness contrasts."""

    def test_extreme_aspect_ratio_1000_to_1(self):
        """Truss with 1000m span and 1m height (aspect ratio 1000:1)."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 1000.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 500.0, "y": 1.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 210000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 210000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 210000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        checks = res["checks"]
        assert checks["passed"] is True
        assert abs(checks["sumFx"]) < 1e-6
        assert abs(checks["sumFy"]) < 1e-6
        reactions = {r["node"]: r for r in res["reactions"]}
        assert math.isclose(reactions["A"]["Ry"], 5.0, rel_tol=1e-5)
        assert math.isclose(reactions["B"]["Ry"], 5.0, rel_tol=1e-5)

    def test_ultra_stiff_vs_ultra_flexible_stiffness_contrast_1e8(self):
        """Members with EA contrast of 10^8:1 in the same determinate truss."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1e8},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -100.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True
        members = {m["id"]: m["N"] for m in res["members"]}
        expected_N_AC = -50.0 * math.sqrt(13) / 3.0
        assert math.isclose(members["AC"], expected_N_AC, rel_tol=1e-5)
        assert math.isclose(members["BC"], expected_N_AC, rel_tol=1e-5)

    def test_stiffness_contrast_1e12_in_hyperstatic_does_not_crash(self):
        """Indeterminate truss with extreme stiffness contrast 10^12."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 0.0, "support": "pin"},
                {"id": "C", "x": 3.0, "y": 3.0, "support": "none"},
                {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1e12},
                {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1.0},
                {"id": "DA", "a": "D", "b": "A", "EA": 1.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1.0},
            ],
            "loads": [{"node": "D", "Fx": 20.0, "Fy": 0.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True

    def test_nanometer_length_member_vs_kilometer_member(self):
        """Very short member (1 mm = 0.001 m) alongside 100 m member."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 100.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 50.0, "y": 10.0, "support": "none"},
                {"id": "D", "x": 50.001, "y": 10.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 10000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 10000.0},
                {"id": "DB", "a": "D", "b": "B", "EA": 10000.0},
                {"id": "CB", "a": "C", "b": "B", "EA": 10000.0},
            ],
            "loads": [{"node": "D", "Fx": 0.0, "Fy": -15.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True


# ==============================================================================
# CATEGORY 2: EXTREME LOADING MAGNITUDES (MEGA vs NANO)
# ==============================================================================

class TestExtremeLoadingMagnitudes:
    """Stress tests with mega-loads (10^7, 10^12 kN) and nano-loads (10^-7, 10^-12 kN)."""

    def test_mega_load_1e7_kn(self):
        """Mega-load of 10,000,000 kN on standard triangle."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1e9},
                {"id": "AC", "a": "A", "b": "C", "EA": 1e9},
                {"id": "BC", "a": "B", "b": "C", "EA": 1e9},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -1e7}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True
        reactions = {r["node"]: r for r in res["reactions"]}
        assert math.isclose(reactions["A"]["Ry"], 5e6, rel_tol=1e-6)
        assert math.isclose(reactions["B"]["Ry"], 5e6, rel_tol=1e-6)

    def test_giga_load_1e12_kn(self):
        """Load of 10^12 kN (teranewton range)."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 6.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 3.0, "y": 4.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1e14},
                {"id": "AC", "a": "A", "b": "C", "EA": 1e14},
                {"id": "BC", "a": "B", "b": "C", "EA": 1e14},
            ],
            "loads": [{"node": "C", "Fx": 1e12, "Fy": -2e12}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True

    def test_nano_load_1e_minus_7_kn(self):
        """Nano-load of 10^-7 kN (0.1 milli-newtons)."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 10000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 10000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -1e-7}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True
        reactions = {r["node"]: r for r in res["reactions"]}
        assert math.isclose(reactions["A"]["Ry"], 0.5e-7, rel_tol=1e-5)
        assert math.isclose(reactions["B"]["Ry"], 0.5e-7, rel_tol=1e-5)

    def test_pico_load_1e_minus_10_kn_behavior(self):
        """Probing pico-load (10^-10 kN). Verify graceful numerical handling."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 10000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 10000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -1e-10}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True


# ==============================================================================
# CATEGORY 3: ADVERSE & NEAR-SINGULAR ANGLES
# ==============================================================================

class TestAdverseAngles:
    """Stress tests with non-trivial and near-orthogonal/near-collinear angles."""

    def test_adverse_angle_17_point_3_degrees(self):
        """Triangle with 17.3° inclination."""
        theta_rad = math.radians(17.3)
        span = 10.0
        height = span * math.tan(theta_rad)
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": span, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 0.0, "y": height, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 10000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 10000.0},
            ],
            "loads": [{"node": "C", "Fx": 25.0, "Fy": -40.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True
        assert res["crossCheck"]["passed"] is True
        assert res["crossCheck"]["maxDifference"] < 1e-7

    def test_adverse_angle_89_point_9_degrees(self):
        """Nearly vertical strut at 89.9° (0.1° from 90°)."""
        theta_rad = math.radians(89.9)
        L = 10.0
        dx = L * math.cos(theta_rad)
        dy = L * math.sin(theta_rad)
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 5.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": dx, "y": dy, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 50000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 50000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 50000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -100.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True
        assert res["crossCheck"]["passed"] is True

    def test_grazing_angle_0_point_01_degrees(self):
        """Nearly flat roof at 0.01° (0.000174 rad)."""
        theta_rad = math.radians(0.01)
        half_span = 50.0
        height = half_span * math.tan(theta_rad)
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2 * half_span, "y": 0.0, "support": "roller"},
                {"id": "C", "x": half_span, "y": height, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1e6},
                {"id": "AC", "a": "A", "b": "C", "EA": 1e6},
                {"id": "BC", "a": "B", "b": "C", "EA": 1e6},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -1.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True


# ==============================================================================
# CATEGORY 4: KINEMATIC LINKAGES, MECHANISMS & INSTABILITIES
# ==============================================================================

class TestKinematicMechanisms:
    """Stress tests on unstable linkages to verify graceful error codes."""

    def test_unbraced_4_bar_linkage(self):
        """Square frame without diagonal brace: 1 kinematic DOF."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "D", "x": 0.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1000.0},
                {"id": "DA", "a": "D", "b": "A", "EA": 1000.0},
            ],
            "loads": [{"node": "D", "Fx": 10.0, "Fy": 0.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] in {"hypostatic", "mechanism"} for e in res["errors"])

    def test_unbraced_5_bar_pentagon(self):
        """Pentagonal ring: multiple internal kinematic degrees of freedom."""
        r = 5.0
        nodes = []
        for i in range(5):
            angle = i * 2 * math.pi / 5
            supp = "pin" if i == 0 else ("roller" if i == 1 else "none")
            nodes.append({"id": f"N{i}", "x": r * math.cos(angle), "y": r * math.sin(angle), "support": supp})
        members = [
            {"id": f"M{i}", "a": f"N{i}", "b": f"N{(i+1)%5}", "EA": 1000.0}
            for i in range(5)
        ]
        payload = {"nodes": nodes, "members": members, "loads": [{"node": "N2", "Fx": 0.0, "Fy": -10.0}]}
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] in {"hypostatic", "mechanism"} for e in res["errors"])

    def test_collinear_three_roller_mechanism(self):
        """Three rollers all in Y direction: unrestrained rigid body motion in X."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "roller"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 3.0, "support": "roller"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
                {"id": "CA", "a": "C", "b": "A", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 10.0, "Fy": 0.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] in {"hypostatic", "mechanism"} for e in res["errors"])

    def test_mechanism_with_zero_loads(self):
        """An unstable mechanism with NO applied loads must still be rejected."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "D", "x": 0.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1000.0},
                {"id": "DA", "a": "D", "b": "A", "EA": 1000.0},
            ],
            "loads": [],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] in {"hypostatic", "mechanism"} for e in res["errors"])

    def test_critical_internal_mechanism_b_plus_r_equals_2n(self):
        """Arch with three collinear hinges: A(0,0), B(4,0), and C(2,0).
        b + r = 6 + 4 = 10 == 2n (g = 0 count), but has an internal mechanism.
        """
        return self.test_critical_internal_mechanism_collinear_three_hinge_arch()

    def test_critical_internal_mechanism_collinear_three_hinge_arch(self):
        """Arch with three collinear hinges: A(0,0), B(4,0), and C(2,0).
        b + r = 6 + 4 = 10 == 2n (g = 0 count), but has an internal rotational mechanism.
        """
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "pin"},
                {"id": "C", "x": 2.0, "y": 0.0, "support": "none"},
                {"id": "D", "x": 0.0, "y": 2.0, "support": "none"},
                {"id": "E", "x": 4.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 1000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
                {"id": "BE", "a": "B", "b": "E", "EA": 1000.0},
                {"id": "CE", "a": "C", "b": "E", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] == "mechanism" for e in res["errors"])

    def test_unbraced_bay_with_overbraced_bay_b_plus_r_equals_2n(self):
        """Bay 1 has double X-brace (hyperstatic), Bay 2 has no diagonal (mechanism).
        Overall count b + r = 2n (g = 0), but Bay 2 can shear freely.
        """
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "D", "x": 0.0, "y": 2.0, "support": "none"},
                {"id": "E", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "F", "x": 4.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AD", "a": "A", "b": "D", "EA": 1000.0},
                {"id": "DE", "a": "D", "b": "E", "EA": 1000.0},
                {"id": "EB", "a": "E", "b": "B", "EA": 1000.0},
                {"id": "BA", "a": "B", "b": "A", "EA": 1000.0},
                {"id": "AE", "a": "A", "b": "E", "EA": 1000.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 1000.0},
                {"id": "EF", "a": "E", "b": "F", "EA": 1000.0},
                {"id": "FC", "a": "F", "b": "C", "EA": 1000.0},
                {"id": "CB", "a": "C", "b": "B", "EA": 1000.0},
            ],
            "loads": [{"node": "F", "Fx": 10.0, "Fy": 0.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] == "mechanism" for e in res["errors"])


# ==============================================================================
# CATEGORY 5: COLLINEAR NODES & REDUNDANT TIES
# ==============================================================================

class TestCollinearNodesAndRedundantTies:
    """Stress tests on collinear chords, internal nodes, and redundant members."""

    def test_straight_line_three_collinear_nodes_unbraced(self):
        """Three nodes in a straight line: A(0,0) - B(2,0) - C(4,0) with no lateral restraint at B."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 2.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 4.0, "y": 0.0, "support": "roller"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [{"node": "B", "Fx": 0.0, "Fy": -5.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] in {"hypostatic", "mechanism"} for e in res["errors"])

    def test_collinear_bottom_chord_in_stable_truss(self):
        """Stable Pratt truss with multiple collinear chord segments."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 6.0, "y": 0.0, "support": "roller"},
                {"id": "D", "x": 3.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 10000.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 10000.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 10000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 10000.0},
            ],
            "loads": [{"node": "B", "Fx": 0.0, "Fy": -20.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["checks"]["passed"] is True
        assert any("colinear" in w.lower() or "alinhad" in w.lower() for w in res["warnings"])

    def test_multi_bay_truss_with_triple_redundant_ties(self):
        """Indeterminate truss with degree g = 3."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 3.0, "y": 0.0, "support": "none"},
                {"id": "C", "x": 6.0, "y": 0.0, "support": "pin"},
                {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
                {"id": "E", "x": 3.0, "y": 3.0, "support": "none"},
                {"id": "F", "x": 6.0, "y": 3.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0},
                {"id": "DE", "a": "D", "b": "E", "EA": 10000.0},
                {"id": "AD", "a": "A", "b": "D", "EA": 10000.0},
                {"id": "BE", "a": "B", "b": "E", "EA": 10000.0},
                {"id": "AE", "a": "A", "b": "E", "EA": 10000.0},
                {"id": "BD", "a": "B", "b": "D", "EA": 10000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 10000.0},
                {"id": "EF", "a": "E", "b": "F", "EA": 10000.0},
                {"id": "CF", "a": "C", "b": "F", "EA": 10000.0},
                {"id": "BF", "a": "B", "b": "F", "EA": 10000.0},
                {"id": "CE", "a": "C", "b": "E", "EA": 10000.0},
            ],
            "loads": [{"node": "E", "Fx": 15.0, "Fy": -30.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "ok"
        assert res["determinacy"]["degree"] > 0
        assert res["checks"]["passed"] is True


# ==============================================================================
# CATEGORY 6: FLOATING AND ISOLATED NODES
# ==============================================================================

class TestFloatingAndIsolatedNodes:
    """Stress tests on unsupported or isolated nodes."""

    def test_isolated_unsupported_node_rejected_as_mechanism(self):
        """Truss with a valid triangle PLUS an isolated free node."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "FLOATING", "x": 10.0, "y": 10.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any("mechanism" in e["code"] or "hypostatic" in e["code"] for e in res["errors"])

    def test_isolated_node_with_load_rejected(self):
        """Isolated free node carrying an external load."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "ISOLATED", "x": 5.0, "y": 5.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [{"node": "ISOLATED", "Fx": 10.0, "Fy": 0.0}],
        }
        res = solve_payload(payload)
        assert res["status"] == "error"


# ==============================================================================
# CATEGORY 7: PATHOLOGICAL INPUTS & API ROBUSTNESS
# ==============================================================================

class TestPathologicalInputsAndApiFuzzing:
    """Probing API robustness against malicious or pathological payloads."""

    def test_nan_coordinates_rejected_gracefully(self):
        """NaN coordinate should return 200 with error status, never 500 crash."""
        payload = {
            "nodes": [
                {"id": "A", "x": "nan", "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [],
        }
        resp = client.post("/api/solve", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"
        assert any(e["code"] in {"bad_number", "invalid_input"} for e in body["errors"])

    def test_infinity_coordinates_rejected_gracefully(self):
        """Infinity coordinate should return status error."""
        payload = {
            "nodes": [
                {"id": "A", "x": "inf", "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B", "EA": 1000.0}],
            "loads": [],
        }
        resp = client.post("/api/solve", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_zero_stiffness_ea_rejected(self):
        """EA <= 0 must be rejected."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 0.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [],
        }
        resp = client.post("/api/solve", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"

    def test_negative_stiffness_ea_rejected(self):
        """EA < 0 must be rejected."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": -500.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            ],
            "loads": [],
        }
        resp = client.post("/api/solve", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_invalid_support_type_rejected(self):
        """Unsupported support string e.g. 'fixed' or 'clamped'."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "fixed_clamped"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            ],
            "members": [{"id": "AB", "a": "A", "b": "B"}],
            "loads": [],
        }
        resp = client.post("/api/solve", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_api_report_endpoint_with_mechanism_does_not_500(self):
        """Posting an unstable mechanism to /api/report returns graceful explanation."""
        payload = {
            "model": {
                "nodes": [
                    {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                    {"id": "B", "x": 2.0, "y": 0.0, "support": "roller"},
                    {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
                    {"id": "D", "x": 0.0, "y": 2.0, "support": "none"},
                ],
                "members": [
                    {"id": "AB", "a": "A", "b": "B"},
                    {"id": "BC", "a": "B", "b": "C"},
                    {"id": "CD", "a": "C", "b": "D"},
                    {"id": "DA", "a": "D", "b": "A"},
                ],
                "loads": [],
            }
        }
        resp = client.post("/api/report", json=payload)
        assert resp.status_code == 200
        assert "Não foi possível gerar o relatório" in resp.text

    def test_api_stress_with_zero_or_negative_allowable(self):
        """Allowable stress <= 0 must return error status."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0, "area": 100.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0, "area": 100.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0, "area": 100.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        resp = client.post("/api/stress", json={"model": model, "mode": "area", "allowable": -150.0})
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"

    def test_empty_payloads(self):
        """Empty json or invalid root types."""
        assert client.post("/api/solve", json={}).json()["status"] == "error"
        assert client.post("/api/solve", json={"nodes": []}).json()["status"] == "error"


# ==============================================================================
# CATEGORY 8: BUG REPRODUCTION & ADVERSARIAL ORACLES
# ==============================================================================

class TestAdversarialBugOracles:
    """Empirical reproduction of vulnerabilities found in the codebase."""

    def test_unhandled_500_on_api_stress_with_non_numeric_allowable(self):
        """BUG 1: POST /api/stress returns 200 with status=error when allowable is non-numeric string."""
        model = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0, "area": 100.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000.0, "area": 100.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0, "area": 100.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        resp = client.post("/api/stress", json={"model": model, "mode": "area", "allowable": "non_numeric_string"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"
        assert body.get("code") == "bad_allowable" or any(e.get("code") == "bad_allowable" for e in body.get("errors", []))

    def test_stress_entries_force_unit_discrepancy(self):
        """BUG 2A: res['stress']['entries'][i]['N'] is converted to user force units."""
        payload = {
            "units": {"force": "N", "length": "m", "area": "mm²", "stress": "MPa"},
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000000.0, "area": 100.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 1000000.0, "area": 100.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000000.0, "area": 100.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -1000.0}],  # 1000 N
        }
        res = solve_payload(payload)
        # res['members'][0]['N'] is 500.0 N
        assert math.isclose(res["members"][0]["N"], 500.0, abs_tol=1e-5)
        # res['stress']['entries'][0]['N'] must also be 500.0 N
        stress_N = res["stress"]["entries"][0]["N"]
        assert math.isclose(stress_N, 500.0, abs_tol=1e-5)
        assert math.isclose(res["members"][0]["N"], stress_N, abs_tol=1e-5)

    def test_reverse_section_sizing_non_mpa_allowable_discrepancy(self):
        """BUG 2B: stress_payload mode='area' converts allowable from input stress units (e.g. GPa or ksi) to MPa."""
        model = {
            "units": {"force": "kN", "length": "m", "area": "mm²", "stress": "GPa"},
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 10000.0, "area": 100.0},
                {"id": "AC", "a": "A", "b": "C", "EA": 10000.0, "area": 100.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 10000.0, "area": 100.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
        }
        # Allowable is 0.25 GPa (= 250 MPa). With N = 5 kN (5000 N), required area should be 5000/250 = 20 mm².
        res = stress_payload(model, mode="area", allowable=0.25)
        req_area = res["stress"]["entries"][0]["requiredArea"]
        assert math.isclose(req_area, 20.0, abs_tol=1e-3)
        assert math.isclose(res["stress"]["entries"][0]["allowable"], 0.25, abs_tol=1e-5)
        assert math.isclose(res["stress"]["allowable"]["tension"], 0.25, abs_tol=1e-5)
        assert math.isclose(res["stress"]["allowable"]["compression"], 0.25, abs_tol=1e-5)
