"""Tensão normal (σ = N/A) e dimensionamento inverso (área requerida).

Gabarito analítico do caso `01-triangulo` (A(0,0) pino, B(4,0) rolete, C(2,3),
Fy = −10 kN em C):

* N_AB = +10/3 kN (tração), N_AC = N_BC = −5√13/3 kN (compressão);
* com A = 100 mm² em todas as barras:
  σ_AB = (10/3)·1000/100 = **33,3333 MPa**;
* com σ_adm = 50 MPa:
  A_req(AB) = (10/3)·1000/50 = **66,6667 mm²**.

A base interna é N e mm² (1 MPa = 1 N/mm²); a força entra em kN e é convertida
aqui, de modo que a tensão sai diretamente em MPa.
"""

from __future__ import annotations

import pytest

from app.core.errors import InputError
from app.core.model import parse_truss
from app.core.solver import solve_payload, stress_payload
from app.core.stress import (
    analyze_stress,
    normal_stress_mpa,
    required_area_mm2,
    required_areas,
)

# gabaritos canônicos do caso 01-triangulo
N_AB = 10 / 3
N_AC = -5 * 13**0.5 / 3
SIGMA_AB = 33.33333333333333  # MPa com A = 100 mm²
AREA_REQ_AB = 66.66666666666667  # mm² com σ_adm = 50 MPa


def model(areas: dict[str, float] | None = None, units: dict | None = None) -> dict:
    """Caso 01-triangulo com área opcional por barra."""
    areas = areas or {}
    members = []
    for member_id, a, b in (("AB", "A", "B"), ("AC", "A", "C"), ("BC", "B", "C")):
        entry = {"id": member_id, "a": a, "b": b, "EA": 1.0}
        if member_id in areas:
            entry["area"] = areas[member_id]
        members.append(entry)
    return {
        "units": units or {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
        ],
        "members": members,
        "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
    }


# --------------------------------------------------------------- σ = N/A
def test_tensao_normal_gabarito() -> None:
    assert normal_stress_mpa(N_AB, 100.0) == pytest.approx(SIGMA_AB, abs=1e-9)


def test_tensao_normal_negativa_em_compressao() -> None:
    sigma = normal_stress_mpa(N_AC, 100.0)
    assert sigma < 0
    assert sigma == pytest.approx(N_AC * 1000 / 100.0, abs=1e-9)


def test_tensao_normal_area_nula_ou_negativa() -> None:
    for bad in (0.0, -5.0):
        with pytest.raises(InputError) as info:
            normal_stress_mpa(10.0, bad)
        assert info.value.code == "bad_area"


# ------------------------------------------------------- área requerida
def test_area_requerida_gabarito() -> None:
    assert required_area_mm2(N_AB, 50.0) == pytest.approx(AREA_REQ_AB, abs=1e-9)


def test_area_requerida_usa_modulo_do_esforco() -> None:
    """A área necessária depende de |N|, não do sinal."""
    assert required_area_mm2(N_AC, 50.0) == pytest.approx(
        required_area_mm2(-N_AC, 50.0), abs=1e-12
    )


def test_area_requerida_tensao_admissivel_invalida() -> None:
    for bad in (0.0, -10.0):
        with pytest.raises(InputError) as info:
            required_area_mm2(10.0, bad)
        assert info.value.code == "bad_allowable"


# ------------------------------------------------------- análise por barra
def test_analyze_stress_completo() -> None:
    truss = parse_truss(model({"AB": 100.0, "AC": 100.0, "BC": 100.0}))
    forces = {"AB": N_AB, "AC": N_AC, "BC": N_AC}
    payload = analyze_stress(truss, forces)

    assert payload["available"] is True
    assert payload["partial"] is False
    assert payload["missing"] == []
    assert len(payload["entries"]) == 3

    by_id = {entry["id"]: entry for entry in payload["entries"]}
    assert by_id["AB"]["sigma"] == pytest.approx(SIGMA_AB, abs=1e-9)
    assert by_id["AB"]["state"] == "tração"
    assert by_id["AC"]["sigma"] == pytest.approx(N_AC * 10.0, abs=1e-9)
    assert by_id["AC"]["state"] == "compressão"

    summary = payload["summary"]
    assert summary["members"] == 3
    assert summary["maxTension"]["id"] == "AB"
    assert summary["maxCompression"]["id"] in {"AC", "BC"}
    assert summary["critical"]["id"] in {"AC", "BC"}
    assert summary["maxAbsStress"] == pytest.approx(abs(N_AC) * 10.0, abs=1e-9)


