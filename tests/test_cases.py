"""Bateria de aceitação: os 12 casos de `tests/cases/` viram testes.

Cada caso válido é verificado em seis frentes independentes:

1. estaticidade (`b + r` vs `2n`);
2. esforços normais contra o gabarito gravado;
3. reações de apoio contra o gabarito gravado;
4. equilíbrio global e nodal (`ΣF = 0`, `ΣM = 0`);
5. conferência pelo **método dos nós** (algoritmo independente do da rigidez);
6. lista de barras de força zero.

Os casos inválidos verificam que o programa **recusa** com o código de erro certo.
"""

from __future__ import annotations

import math

import pytest
from conftest import ERROR_CASES, OK_CASES

from app.core.joints import method_of_joints
from app.core.model import parse_truss
from app.core.solver import solve_payload


def case_id(case: dict) -> str:
    return case["slug"]


@pytest.mark.parametrize("case", OK_CASES, ids=case_id)
def test_caso_valido(case: dict) -> None:
    out = solve_payload(case["input"])
    expect = case["expect"]

    assert out["status"] == "ok", out.get("errors")
    assert out["errors"] == []


@pytest.mark.parametrize("case", OK_CASES, ids=case_id)
def test_estaticidade(case: dict) -> None:
    out = solve_payload(case["input"])
    expect = case["expect"]["determinacy"]
    got = out["determinacy"]
    assert got["n"] == expect["n"]
    assert got["b"] == expect["b"]
    assert got["r"] == expect["r"]
    assert got["degree"] == expect["degree"]
    assert got["label"] == expect["label"]
    # a contagem precisa fechar com a definição
    assert got["degree"] == got["b"] + got["r"] - 2 * got["n"]


@pytest.mark.parametrize("case", OK_CASES, ids=case_id)
def test_esforcos_normais(case: dict) -> None:
    out = solve_payload(case["input"])
    tol = case["expect"]["tolerance"]
    for member_id, expected in case["expect"]["members"].items():
        got = next(m["N"] for m in out["members"] if m["id"] == member_id)
        assert math.isclose(got, expected, abs_tol=tol), (
            f"barra {member_id}: obtido {got:.6f}, esperado {expected:.6f}"
        )


@pytest.mark.parametrize("case", OK_CASES, ids=case_id)
def test_reacoes(case: dict) -> None:
    out = solve_payload(case["input"])
    tol = case["expect"]["tolerance"]
    for node_id, components in case["expect"]["reactions"].items():
        entry = next(r for r in out["reactions"] if r["node"] == node_id)
        for component, expected in components.items():
            assert math.isclose(entry[component], expected, abs_tol=tol), (
                f"reação {node_id}.{component}: obtido {entry[component]:.6f}, "
                f"esperado {expected:.6f}"
            )


@pytest.mark.parametrize("case", OK_CASES, ids=case_id)
def test_equilibrio(case: dict) -> None:
    out = solve_payload(case["input"])
    checks = out["checks"]
    assert checks["passed"], (
        f"equilíbrio não fechou: ΣFx={checks['sumFx']:.2e} "
        f"ΣFy={checks['sumFy']:.2e} ΣM={checks['sumM']:.2e} "
        f"resíduo nodal={checks['maxNodalResidual']:.2e} "
        f"(nó {checks['worstNode']})"
    )
    assert abs(checks["sumFx"]) < 1e-9
    assert abs(checks["sumFy"]) < 1e-9
    assert abs(checks["sumM"]) < 1e-8
    assert checks["maxNodalResidual"] < 1e-9


@pytest.mark.parametrize("case", OK_CASES, ids=case_id)
def test_metodo_dos_nos(case: dict) -> None:
    """O método da rigidez e o método dos nós têm de dar o mesmo resultado."""
    out = solve_payload(case["input"])
    cross = out["crossCheck"]

    if out["determinacy"]["degree"] > 0:
        # hiperestática: o método dos nós não se aplica (sistema não quadrado)
        assert cross["available"] is False
        assert "isostática" in cross["reason"]
        return

    assert cross["available"] is True, cross["reason"]
    assert cross["passed"] is True, (
        f"divergência de {cross['maxDifference']:.2e} entre rigidez e método dos nós"
    )
    assert cross["maxDifference"] < 1e-9

    # confere também contra a implementação de referência, direto
    truss = parse_truss(case["input"])
    reference = method_of_joints(truss)
    got = {m["id"]: m["N"] for m in out["members"]}
    for member_id, expected in reference.member_forces.items():
        assert math.isclose(got[member_id], expected, abs_tol=1e-9)


@pytest.mark.parametrize("case", OK_CASES, ids=case_id)
def test_barras_de_forca_zero(case: dict) -> None:
    out = solve_payload(case["input"])
    got = sorted(entry["member"] for entry in out["zero_force"])
    assert got == case["expect"]["zeroForce"]

    # consistência: toda barra listada tem N nulo de fato
    forces = {m["id"]: m["N"] for m in out["members"]}
    for member_id in got:
        assert abs(forces[member_id]) < 1e-9


@pytest.mark.parametrize("case", ERROR_CASES, ids=case_id)
def test_caso_de_erro(case: dict) -> None:
    out = solve_payload(case["input"])
    expect = case["expect"]

    assert out["status"] == "error"
    codes = [error["code"] for error in out["errors"]]
    assert expect["errorCode"] in codes, f"códigos obtidos: {codes}"

    # não devolve resultado parcial que possa ser confundido com solução válida
    assert out["members"] == []
    assert out["reactions"] == []
    assert out["checks"] is None


@pytest.mark.parametrize("case", ERROR_CASES, ids=case_id)
def test_mensagem_de_erro_e_util(case: dict) -> None:
    out = solve_payload(case["input"])
    message = out["errors"][0]["message"]
    assert len(message) > 40, "a mensagem de erro precisa explicar o problema"
    assert any(char in message for char in "áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ") or " " in message


def test_bateria_tem_doze_casos() -> None:
    from conftest import CASES

    assert len(CASES) == 12, "o plano prevê 12 casos (a banca usa 8)"
    assert len(OK_CASES) == 10
    assert len(ERROR_CASES) == 2
