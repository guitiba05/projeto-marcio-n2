"""Unidades: o cálculo é sempre em kN/m, a saída volta nas unidades de entrada."""

from __future__ import annotations

import math

import pytest

from app.core.errors import InputError
from app.core.solver import solve_payload
from app.core.units import (
    FORCE_TO_KN,
    LENGTH_TO_M,
    force_factor,
    format_number,
    length_factor,
)

TRIANGLE_KN_M = {
    "units": {"force": "kN", "length": "m"},
    "nodes": [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
        {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
    ],
    "members": [
        {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
        {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
        {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
    ],
    "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
}

# a mesma treliça, em newtons e milímetros
# (EA = 1e6 N equivale a 1000 kN, então a física é idêntica à do caso kN/m)
TRIANGLE_N_MM = {
    "units": {"force": "N", "length": "mm"},
    "nodes": [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "B", "x": 4000.0, "y": 0.0, "support": "roller"},
        {"id": "C", "x": 2000.0, "y": 3000.0, "support": "none"},
    ],
    "members": [
        {"id": "AB", "a": "A", "b": "B", "EA": 1000000.0},
        {"id": "AC", "a": "A", "b": "C", "EA": 1000000.0},
        {"id": "BC", "a": "B", "b": "C", "EA": 1000000.0},
    ],
    "loads": [{"node": "C", "Fx": 0.0, "Fy": -10000.0}],
}


def test_fatores_de_conversao() -> None:
    assert force_factor("kN") == 1.0
    assert force_factor("N") == pytest.approx(1e-3)
    assert force_factor("kgf") == pytest.approx(9.80665e-3)
    assert force_factor("tf") == pytest.approx(9.80665)
    assert length_factor("m") == 1.0
    assert length_factor("mm") == pytest.approx(1e-3)
    assert length_factor("cm") == pytest.approx(1e-2)
    assert length_factor("ft") == pytest.approx(0.3048)


def test_unidade_de_forca_desconhecida() -> None:
    with pytest.raises(InputError) as excinfo:
        force_factor("banana")
    assert excinfo.value.code == "bad_units"


def test_unidade_de_comprimento_desconhecida() -> None:
    with pytest.raises(InputError) as excinfo:
        length_factor("banana")
    assert excinfo.value.code == "bad_units"


def test_formatacao_nao_mostra_zero_negativo() -> None:
    assert format_number(-0.0001) == "0.000"
    assert format_number(3.14159) == "3.142"
    assert format_number(-6.0092) == "-6.009"


def test_mesma_treliça_em_n_mm_da_mesmo_resultado_fisico() -> None:
    """kN/m e N/mm têm de produzir os mesmos esforços, só que em outra unidade."""
    metric = solve_payload(TRIANGLE_KN_M)
    imperialish = solve_payload(TRIANGLE_N_MM)
    assert metric["status"] == "ok" and imperialish["status"] == "ok"

    # o contrato ganhou área e tensão; aqui interessa o par força/comprimento
    assert metric["units"]["force"] == "kN" and metric["units"]["length"] == "m"
    assert imperialish["units"]["force"] == "N" and imperialish["units"]["length"] == "mm"

    for member_metric, member_other in zip(metric["members"], imperialish["members"]):
        assert member_metric["id"] == member_other["id"]
        # 1 kN = 1000 N
        assert math.isclose(
            member_other["N"], member_metric["N"] * 1000.0, rel_tol=1e-9, abs_tol=1e-6
        ), f"barra {member_metric['id']}: {member_metric['N']} kN vs {member_other['N']} N"
        # 1 m = 1000 mm
        assert math.isclose(
            member_other["length"], member_metric["length"] * 1000.0, rel_tol=1e-9
        )
        assert member_metric["state"] == member_other["state"]

    for reaction_metric, reaction_other in zip(
        metric["reactions"], imperialish["reactions"]
    ):
        assert reaction_metric["node"] == reaction_other["node"]
        assert math.isclose(
            reaction_other["Ry"], reaction_metric["Ry"] * 1000.0, rel_tol=1e-9, abs_tol=1e-6
        )


def test_soma_de_momento_escala_com_forca_e_comprimento() -> None:
    metric = solve_payload(TRIANGLE_KN_M)
    other = solve_payload(TRIANGLE_N_MM)
    # kN·m -> N·mm é 1000 * 1000 = 1e6
    assert math.isclose(
        other["checks"]["sumM"], metric["checks"]["sumM"] * 1e6, abs_tol=1e-3
    )


def test_deslocamentos_escalam_com_o_comprimento() -> None:
    metric = solve_payload(TRIANGLE_KN_M)
    other = solve_payload(TRIANGLE_N_MM)
    by_node_metric = {d["node"]: d for d in metric["displacements"]}
    by_node_other = {d["node"]: d for d in other["displacements"]}
    for node_id, entry in by_node_metric.items():
        assert math.isclose(
            by_node_other[node_id]["uy"], entry["uy"] * 1000.0, abs_tol=1e-9
        )


def test_conversao_nao_quebra_o_equilibrio() -> None:
    for payload in (TRIANGLE_KN_M, TRIANGLE_N_MM):
        out = solve_payload(payload)
        assert out["checks"]["passed"] is True


def test_to_dict_faz_round_trip_nas_unidades_originais() -> None:
    from app.core.model import parse_truss

    truss = parse_truss(TRIANGLE_N_MM)
    rebuilt = truss.to_dict()
    assert rebuilt["units"]["force"] == "N" and rebuilt["units"]["length"] == "mm"
    assert rebuilt["nodes"][1]["x"] == pytest.approx(4000.0)
    assert rebuilt["loads"][0]["Fy"] == pytest.approx(-10000.0)
    # e o round-trip continua resolvendo a mesma coisa
    again = solve_payload(rebuilt)
    first = solve_payload(TRIANGLE_N_MM)
    assert [m["N"] for m in again["members"]] == [m["N"] for m in first["members"]]


def test_kip_e_pe_produzem_mesma_fisica() -> None:
    payload = {
        "units": {"force": "kip", "length": "ft"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 10.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 5.0, "y": 8.0, "support": "none"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
            {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
            {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
        ],
        "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
    }
    out = solve_payload(payload)
    assert out["status"] == "ok"
    # simetria: as duas diagonais têm o mesmo esforço, e as reações verticais
    # somam a carga aplicada
    forces = {m["id"]: m["N"] for m in out["members"]}
    assert math.isclose(forces["AC"], forces["BC"], abs_tol=1e-9)
    total_ry = sum(r["Ry"] for r in out["reactions"])
    assert math.isclose(total_ry, 10.0, abs_tol=1e-9)
    assert set(FORCE_TO_KN) >= {"kip", "lbf"}
    assert set(LENGTH_TO_M) >= {"ft", "in"}