def test_analyze_stress_parcial_sem_area() -> None:
    """Barra sem área: não calcula σ, mas não invalida as demais."""
    truss = parse_truss(model({"AB": 100.0}))
    payload = analyze_stress(truss, {"AB": N_AB, "AC": N_AC, "BC": N_AC})

    assert payload["available"] is False
    assert payload["partial"] is True
    assert sorted(payload["missing"]) == ["AC", "BC"]
    assert [entry["id"] for entry in payload["entries"]] == ["AB"]


def test_analyze_stress_sem_area_nenhuma() -> None:
    truss = parse_truss(model())
    payload = analyze_stress(truss, {"AB": N_AB, "AC": N_AC, "BC": N_AC})

    assert payload["available"] is False
    assert payload["partial"] is False
    assert payload["entries"] == []
    assert payload["summary"]["maxAbsStress"] == 0.0
    assert payload["summary"]["critical"] is None


# ------------------------------------------------- área requerida por barra
def test_required_areas_tensao_admissivel_unica() -> None:
    truss = parse_truss(model())
    payload = required_areas(truss, {"AB": N_AB, "AC": N_AC, "BC": N_AC}, 50.0)

    by_id = {entry["id"]: entry for entry in payload["entries"]}
    assert by_id["AB"]["requiredArea"] == pytest.approx(AREA_REQ_AB, abs=1e-9)
    assert by_id["AC"]["requiredArea"] == pytest.approx(
        abs(N_AC) * 1000 / 50.0, abs=1e-9
    )
    assert payload["summary"]["governing"]["id"] in {"AC", "BC"}
    assert payload["summary"]["allSufficient"] is None  # sem área atual


def test_required_areas_tracao_e_compressao_distintas() -> None:
    truss = parse_truss(model())
    payload = required_areas(
        truss,
        {"AB": N_AB, "AC": N_AC, "BC": N_AC},
        {"tension": 50.0, "compression": 80.0},
    )
    by_id = {entry["id"]: entry for entry in payload["entries"]}

    assert payload["allowable"] == {"tension": 50.0, "compression": 80.0}
    assert by_id["AB"]["allowable"] == 50.0
    assert by_id["AC"]["allowable"] == 80.0
    assert by_id["AB"]["requiredArea"] == pytest.approx(AREA_REQ_AB, abs=1e-9)
    assert by_id["AC"]["requiredArea"] == pytest.approx(
        abs(N_AC) * 1000 / 80.0, abs=1e-9
    )


def test_required_areas_verifica_area_atual() -> None:
    truss = parse_truss(model({"AB": 100.0, "AC": 100.0, "BC": 100.0}))
    payload = required_areas(truss, {"AB": N_AB, "AC": N_AC, "BC": N_AC}, 50.0)

    by_id = {entry["id"]: entry for entry in payload["entries"]}
    assert by_id["AB"]["ok"] is True          # 100 mm² ≥ 66,67 mm²
    assert by_id["AC"]["ok"] is False         # 100 mm² < 120,19 mm²
    assert by_id["AC"]["currentArea"] == pytest.approx(100.0)
    assert by_id["AB"]["utilisation"] == pytest.approx(
        AREA_REQ_AB / 100.0, abs=1e-9
    )
    assert payload["summary"]["allSufficient"] is False


# ------------------------------------------------------- payload da API/core
def test_stress_payload_modo_tensao() -> None:
    payload = stress_payload(
        model({"AB": 100.0, "AC": 100.0, "BC": 100.0}), mode="stress"
    )
    assert payload["status"] == "ok"
    assert payload["mode"] == "stress"
    assert payload["errors"] == []
    assert payload["units"]["area"] == "mm²"
    assert payload["units"]["stress"] == "MPa"

    by_id = {entry["id"]: entry for entry in payload["stress"]["entries"]}
    assert by_id["AB"]["sigma"] == pytest.approx(SIGMA_AB, abs=1e-9)
    assert by_id["AB"]["area"] == pytest.approx(100.0)


