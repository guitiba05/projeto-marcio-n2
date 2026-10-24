"""Validação de entrada: cada erro previsível tem de virar mensagem, não exceção solta."""

from __future__ import annotations

import pytest

from app.core.errors import InputError
from app.core.model import parse_truss
from app.core.solver import solve_payload

BASE = {
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


def payload(**overrides) -> dict:
    data = {key: value for key, value in BASE.items()}
    data.update(overrides)
    return data


def error_code(data: dict) -> str:
    out = solve_payload(data)
    assert out["status"] == "error", "esperava erro de entrada"
    return out["errors"][0]["code"]


def test_entrada_base_e_valida() -> None:
    assert solve_payload(payload())["status"] == "ok"


def test_sem_nos() -> None:
    assert error_code(payload(nodes=[])) == "no_nodes"


def test_sem_barras() -> None:
    assert error_code(payload(members=[])) == "no_members"


def test_nenhum_apoio() -> None:
    nodes = [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "none"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "none"},
        {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
    ]
    assert error_code(payload(nodes=nodes)) == "no_supports"


def test_no_duplicado() -> None:
    nodes = BASE["nodes"] + [{"id": "A", "x": 9.0, "y": 9.0, "support": "none"}]
    assert error_code(payload(nodes=nodes)) == "invalid_input"


def test_barra_com_no_inexistente() -> None:
    members = BASE["members"] + [{"id": "XZ", "a": "A", "b": "Z", "EA": 1.0}]
    assert error_code(payload(members=members)) == "invalid_input"


def test_barra_duplicada() -> None:
    members = BASE["members"] + [{"id": "BA", "a": "B", "b": "A", "EA": 1.0}]
    assert error_code(payload(members=members)) == "invalid_input"


def test_barra_com_mesmo_no() -> None:
    members = BASE["members"] + [{"id": "AA", "a": "A", "b": "A", "EA": 1.0}]
    assert error_code(payload(members=members)) == "invalid_input"


def test_barra_de_comprimento_zero() -> None:
    """Dois nós com coordenadas iguais geram barra de comprimento nulo."""
    nodes = BASE["nodes"] + [{"id": "D", "x": 0.0, "y": 0.0, "support": "none"}]
    members = BASE["members"] + [{"id": "AD", "a": "A", "b": "D", "EA": 1.0}]
    out = solve_payload(payload(nodes=nodes, members=members))
    assert out["status"] == "error"
    assert out["errors"][0]["code"] in {"zero_length_member", "invalid_input"}


def test_ea_nao_positivo() -> None:
    members = [dict(member) for member in BASE["members"]]
    members[0]["EA"] = 0.0
    assert error_code(payload(members=members)) == "invalid_input"


def test_carga_em_no_inexistente() -> None:
    loads = [{"node": "Z", "Fx": 1.0, "Fy": 0.0}]
    assert error_code(payload(loads=loads)) == "unknown_node"


def test_coordenada_nao_numerica() -> None:
    nodes = [dict(node) for node in BASE["nodes"]]
    nodes[0]["x"] = "abc"
    assert error_code(payload(nodes=nodes)) == "invalid_input"


def test_coordenada_infinita() -> None:
    nodes = [dict(node) for node in BASE["nodes"]]
    nodes[0]["x"] = float("inf")
    assert error_code(payload(nodes=nodes)) == "invalid_input"


def test_apoio_desconhecido() -> None:
    nodes = [dict(node) for node in BASE["nodes"]]
    nodes[0]["support"] = "engaste_perfeito"
    assert error_code(payload(nodes=nodes)) == "invalid_input"


def test_unidade_desconhecida() -> None:
    assert error_code(payload(units={"force": "banana", "length": "m"})) == "bad_units"


def test_apelidos_de_apoio_em_portugues() -> None:
    nodes = [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "articulacao"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "roleto"},
        {"id": "C", "x": 2.0, "y": 3.0, "support": "livre"},
    ]
    truss = parse_truss(payload(nodes=nodes))
    assert truss.nodes[0].support == "pin"
    assert truss.nodes[1].support == "roller"
    assert truss.nodes[2].support == "none"


def test_ids_gerados_quando_omitidos() -> None:
    nodes = [
        {"x": 0.0, "y": 0.0, "support": "pin"},
        {"x": 4.0, "y": 0.0, "support": "roller"},
        {"x": 2.0, "y": 3.0},
    ]
    members = [
        {"a": "N1", "b": "N2"},
        {"a": "N1", "b": "N3"},
        {"a": "N2", "b": "N3"},
    ]
    truss = parse_truss({"nodes": nodes, "members": members, "loads": []})
    assert truss.node_ids == ("N1", "N2", "N3")
    assert [member.id for member in truss.members] == ["N1N2", "N1N3", "N2N3"]


def test_no_isolado_gera_aviso() -> None:
    """Nó isolado vira aviso na leitura — e, claro, deixa a treliça hipostática."""
    nodes = BASE["nodes"] + [{"id": "D", "x": 10.0, "y": 10.0, "support": "none"}]
    truss = parse_truss(payload(nodes=nodes))
    assert any("isolado" in warning for warning in truss.warnings)

    # com um nó sem barras a contagem cai para g < 0 e o cálculo é recusado
    out = solve_payload(payload(nodes=nodes))
    assert out["status"] == "error"
    assert out["errors"][0]["code"] == "hypostatic"


def test_subestruturas_desconexas_geram_aviso() -> None:
    """Duas treliças estáveis separadas: resolve, mas avisa da descontinuidade."""
    nodes = [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
        {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
        {"id": "D", "x": 10.0, "y": 0.0, "support": "pin"},
        {"id": "E", "x": 14.0, "y": 0.0, "support": "roller"},
        {"id": "F", "x": 12.0, "y": 3.0, "support": "none"},
    ]
    members = [
        {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
        {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
        {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
        {"id": "DE", "a": "D", "b": "E", "EA": 1.0},
        {"id": "DF", "a": "D", "b": "F", "EA": 1.0},
        {"id": "EF", "a": "E", "b": "F", "EA": 1.0},
    ]
    loads = [{"node": "C", "Fx": 0.0, "Fy": -10.0}]
    out = solve_payload(payload(nodes=nodes, members=members, loads=loads))
    assert out["status"] == "ok", out["errors"]
    assert any("desconexas" in warning for warning in out["warnings"])


def test_parse_truss_levanta_input_error() -> None:
    with pytest.raises(InputError):
        parse_truss({"nodes": [], "members": []})


def test_entrada_nao_e_objeto() -> None:
    out = solve_payload(["nao", "e", "objeto"])  # type: ignore[arg-type]
    assert out["status"] == "error"
    assert out["errors"][0]["code"] == "bad_payload"
