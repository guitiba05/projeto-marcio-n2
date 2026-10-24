"""Adversarial Oracle & Dual-Method Verification Test Suite.

Author: challenger_adversarial_2
Role: Adversarial Oracle and Dual-Method Challenger 2

This test suite independently probes:
1. Closed-form static node balance oracle (independent of DSM) tested on arbitrary determinate trusses.
2. Symbolic rational node balance oracle using SymPy.
3. Zero-force member detection rules R1, R2, R3:
   - Invariance of remaining member forces when true zero-force members are removed.
   - Immediate activation and linear force response under small loads applied to zero-force nodes.
   - Cascading multi-tier zero-force chains.
4. Strict static equilibrium residual compliance on all 12 presets:
   - |sum Fx| < 10^-6 kN
   - |sum Fy| < 10^-6 kN
   - |sum M(0,0)| < 10^-6 kN*m
   - |sum M(center)| < 10^-6 kN*m
   - max nodal residual < 10^-6 kN
   - Graceful, non-crashing rejection of hypostatic and mechanism cases.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
import pytest
import sympy as sp

from conftest import CASES, ERROR_CASES, OK_CASES
from app.core.determinacy import analyze_determinacy
from app.core.errors import DeterminacyError
from app.core.joints import method_of_joints
from app.core.model import parse_truss
from app.core.solver import solve_payload
from app.core.stiffness import analyze
from app.core.zero_force import find_zero_force_rules, summarize_zero_force


# ==============================================================================
# INDEPENDENT VERIFICATION ORACLE (From First Principles)
# ==============================================================================

class IndependentStaticOracle:
    """Independent static node equilibrium oracle.
    
    Constructs the global static node balance equations:
        sum_e (N_e * unit_vector_outward) + F_ext + R = 0
    without using element stiffness matrices, Young's modulus, or displacements.
    """

    @staticmethod
    def solve_determinate(payload: dict) -> tuple[dict[str, float], dict[str, float]]:
        nodes = {n["id"]: np.array([n["x"], n["y"]], dtype=float) for n in payload["nodes"]}
        node_ids = sorted(list(nodes.keys()))
        node_idx = {nid: i for i, nid in enumerate(node_ids)}
        n = len(node_ids)

        members = payload["members"]
        b = len(members)

        restr: list[tuple[str, str, np.ndarray]] = []
        for n_item in payload["nodes"]:
            supp = n_item.get("support", "none")
            nid = n_item["id"]
            if supp == "pin":
                restr.append((nid, "ux", np.array([1.0, 0.0])))
                restr.append((nid, "uy", np.array([0.0, 1.0])))
            elif supp in ("roller", "roller_y"):
                restr.append((nid, "uy", np.array([0.0, 1.0])))
            elif supp == "roller_x":
                restr.append((nid, "ux", np.array([1.0, 0.0])))

        r = len(restr)
        if b + r != 2 * n:
            raise ValueError(f"Oracle requires determinate truss: b+r={b+r} != 2n={2*n}")

        C = np.zeros((2 * n, b + r), dtype=float)
        rhs = np.zeros(2 * n, dtype=float)

        for j, m in enumerate(members):
            a_id, b_id = m["a"], m["b"]
            vec = nodes[b_id] - nodes[a_id]
            length = float(np.linalg.norm(vec))
            u_ab = vec / length
            ia = node_idx[a_id]
            ib = node_idx[b_id]
            C[2 * ia : 2 * ia + 2, j] += u_ab
            C[2 * ib : 2 * ib + 2, j] -= u_ab

        for k, (nid, comp, dir_vec) in enumerate(restr):
            i = node_idx[nid]
            C[2 * i : 2 * i + 2, b + k] += dir_vec

        for load in payload.get("loads", []):
            i = node_idx[load["node"]]
            rhs[2 * i] -= float(load.get("Fx", 0.0))
            rhs[2 * i + 1] -= float(load.get("Fy", 0.0))

        if np.linalg.matrix_rank(C) < 2 * n:
            raise ValueError("Equilibrium matrix singular: mechanism present")

        sol = np.linalg.solve(C, rhs)
        member_forces = {m["id"]: float(sol[j]) for j, m in enumerate(members)}
        reactions = {f"{restr[k][0]}_{restr[k][1]}": float(sol[b + k]) for k in range(r)}
        return member_forces, reactions

    @staticmethod
    def solve_symbolic_rational(payload: dict) -> tuple[dict[str, float], dict[str, float]]:
        """Exact rational equilibrium solver using SymPy."""
        nodes = {n["id"]: (sp.Rational(str(n["x"])), sp.Rational(str(n["y"]))) for n in payload["nodes"]}
        members = payload["members"]
        member_syms = {m["id"]: sp.Symbol(f"N_{m['id']}") for m in members}

        reaction_syms = {}
        for n_item in payload["nodes"]:
            supp = n_item.get("support", "none")
            nid = n_item["id"]
            if supp == "pin":
                reaction_syms[(nid, "ux")] = sp.Symbol(f"R_{nid}_ux")
                reaction_syms[(nid, "uy")] = sp.Symbol(f"R_{nid}_uy")
            elif supp in ("roller", "roller_y"):
                reaction_syms[(nid, "uy")] = sp.Symbol(f"R_{nid}_uy")
            elif supp == "roller_x":
                reaction_syms[(nid, "ux")] = sp.Symbol(f"R_{nid}_ux")

        eqs = []
        for n_item in payload["nodes"]:
            nid = n_item["id"]
            fx_expr = sp.Rational(0)
            fy_expr = sp.Rational(0)

            for load in payload.get("loads", []):
                if load["node"] == nid:
                    fx_expr += sp.Rational(str(load.get("Fx", 0.0)))
                    fy_expr += sp.Rational(str(load.get("Fy", 0.0)))

            if (nid, "ux") in reaction_syms:
                fx_expr += reaction_syms[(nid, "ux")]
            if (nid, "uy") in reaction_syms:
                fy_expr += reaction_syms[(nid, "uy")]

            for m in members:
                if m["a"] == nid or m["b"] == nid:
                    other_id = m["b"] if m["a"] == nid else m["a"]
                    dx = float(nodes[other_id][0] - nodes[nid][0])
                    dy = float(nodes[other_id][1] - nodes[nid][1])
                    length = math.hypot(dx, dy)
                    c = dx / length
                    s = dy / length
                    fx_expr += sp.Rational(str(round(c, 14))) * member_syms[m["id"]]
                    fy_expr += sp.Rational(str(round(s, 14))) * member_syms[m["id"]]

            eqs.append(fx_expr)
            eqs.append(fy_expr)

        all_vars = list(member_syms.values()) + list(reaction_syms.values())
        sol = sp.solve(eqs, all_vars)
        if not sol:
            raise ValueError("SymPy failed to resolve system")

        member_forces = {m["id"]: float(sol[member_syms[m["id"]]]) for m in members}
        reactions = {f"{k[0]}_{k[1]}": float(sol[v]) for k, v in reaction_syms.items()}
        return member_forces, reactions


def generate_simple_determinate_truss(seed: int, num_added_nodes: int = 5) -> dict:
    """Procedurally generates an arbitrary simple determinate 2D truss."""
    rng = random.Random(seed)
    nodes = [
        {"id": "N0", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "N1", "x": 4.0, "y": 0.0, "support": "roller"},
        {"id": "N2", "x": 2.0, "y": 3.0, "support": "none"},
    ]
    members = [
        {"id": "M01", "a": "N0", "b": "N1", "EA": 200000.0},
        {"id": "M02", "a": "N0", "b": "N2", "EA": 200000.0},
        {"id": "M12", "a": "N1", "b": "N2", "EA": 200000.0},
    ]
    node_ids = ["N0", "N1", "N2"]

    for idx in range(3, 3 + num_added_nodes):
        nid = f"N{idx}"
        i, j = rng.sample(node_ids, 2)
        ni = next(n for n in nodes if n["id"] == i)
        nj = next(n for n in nodes if n["id"] == j)

        for _ in range(100):
            xk = round(rng.uniform(-3.0, 12.0), 2)
            yk = round(rng.uniform(1.0, 10.0), 2)
            cross = (ni["x"] - xk) * (nj["y"] - yk) - (ni["y"] - yk) * (nj["x"] - xk)
            if abs(cross) > 1.5:
                break

        nodes.append({"id": nid, "x": xk, "y": yk, "support": "none"})
        members.append({"id": f"M_{nid}_{i}", "a": nid, "b": i, "EA": 200000.0})
        members.append({"id": f"M_{nid}_{j}", "a": nid, "b": j, "EA": 200000.0})
        node_ids.append(nid)

    loads = []
    for nid in node_ids:
        if rng.random() > 0.4:
            loads.append({
                "node": nid,
                "Fx": round(rng.uniform(-25.0, 25.0), 2),
                "Fy": round(rng.uniform(-40.0, 40.0), 2),
            })
    if not loads:
        loads.append({"node": "N2", "Fx": 12.0, "Fy": -18.0})

    return {"nodes": nodes, "members": members, "loads": loads, "units": {"force": "kN", "length": "m"}}


# ==============================================================================
# OBJECTIVE 1: INDEPENDENT VERIFICATION ORACLE VS DSM
# ==============================================================================

class TestAdversarialIndependentOracle:
    """Verifies DSM outputs against completely independent static node balance oracles."""

    DETERMINATE_SLUGS = [
        "01-triangulo",
        "02-telhado-pratt",
        "03-warren",
        "04-pratt-vento",
        "05-forca-zero-T",
        "06-forca-zero-R3",
        "07-geometria-irregular",
        "11-sem-carga",
        "12-pratt-grande",
    ]

    @pytest.mark.parametrize("slug", DETERMINATE_SLUGS)
    def test_canonical_determinate_trusses_vs_oracle(self, slug: str) -> None:
        case = next(c for c in OK_CASES if c["slug"] == slug)
        oracle_forces, oracle_reactions = IndependentStaticOracle.solve_determinate(case["input"])

        dsm_res = solve_payload(case["input"])
        assert dsm_res["status"] == "ok"

        dsm_forces = {m["id"]: m["N"] for m in dsm_res["members"]}
        for mid, o_force in oracle_forces.items():
            d_force = dsm_forces[mid]
            assert math.isclose(d_force, o_force, abs_tol=1e-7), (
                f"Discrepancy on {slug} member {mid}: DSM={d_force}, Oracle={o_force}"
            )

    def test_symbolic_rational_oracle_case01(self) -> None:
        case = next(c for c in OK_CASES if c["slug"] == "01-triangulo")
        sym_forces, _ = IndependentStaticOracle.solve_symbolic_rational(case["input"])
        dsm_res = solve_payload(case["input"])
        for m in dsm_res["members"]:
            assert math.isclose(m["N"], sym_forces[m["id"]], abs_tol=1e-7)

    def test_symbolic_rational_oracle_case05(self) -> None:
        case = next(c for c in OK_CASES if c["slug"] == "05-forca-zero-T")
        sym_forces, _ = IndependentStaticOracle.solve_symbolic_rational(case["input"])
        dsm_res = solve_payload(case["input"])
        for m in dsm_res["members"]:
            assert math.isclose(m["N"], sym_forces[m["id"]], abs_tol=1e-7)

    def test_symbolic_rational_oracle_case06(self) -> None:
        case = next(c for c in OK_CASES if c["slug"] == "06-forca-zero-R3")
        sym_forces, _ = IndependentStaticOracle.solve_symbolic_rational(case["input"])
        dsm_res = solve_payload(case["input"])
        for m in dsm_res["members"]:
            assert math.isclose(m["N"], sym_forces[m["id"]], abs_tol=1e-7)

    @pytest.mark.parametrize("seed", list(range(10)))
    def test_arbitrary_random_determinate_trusses(self, seed: int) -> None:
        payload = generate_simple_determinate_truss(seed=seed, num_added_nodes=6)
        oracle_forces, _ = IndependentStaticOracle.solve_determinate(payload)

        dsm_res = solve_payload(payload)
        assert dsm_res["status"] == "ok"

        dsm_forces = {m["id"]: m["N"] for m in dsm_res["members"]}
        worst_diff = max(abs(oracle_forces[mid] - dsm_forces[mid]) for mid in oracle_forces)
        assert worst_diff < 1e-7, f"Random truss seed {seed} failed with max diff {worst_diff}"

    def test_indeterminate_truss_equilibrium_subspace(self) -> None:
        """Proves that for hyperstatic Case 08, DSM solution strictly satisfies C * x = rhs."""
        case = next(c for c in OK_CASES if c["slug"] == "08-hiperestatica")
        payload = case["input"]

        nodes = {n["id"]: np.array([n["x"], n["y"]], dtype=float) for n in payload["nodes"]}
        node_ids = sorted(list(nodes.keys()))
        node_idx = {nid: i for i, nid in enumerate(node_ids)}
        n = len(node_ids)
        members = payload["members"]
        b = len(members)

        restr = []
        for n_item in payload["nodes"]:
            supp = n_item.get("support", "none")
            nid = n_item["id"]
            if supp == "pin":
                restr.append((nid, "ux", np.array([1.0, 0.0])))
                restr.append((nid, "uy", np.array([0.0, 1.0])))
            elif supp in ("roller", "roller_y"):
                restr.append((nid, "uy", np.array([0.0, 1.0])))
            elif supp == "roller_x":
                restr.append((nid, "ux", np.array([1.0, 0.0])))
        r = len(restr)

        C = np.zeros((2 * n, b + r), dtype=float)
        rhs = np.zeros(2 * n, dtype=float)

        for j, m in enumerate(members):
            a_id, b_id = m["a"], m["b"]
            vec = nodes[b_id] - nodes[a_id]
            length = float(np.linalg.norm(vec))
            u_ab = vec / length
            ia = node_idx[a_id]
            ib = node_idx[b_id]
            C[2 * ia : 2 * ia + 2, j] += u_ab
            C[2 * ib : 2 * ib + 2, j] -= u_ab

        for k, (nid, comp, dir_vec) in enumerate(restr):
            i = node_idx[nid]
            C[2 * i : 2 * i + 2, b + k] += dir_vec

        for load in payload.get("loads", []):
            i = node_idx[load["node"]]
            rhs[2 * i] -= float(load.get("Fx", 0.0))
            rhs[2 * i + 1] -= float(load.get("Fy", 0.0))

        dsm_res = solve_payload(payload)
        x_dsm = np.zeros(b + r, dtype=float)
        for j, m in enumerate(members):
            x_dsm[j] = next(item["N"] for item in dsm_res["members"] if item["id"] == m["id"])
        for k, (nid, comp, _) in enumerate(restr):
            r_item = next(item for item in dsm_res["reactions"] if item["node"] == nid)
            val = r_item["Rx"] if comp == "ux" else r_item["Ry"]
            x_dsm[b + k] = val

        residual = np.linalg.norm(C @ x_dsm - rhs)
        assert residual < 1e-12, f"Hyperstatic Case 08 violated static equilibrium: {residual}"

        # Method of joints should explicitly signal that hyperstatic truss is not isostatic
        truss = parse_truss(payload)
        cross = dsm_res["crossCheck"]
        assert cross["available"] is False
        assert "isostática" in cross["reason"]


# ==============================================================================
# OBJECTIVE 2: PROBE ZERO-FORCE RULES R1, R2, R3 (INVARIANCE & ACTIVATION)
# ==============================================================================

class TestAdversarialZeroForceInvariants:
    """Probes zero-force detection rules R1, R2, R3 under member removal and perturbation loads."""

    def test_r1_unloaded_single_bar_mechanics(self) -> None:
        """Verifies Rule R1 and confirms hypostatic rejection in 2D linear stiffness."""
        payload = {
            "nodes": [
                {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
                {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
                {"id": "C", "x": 2.0, "y": 2.0, "support": "none"},
                {"id": "D", "x": 2.0, "y": 4.0, "support": "none"},
            ],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
                {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
                {"id": "CA", "a": "C", "b": "A", "EA": 1000.0},
                {"id": "CD", "a": "C", "b": "D", "EA": 1000.0},
            ],
            "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
            "units": {"force": "kN", "length": "m"},
        }
        truss = parse_truss(payload)
        rules = find_zero_force_rules(truss)
        assert "CD" in rules
        assert "R1" in rules["CD"]

        # 2D linear DSM correctly recognizes that dangling node D creates a mechanism (hypostatic)
        res = solve_payload(payload)
        assert res["status"] == "error"
        assert any(e["code"] == "hypostatic" for e in res["errors"])

    def test_r2_removal_invariance_case05(self) -> None:
        """Case 05: Removing R2 members CD and DA leaves all other member forces invariant."""
        case = next(c for c in OK_CASES if c["slug"] == "05-forca-zero-T")
        payload1 = case["input"]
        res1 = solve_payload(payload1)
        forces1 = {m["id"]: m["N"] for m in res1["members"]}

        payload2 = {
            "units": payload1["units"],
            "nodes": [n for n in payload1["nodes"] if n["id"] != "D"],
            "members": [m for m in payload1["members"] if m["id"] not in ("CD", "DA")],
            "loads": payload1["loads"],
        }
        res2 = solve_payload(payload2)
        forces2 = {m["id"]: m["N"] for m in res2["members"]}

        for mid in forces2:
            assert math.isclose(forces2[mid], forces1[mid], abs_tol=1e-12), (
                f"Member {mid} changed after removing R2 zero-force members: "
                f"{forces1[mid]} vs {forces2[mid]}"
            )

    def test_r2_load_activation_case05(self) -> None:
        """Case 05: Applying load to zero-force node D activates CD and DA linearly."""
        case = next(c for c in OK_CASES if c["slug"] == "05-forca-zero-T")
        base_payload = case["input"]

        for eps in (1e-5, 1e-3, 0.5, 2.0):
            pert_payload = {
                "units": base_payload["units"],
                "nodes": base_payload["nodes"],
                "members": base_payload["members"],
                "loads": base_payload["loads"] + [{"node": "D", "Fx": 2.5 * eps, "Fy": -4.0 * eps}],
            }
            res = solve_payload(pert_payload)
            forces = {m["id"]: m["N"] for m in res["members"]}

            # Statics at node D: CD is horizontal, DA is vertical
            # sum Fx = N_CD * 1 + Fx_D = 0 => N_CD = -Fx_D = -2.5 * eps
            # sum Fy = N_DA * (-1) + Fy_D = 0 => N_DA = Fy_D = -4.0 * eps
            assert math.isclose(forces["CD"], -2.5 * eps, abs_tol=1e-8)
            assert math.isclose(forces["DA"], -4.0 * eps, abs_tol=1e-8)
            assert res["checks"]["passed"] is True

    def test_r3_removal_invariance_case06(self) -> None:
        """Case 06: Removing R3 zero-force strut CT leaves AT, BT and bottom chord forces invariant."""
        case = next(c for c in OK_CASES if c["slug"] == "06-forca-zero-R3")
        payload1 = case["input"]
        res1 = solve_payload(payload1)
        forces1 = {m["id"]: m["N"] for m in res1["members"]}

        # Unsegment collinear bottom chord AC + CB -> AB
        payload2 = {
            "units": payload1["units"],
            "nodes": [n for n in payload1["nodes"] if n["id"] != "C"],
            "members": [
                {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
                {"id": "AT", "a": "A", "b": "T", "EA": 1.0},
                {"id": "BT", "a": "B", "b": "T", "EA": 1.0},
            ],
            "loads": payload1["loads"],
        }
        res2 = solve_payload(payload2)
        forces2 = {m["id"]: m["N"] for m in res2["members"]}

        assert math.isclose(forces2["AT"], forces1["AT"], abs_tol=1e-12)
        assert math.isclose(forces2["BT"], forces1["BT"], abs_tol=1e-12)
        assert math.isclose(forces2["AB"], forces1["AC"], abs_tol=1e-12)

    def test_r3_removal_invariance_case02_pratt_roof(self) -> None:
        """Case 02: Removing zero-force struts C1T1 and C3T3 leaves all 9 remaining members invariant."""
        case = next(c for c in OK_CASES if c["slug"] == "02-telhado-pratt")
        payload1 = case["input"]
        res1 = solve_payload(payload1)
        forces1 = {m["id"]: m["N"] for m in res1["members"]}

        payload2 = {
            "units": payload1["units"],
            "nodes": [n for n in payload1["nodes"] if n["id"] not in ("C1", "C3")],
            "members": [
                {"id": "AC2", "a": "A", "b": "C2", "EA": 1.0},
                {"id": "C2E", "a": "C2", "b": "E", "EA": 1.0},
                {"id": "AT1", "a": "A", "b": "T1", "EA": 1.0},
                {"id": "T1T2", "a": "T1", "b": "T2", "EA": 1.0},
                {"id": "T2T3", "a": "T2", "b": "T3", "EA": 1.0},
                {"id": "T3E", "a": "T3", "b": "E", "EA": 1.0},
                {"id": "C2T2", "a": "C2", "b": "T2", "EA": 1.0},
                {"id": "T1C2", "a": "T1", "b": "C2", "EA": 1.0},
                {"id": "T3C2", "a": "T3", "b": "C2", "EA": 1.0},
            ],
            "loads": payload1["loads"],
        }
        res2 = solve_payload(payload2)
        forces2 = {m["id"]: m["N"] for m in res2["members"]}

        for mid in ("AT1", "T1T2", "T2T3", "T3E", "C2T2", "T1C2", "T3C2"):
            assert math.isclose(forces2[mid], forces1[mid], abs_tol=1e-12)
        assert math.isclose(forces2["AC2"], forces1["AC1"], abs_tol=1e-12)
        assert math.isclose(forces2["C2E"], forces1["C3E"], abs_tol=1e-12)

    def test_r3_load_activation_case06_and_case02(self) -> None:
        """Applying perpendicular load to R3 joint immediately activates the third member."""
        # Case 06
        case6 = next(c for c in OK_CASES if c["slug"] == "06-forca-zero-R3")
        for val in (0.01, 1.0, 7.5):
            pert = {
                "units": case6["input"]["units"],
                "nodes": case6["input"]["nodes"],
                "members": case6["input"]["members"],
                "loads": case6["input"]["loads"] + [{"node": "C", "Fx": 0.0, "Fy": -val}],
            }
            res = solve_payload(pert)
            forces = {m["id"]: m["N"] for m in res["members"]}
            # Vertical equilibrium at C: N_CT + Fy_C = 0 => N_CT = val
            assert math.isclose(forces["CT"], val, abs_tol=1e-8)

        # Case 02
        case2 = next(c for c in OK_CASES if c["slug"] == "02-telhado-pratt")
        pert2 = {
            "units": case2["input"]["units"],
            "nodes": case2["input"]["nodes"],
            "members": case2["input"]["members"],
            "loads": case2["input"]["loads"] + [{"node": "C1", "Fx": 0.0, "Fy": -3.5}],
        }
        res2 = solve_payload(pert2)
        forces2 = {m["id"]: m["N"] for m in res2["members"]}
        assert math.isclose(forces2["C1T1"], 3.5, abs_tol=1e-8)
        assert math.isclose(forces2["C3T3"], 0.0, abs_tol=1e-8)

    def test_cascading_r2_chain_invariance_and_activation(self) -> None:
        """Cascading R2 chain: multi-tier zero-force members, force invariance, and tip activation."""
        nodes = [
            {"id": "N0", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "N1", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "N2", "x": 2.0, "y": 3.0, "support": "none"},
            {"id": "N3", "x": 4.0, "y": 3.0, "support": "none"},
            {"id": "N4", "x": 6.0, "y": 2.0, "support": "none"},
            {"id": "N5", "x": 8.0, "y": 2.0, "support": "none"},
        ]
        members = [
            {"id": "M01", "a": "N0", "b": "N1", "EA": 10000.0},
            {"id": "M02", "a": "N0", "b": "N2", "EA": 10000.0},
            {"id": "M12", "a": "N1", "b": "N2", "EA": 10000.0},
            {"id": "M13", "a": "N1", "b": "N3", "EA": 10000.0},
            {"id": "M23", "a": "N2", "b": "N3", "EA": 10000.0},
            {"id": "M14", "a": "N1", "b": "N4", "EA": 10000.0},
            {"id": "M34", "a": "N3", "b": "N4", "EA": 10000.0},
            {"id": "M35", "a": "N3", "b": "N5", "EA": 10000.0},
            {"id": "M45", "a": "N4", "b": "N5", "EA": 10000.0},
        ]
        loads = [{"node": "N2", "Fx": 0.0, "Fy": -20.0}]

        truss = parse_truss({"nodes": nodes, "members": members, "loads": loads, "units": {"force": "kN", "length": "m"}})
        res1 = analyze(truss)
        forces1 = {m.id: m.N for m in res1.members}

        # Verify all cascade members carry exactly zero force in DSM
        cascade_members = ["M13", "M14", "M23", "M34", "M35", "M45"]
        for cm in cascade_members:
            assert abs(forces1[cm]) < 1e-12

        # Invariance: remove all cascade nodes (N3, N4, N5) and members
        core_nodes = [n for n in nodes if n["id"] in ("N0", "N1", "N2")]
        core_members = [m for m in members if m["id"] in ("M01", "M02", "M12")]
        core_truss = parse_truss({"nodes": core_nodes, "members": core_members, "loads": loads, "units": {"force": "kN", "length": "m"}})
        res_core = analyze(core_truss)
        forces_core = {m.id: m.N for m in res_core.members}

        for cm in ("M01", "M02", "M12"):
            assert math.isclose(forces_core[cm], forces1[cm], abs_tol=1e-12)

        # Tip activation: apply load at N5 (breaking symmetric vertical cancellation)
        loads_tip = loads + [{"node": "N5", "Fx": 0.05, "Fy": -0.15}]
        truss_tip = parse_truss({"nodes": nodes, "members": members, "loads": loads_tip, "units": {"force": "kN", "length": "m"}})
        res_tip = analyze(truss_tip)
        forces_tip = {m.id: m.N for m in res_tip.members}

        for cm in cascade_members:
            assert abs(forces_tip[cm]) > 1e-4, f"Member {cm} failed to activate under tip load"


# ==============================================================================
# OBJECTIVE 3: STATIC EQUILIBRIUM RESIDUAL COMPLIANCE ON ALL 12 PRESETS
# ==============================================================================

class TestAdversarialResidualCompliance:
    """Verifies strict static equilibrium residual compliance |sum Fx, sum Fy, sum M| < 10^-6."""

    @pytest.mark.parametrize("case", OK_CASES, ids=lambda c: c["slug"])
    def test_preset_strict_equilibrium_residuals(self, case: dict) -> None:
        slug = case["slug"]
        res = solve_payload(case["input"])
        assert res["status"] == "ok", f"Expected ok status for {slug}"

        chk = res["checks"]
        sum_fx = abs(chk["sumFx"])
        sum_fy = abs(chk["sumFy"])
        sum_m_origin = abs(chk["sumM"])
        nodal_residual = chk["maxNodalResidual"]

        # Strict acceptance criteria: < 10^-6
        assert sum_fx < 1e-6, f"{slug}: |sum Fx| = {sum_fx} >= 1e-6"
        assert sum_fy < 1e-6, f"{slug}: |sum Fy| = {sum_fy} >= 1e-6"
        assert sum_m_origin < 1e-6, f"{slug}: |sum M_O| = {sum_m_origin} >= 1e-6"
        assert nodal_residual < 1e-6, f"{slug}: max nodal residual = {nodal_residual} >= 1e-6"
        assert chk["passed"] is True

        # Independent Moment Verification about geometric centroid
        nodes = case["input"]["nodes"]
        xc = sum(n["x"] for n in nodes) / len(nodes)
        yc = sum(n["y"] for n in nodes) / len(nodes)

        sum_m_centroid = 0.0
        for load in case["input"].get("loads", []):
            n = next(item for item in nodes if item["id"] == load["node"])
            dx = n["x"] - xc
            dy = n["y"] - yc
            sum_m_centroid += dx * load.get("Fy", 0.0) - dy * load.get("Fx", 0.0)

        for r in res["reactions"]:
            n = next(item for item in nodes if item["id"] == r["node"])
            dx = n["x"] - xc
            dy = n["y"] - yc
            sum_m_centroid += dx * r["Ry"] - dy * r["Rx"]

        assert abs(sum_m_centroid) < 1e-6, (
            f"{slug}: Centroid moment residual |sum M_C| = {abs(sum_m_centroid)} >= 1e-6"
        )

    @pytest.mark.parametrize("case", ERROR_CASES, ids=lambda c: c["slug"])
    def test_preset_error_cases_fail_gracefully(self, case: dict) -> None:
        slug = case["slug"]
        res = solve_payload(case["input"])
        assert res["status"] == "error", f"Expected error status for {slug}"
        assert len(res["errors"]) > 0

        expected_code = case["expect"].get("errorCode") or case["expect"].get("code")
        actual_codes = [e.get("code") for e in res["errors"]]
        assert expected_code in actual_codes, (
            f"{slug}: Expected error code '{expected_code}', got {actual_codes}"
        )