def test_stress_payload_modo_area() -> None:
    payload = stress_payload(model(), mode="area", allowable=50.0)
    assert payload["status"] == "ok"
    assert payload["mode"] == "area"

    by_id = {entry["id"]: entry for entry in payload["stress"]["entries"]}
    assert by_id["AB"]["requiredArea"] == pytest.approx(AREA_REQ_AB, abs=1e-9)


def test_stress_payload_modo_area_sem_allowable() -> None:
    payload = stress_payload(model(), mode="area", allowable=None)
    assert payload["status"] == "error"
    assert payload["errors"][0]["code"] == "bad_allowable"


def test_stress_payload_area_invalida_no_modelo() -> None:
    bad = model({"AB": -100.0})
    payload = stress_payload(bad, mode="stress")
    assert payload["status"] == "error"
    assert payload["errors"][0]["code"] == "invalid_input"


# ------------------------------------------------------------- unidades
def test_stress_payload_com_area_em_cm2() -> None:
    """1 cm² = 100 mm², então 1 cm² dá a mesma σ que 100 mm²."""
    payload = stress_payload(
        model(
            {"AB": 1.0, "AC": 1.0, "BC": 1.0},
            units={"force": "kN", "length": "m", "area": "cm²", "stress": "MPa"},
        ),
        mode="stress",
    )
    by_id = {entry["id"]: entry for entry in payload["stress"]["entries"]}
    assert payload["units"]["area"] == "cm²"
    assert by_id["AB"]["area"] == pytest.approx(1.0)
    assert by_id["AB"]["sigma"] == pytest.approx(SIGMA_AB, abs=1e-9)


def test_stress_payload_com_tensao_em_ksi() -> None:
    payload = stress_payload(
        model(
            {"AB": 100.0, "AC": 100.0, "BC": 100.0},
            units={"force": "kN", "length": "m", "area": "mm²", "stress": "ksi"},
        ),
        mode="stress",
    )
    by_id = {entry["id"]: entry for entry in payload["stress"]["entries"]}
    assert payload["units"]["stress"] == "ksi"
    assert by_id["AB"]["sigma"] == pytest.approx(SIGMA_AB / 6.894757293168361, abs=1e-9)


def test_area_requerida_em_cm2() -> None:
    payload = stress_payload(
        model(units={"force": "kN", "length": "m", "area": "cm²"}),
        mode="area",
        allowable=50.0,
    )
    by_id = {entry["id"]: entry for entry in payload["stress"]["entries"]}
    # 66,6667 mm² = 0,666667 cm²
    assert by_id["AB"]["requiredArea"] == pytest.approx(AREA_REQ_AB / 100.0, abs=1e-9)


# ------------------------------------------------- tensão dentro de /api/solve
def test_solve_inclui_bloco_de_tensao() -> None:
    solution = solve_payload(model({"AB": 100.0, "AC": 100.0, "BC": 100.0}))
    assert solution["status"] == "ok"
    assert "stress" in solution
    assert solution["units"]["area"] == "mm²"
    assert solution["units"]["stress"] == "MPa"

    stress = solution["stress"]
    assert stress["available"] is True
    by_id = {entry["id"]: entry for entry in stress["entries"]}
    assert by_id["AB"]["sigma"] == pytest.approx(SIGMA_AB, abs=1e-9)

    # a área também aparece na tabela de barras
    members = {member["id"]: member for member in solution["members"]}
    assert members["AB"]["area"] == pytest.approx(100.0)


def test_solve_sem_area_nao_calcula_tensao() -> None:
    solution = solve_payload(model())
    assert solution["status"] == "ok"
    assert solution["stress"]["available"] is False
    assert solution["stress"]["entries"] == []
    assert sorted(solution["stress"]["missing"]) == ["AB", "AC", "BC"]
