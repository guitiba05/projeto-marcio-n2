"""Regras de barras de força zero (R1, R2, R3) e as condições em que NÃO valem."""

from __future__ import annotations

from app.core.model import parse_truss
from app.core.solver import solve_payload
from app.core.zero_force import find_zero_force_rules, summarize_zero_force


def build(nodes: list[dict], members: list[dict], loads: list[dict] | None = None):
    return parse_truss(
        {
            "units": {"force": "kN", "length": "m"},
            "nodes": nodes,
            "members": members,
            "loads": loads or [],
        }
    )


def test_r1_no_com_uma_unica_barra() -> None:
    """R1: nó com uma só barra, sem carga e sem vínculo."""
    truss = build(
        nodes=[
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "D", "x": 2.0, "y": 3.0, "support": "none"},
        ],
        members=[
            {"id": "AB", "a": "A", "b": "B"},
            {"id": "AD", "a": "A", "b": "D"},
        ],
    )
    rules = find_zero_force_rules(truss)
    assert "AD" in rules
    assert rules["AD"].startswith("R1")


def test_r2_no_com_duas_barras_nao_colineares() -> None:
    """R2: nó com duas barras não colineares, sem carga e sem vínculo."""
    truss = build(
        nodes=[
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 4.0, "y": 3.0, "support": "none"},
            {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
        ],
        members=[
            {"id": "AB", "a": "A", "b": "B"},
            {"id": "BC", "a": "B", "b": "C"},
            {"id": "CD", "a": "C", "b": "D"},
            {"id": "DA", "a": "D", "b": "A"},
            {"id": "AC", "a": "A", "b": "C"},
        ],
        loads=[{"node": "C", "Fx": 6.0, "Fy": -10.0}],
    )
    rules = find_zero_force_rules(truss)
    assert rules["CD"].startswith("R2")
    assert rules["DA"].startswith("R2")


def test_r3_no_com_tres_barras_duas_colineares() -> None:
    """R3: nó com três barras, sendo duas colineares — a terceira é de força zero."""
    truss = build(
        nodes=[
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "T", "x": 2.0, "y": 3.0, "support": "none"},
        ],
        members=[
            {"id": "AC", "a": "A", "b": "C"},
            {"id": "CB", "a": "C", "b": "B"},
            {"id": "CT", "a": "C", "b": "T"},
            {"id": "AT", "a": "A", "b": "T"},
            {"id": "BT", "a": "B", "b": "T"},
        ],
        loads=[{"node": "T", "Fx": 0.0, "Fy": -10.0}],
    )
    rules = find_zero_force_rules(truss)
    assert "CT" in rules
    assert rules["CT"].startswith("R3")
    # as barras do banzo inferior NÃO são de força zero
    assert "AC" not in rules
    assert "CB" not in rules


def test_regra_nao_vale_em_no_carregado() -> None:
    """Com carga aplicada no nó, a regra geométrica não se aplica."""
    base_nodes = [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
        {"id": "C", "x": 4.0, "y": 3.0, "support": "none"},
        {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
    ]
    members = [
        {"id": "AB", "a": "A", "b": "B"},
        {"id": "BC", "a": "B", "b": "C"},
        {"id": "CD", "a": "C", "b": "D"},
        {"id": "DA", "a": "D", "b": "A"},
        {"id": "AC", "a": "A", "b": "C"},
    ]

    without_load = find_zero_force_rules(build(base_nodes, members, []))
    assert "CD" in without_load and "DA" in without_load

    with_load = find_zero_force_rules(
        build(base_nodes, members, [{"node": "D", "Fx": 0.0, "Fy": -5.0}])
    )
    assert "CD" not in with_load
    assert "DA" not in with_load


def test_regra_nao_vale_em_no_com_vinculo() -> None:
    """Nó com apoio tem reação, então a regra de força zero não se aplica a ele.

    Aqui todos os nós livres estão carregados e todos os outros têm vínculo,
    de modo que nenhuma regra geométrica pode ser aplicada.
    """
    nodes = [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
        {"id": "C", "x": 4.0, "y": 3.0, "support": "roller"},
        {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
    ]
    members = [
        {"id": "AB", "a": "A", "b": "B"},
        {"id": "BC", "a": "B", "b": "C"},
        {"id": "CD", "a": "C", "b": "D"},
        {"id": "DA", "a": "D", "b": "A"},
        {"id": "AC", "a": "A", "b": "C"},
    ]
    loads = [{"node": "D", "Fx": 0.0, "Fy": -5.0}]
    rules = find_zero_force_rules(build(nodes, members, loads))

    # C tem vínculo e D está carregado: nenhuma regra pode disparar
    assert rules == {}
    assert "BC" not in rules
    assert "CD" not in rules


def test_resultado_numerico_confirma_a_regra() -> None:
    """A regra é geométrica; o solver confirma numericamente |N| ≈ 0."""
    payload = {
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 4.0, "y": 3.0, "support": "none"},
            {"id": "D", "x": 0.0, "y": 3.0, "support": "none"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B"},
            {"id": "BC", "a": "B", "b": "C"},
            {"id": "CD", "a": "C", "b": "D"},
            {"id": "DA", "a": "D", "b": "A"},
            {"id": "AC", "a": "A", "b": "C"},
        ],
        "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
    }
    out = solve_payload(payload)
    entries = {entry["member"]: entry for entry in out["zero_force"]}
    assert entries["CD"]["confirmed"] is True
    assert entries["DA"]["confirmed"] is True
    assert entries["CD"]["rule"].startswith("R2")
    assert abs(entries["CD"]["N"]) < 1e-9


def test_caso_sem_carga_todas_as_barras_sao_de_forca_zero() -> None:
    payload = {
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B"},
            {"id": "AC", "a": "A", "b": "C"},
            {"id": "BC", "a": "B", "b": "C"},
        ],
        "loads": [],
    }
    out = solve_payload(payload)
    assert sorted(entry["member"] for entry in out["zero_force"]) == ["AB", "AC", "BC"]
    assert out["summary"]["zero"] == 3
    assert out["summary"]["tension"] == 0
    assert out["summary"]["compression"] == 0


def test_summarize_marca_apenas_regra_quando_nao_confirma() -> None:
    """Uma barra que a regra aponta mas o solver não zera aparece com confirmed=False."""
    truss = build(
        nodes=[
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "T", "x": 2.0, "y": 3.0, "support": "none"},
        ],
        members=[
            {"id": "AC", "a": "A", "b": "C"},
            {"id": "CB", "a": "C", "b": "B"},
            {"id": "CT", "a": "C", "b": "T"},
            {"id": "AT", "a": "A", "b": "T"},
            {"id": "BT", "a": "B", "b": "T"},
        ],
        loads=[{"node": "T", "Fx": 0.0, "Fy": -10.0}],
    )
    # forçamos um valor não nulo para a barra que a regra aponta
    entries = summarize_zero_force(truss, {"AC": 3.0, "CB": 3.0, "CT": 0.0, "AT": -6.0, "BT": -6.0})
    by_member = {entry["member"]: entry for entry in entries}
    assert by_member["CT"]["confirmed"] is True
    assert by_member["CT"]["numeric"] is True

    entries_fake = summarize_zero_force(
        truss, {"AC": 3.0, "CB": 3.0, "CT": 1.5, "AT": -6.0, "BT": -6.0}
    )
    by_member_fake = {entry["member"]: entry for entry in entries_fake}
    assert by_member_fake["CT"]["confirmed"] is False
    assert by_member_fake["CT"]["rule"].startswith("R3")
