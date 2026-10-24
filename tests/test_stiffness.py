"""Propriedades do método matricial da rigidez que precisam valer sempre."""

from __future__ import annotations

import copy
import math

import numpy as np
import pytest
from conftest import OK_CASES

from app.core.errors import DeterminacyError, MechanismError
from app.core.model import parse_truss
from app.core.stiffness import analyze, assemble, member_stiffness
from app.core.solver import solve_payload

TRIANGLE = {
    "units": {"force": "kN", "length": "m"},
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
    "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
}

SQUARE_HYPER = {
    "units": {"force": "kN", "length": "m"},
    "nodes": [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
        {"id": "C", "x": 4.0, "y": 4.0, "support": "none"},
        {"id": "D", "x": 0.0, "y": 4.0, "support": "none"},
    ],
    "members": [
        {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
        {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
        {"id": "CD", "a": "C", "b": "D", "EA": 1.0},
        {"id": "DA", "a": "D", "b": "A", "EA": 1.0},
        {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
        {"id": "BD", "a": "B", "b": "D", "EA": 1.0},
    ],
    "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
}


def with_ea(data: dict, ea: float) -> dict:
    data = copy.deepcopy(data)
    for member in data["members"]:
        member["EA"] = ea
    return data


def test_matriz_da_barra_e_simetrica_e_singular() -> None:
    """A matriz 4x4 da barra é simétrica e tem posto 1 (só rigidez axial)."""
    k = member_stiffness(EA=100.0, length=2.5, c=0.6, s=0.8)
    assert np.allclose(k, k.T)
    assert np.linalg.matrix_rank(k, tol=1e-9) == 1
    # modo de corpo rígido: translação pura não gera força
    translation = np.array([1.0, 0.0, 1.0, 0.0])
    assert np.allclose(k @ translation, 0.0, atol=1e-9)
    # alongamento axial puro: o vetor [-c,-s,c,s] desloca os nós no eixo da barra,
    # gerando força (EA/L)·2 em cada extremidade, na direção do eixo
    elongation = np.array([-0.6, -0.8, 0.6, 0.8])
    force = k @ elongation
    expected = 100.0 / 2.5 * 2.0
    assert np.allclose(force[:2], expected * np.array([-0.6, -0.8]), atol=1e-9)
    assert np.allclose(force[2:], expected * np.array([0.6, 0.8]), atol=1e-9)


@pytest.mark.parametrize("case", OK_CASES, ids=lambda case: case["slug"])
def test_matriz_global_e_simetrica(case: dict) -> None:
    truss = parse_truss(case["input"])
    K, F = assemble(truss)
    assert K.shape == (truss.n_dof, truss.n_dof)
    assert np.allclose(K, K.T)
    assert F.shape == (truss.n_dof,)
    # soma das forças nodais aplicadas bate com o vetor F
    total = sum(load.Fx for load in truss.loads)
    assert math.isclose(float(F[0::2].sum()), total, abs_tol=1e-12)


@pytest.mark.parametrize("case", OK_CASES, ids=lambda case: case["slug"])
def test_deslocamentos_nulos_nos_apoios(case: dict) -> None:
    out = solve_payload(case["input"])
    displacements = {d["node"]: (d["ux"], d["uy"]) for d in out["displacements"]}
    truss = parse_truss(case["input"])
    for node in truss.nodes:
        ux, uy = displacements[node.id]
        if "ux" in node.restraints:
            assert abs(ux) < 1e-12, f"nó {node.id}: ux deveria ser nulo"
        if "uy" in node.restraints:
            assert abs(uy) < 1e-12, f"nó {node.id}: uy deveria ser nulo"


@pytest.mark.parametrize("case", OK_CASES, ids=lambda case: case["slug"])
def test_reacoes_batem_com_K_u_menos_F(case: dict) -> None:
    """R = K·u − F nos graus de liberdade restringidos."""
    truss = parse_truss(case["input"])
    result = analyze(truss)
    residual = result.K @ result.u - result.F
    for dof in result.restrained_dofs:
        assert math.isclose(
            result.reaction_values[dof], float(residual[dof]), abs_tol=1e-9
        )


def test_isostatica_nao_depende_de_EA() -> None:
    """Em treliça isostática os esforços normais independem da rigidez das barras."""
    base = solve_payload(TRIANGLE)
    reference = {m["id"]: m["N"] for m in base["members"]}

    for ea in (1.0, 1e-3, 1e3, 2.5e6):
        out = solve_payload(with_ea(TRIANGLE, ea))
        assert out["status"] == "ok"
        for member in out["members"]:
            assert math.isclose(member["N"], reference[member["id"]], abs_tol=1e-6), (
                f"EA={ea}: barra {member['id']} mudou de {reference[member['id']]} "
                f"para {member['N']}"
            )


def test_hiperestatica_depende_de_EA() -> None:
    """Em treliça hiperestática os esforços dependem de EA — comportamento esperado."""
    first = solve_payload(SQUARE_HYPER)
    assert first["status"] == "ok"
    assert first["determinacy"]["degree"] == 1

    # com EA diferente na diagonal AC, o esforço nela muda
    modified = copy.deepcopy(SQUARE_HYPER)
    for member in modified["members"]:
        if member["id"] == "AC":
            member["EA"] = 50.0
    second = solve_payload(modified)

    n_first = next(m["N"] for m in first["members"] if m["id"] == "AC")
    n_second = next(m["N"] for m in second["members"] if m["id"] == "AC")
    assert not math.isclose(n_first, n_second, abs_tol=1e-3)
    assert any("hiperestática" in warning for warning in first["warnings"])


def test_hiperestatica_avisa_na_saida() -> None:
    out = solve_payload(SQUARE_HYPER)
    assert any("EA" in warning for warning in out["warnings"])
    assert out["crossCheck"]["available"] is False


def test_hipostatica_levanta_determinacy_error() -> None:
    data = copy.deepcopy(TRIANGLE)
    data["nodes"][1]["support"] = "none"
    truss = parse_truss(data)
    with pytest.raises(DeterminacyError):
        analyze(truss)


def test_mecanismo_levanta_mechanism_error() -> None:
    data = {
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "C", "x": 4.0, "y": 0.0, "support": "pin"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
            {"id": "CB", "a": "C", "b": "B", "EA": 1.0},
        ],
        "loads": [{"node": "B", "Fx": 0.0, "Fy": -5.0}],
    }
    truss = parse_truss(data)
    # a contagem dá g = 0...
    from app.core.determinacy import analyze_determinacy

    assert analyze_determinacy(truss).degree == 0
    # ...mas o solver detecta o mecanismo
    with pytest.raises(MechanismError) as excinfo:
        analyze(truss)
    assert "mecanismo" in str(excinfo.value).lower()
    assert "B.uy" in str(excinfo.value)


def test_nenhum_valor_absurdo_em_caso_singular() -> None:
    """O caso de mecanismo não pode devolver forças gigantes."""
    data = {
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "C", "x": 4.0, "y": 0.0, "support": "pin"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
            {"id": "CB", "a": "C", "b": "B", "EA": 1.0},
        ],
        "loads": [{"node": "B", "Fx": 0.0, "Fy": -5.0}],
    }
    out = solve_payload(data)
    assert out["status"] == "error"
    assert out["members"] == []


def test_tração_e_compressão_tem_sinal_correto() -> None:
    out = solve_payload(TRIANGLE)
    states = {m["id"]: (m["N"], m["state"]) for m in out["members"]}
    assert states["AB"][0] > 0 and states["AB"][1] == "tração"
    assert states["AC"][0] < 0 and states["AC"][1] == "compressão"
    # a barra horizontal inferior está tracionada e as diagonais comprimidas:
    # coerente com a carga vertical para baixo no vértice
