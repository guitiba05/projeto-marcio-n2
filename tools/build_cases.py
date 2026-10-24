"""Gera/valida a bateria de casos. Roda o solver e o método dos nós,
cruza os dois, e emite os JSON com gabarito em tests/cases/."""

import json
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.getcwd())

from app.core.joints import method_of_joints
from app.core.model import parse_truss
from app.core.solver import solve_payload
from app.core.errors import InputError

CASES = []


def case(**kw):
    CASES.append(kw)


# ---------------------------------------------------------------- 1
case(
    slug="01-triangulo",
    name="Triângulo isostático (caso canônico)",
    description=(
        "Treliça triangular com pino em A, roleto em B e carga vertical em C. "
        "É o caso de referência com solução analítica exata: Ay = By = 5 kN, "
        "N_AB = 10/3 kN (tração) e N_AC = N_BC = -5√13/3 kN (compressão)."
    ),
    exercises=["equilíbrio externo", "método dos nós", "tração/compressão"],
    input={
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
    },
    exact={
        "members": {"AB": 10.0 / 3.0, "AC": -5.0 * math.sqrt(13) / 3.0, "BC": -5.0 * math.sqrt(13) / 3.0},
        "reactions": {"A": {"Rx": 0.0, "Ry": 5.0}, "B": {"Ry": 5.0}},
    },
)

# ---------------------------------------------------------------- 2
case(
    slug="02-telhado-pratt",
    name="Treliça de telhado (Pratt) com carga distribuída convertida em nodal",
    description=(
        "Telhado de duas águas com 4 painéis e carga vertical aplicada nos nós do "
        "banzo superior (equivalente a uma carga distribuída sobre a cobertura). "
        "Exercita conversão de carregamento e múltiplos nós carregados."
    ),
    exercises=["carga distribuída → nodal", "banzo superior comprimido", "simetria"],
    input={
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "C1", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "C2", "x": 4.0, "y": 0.0, "support": "none"},
            {"id": "C3", "x": 6.0, "y": 0.0, "support": "none"},
            {"id": "E", "x": 8.0, "y": 0.0, "support": "roller"},
            {"id": "T1", "x": 2.0, "y": 2.5, "support": "none"},
            {"id": "T2", "x": 4.0, "y": 3.0, "support": "none"},
            {"id": "T3", "x": 6.0, "y": 2.5, "support": "none"},
        ],
        "members": [
            {"id": "AC1", "a": "A", "b": "C1", "EA": 1.0},
            {"id": "C1C2", "a": "C1", "b": "C2", "EA": 1.0},
            {"id": "C2C3", "a": "C2", "b": "C3", "EA": 1.0},
            {"id": "C3E", "a": "C3", "b": "E", "EA": 1.0},
            {"id": "AT1", "a": "A", "b": "T1", "EA": 1.0},
            {"id": "T1T2", "a": "T1", "b": "T2", "EA": 1.0},
            {"id": "T2T3", "a": "T2", "b": "T3", "EA": 1.0},
            {"id": "T3E", "a": "T3", "b": "E", "EA": 1.0},
            {"id": "C1T1", "a": "C1", "b": "T1", "EA": 1.0},
            {"id": "C2T2", "a": "C2", "b": "T2", "EA": 1.0},
            {"id": "C3T3", "a": "C3", "b": "T3", "EA": 1.0},
            {"id": "T1C2", "a": "T1", "b": "C2", "EA": 1.0},
            {"id": "T3C2", "a": "T3", "b": "C2", "EA": 1.0},
        ],
        "loads": [
            {"node": "T1", "Fx": 0.0, "Fy": -4.0},
            {"node": "T2", "Fx": 0.0, "Fy": -8.0},
            {"node": "T3", "Fx": 0.0, "Fy": -4.0},
        ],
    },
)

# ---------------------------------------------------------------- 3
case(
    slug="03-warren",
    name="Treliça Warren com 3 painéis",
    description=(
        "Banzo inferior reto, banzo superior com montantes inclinados em zigue-zague. "
        "Carregamento simétrico nos nós superiores; os resultados devem sair simétricos."
    ),
    exercises=["simetria", "padrão alternado de tração/compressão"],
    input={
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "B0", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B1", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "B2", "x": 4.0, "y": 0.0, "support": "none"},
            {"id": "B3", "x": 6.0, "y": 0.0, "support": "roller"},
            {"id": "T0", "x": 1.0, "y": 2.0, "support": "none"},
            {"id": "T1", "x": 3.0, "y": 2.0, "support": "none"},
            {"id": "T2", "x": 5.0, "y": 2.0, "support": "none"},
        ],
        "members": [
            {"id": "B0B1", "a": "B0", "b": "B1", "EA": 1.0},
            {"id": "B1B2", "a": "B1", "b": "B2", "EA": 1.0},
            {"id": "B2B3", "a": "B2", "b": "B3", "EA": 1.0},
            {"id": "T0T1", "a": "T0", "b": "T1", "EA": 1.0},
            {"id": "T1T2", "a": "T1", "b": "T2", "EA": 1.0},
            {"id": "B0T0", "a": "B0", "b": "T0", "EA": 1.0},
            {"id": "T0B1", "a": "T0", "b": "B1", "EA": 1.0},
            {"id": "B1T1", "a": "B1", "b": "T1", "EA": 1.0},
            {"id": "T1B2", "a": "T1", "b": "B2", "EA": 1.0},
            {"id": "B2T2", "a": "B2", "b": "T2", "EA": 1.0},
            {"id": "T2B3", "a": "T2", "b": "B3", "EA": 1.0},
        ],
        "loads": [
            {"node": "T0", "Fx": 0.0, "Fy": -10.0},
            {"node": "T1", "Fx": 0.0, "Fy": -10.0},
            {"node": "T2", "Fx": 0.0, "Fy": -10.0},
        ],
    },
)

# ---------------------------------------------------------------- 4
case(
    slug="04-pratt-vento",
    name="Treliça Pratt com carga lateral (vento)",
    description=(
        "Banzo superior reto, montantes verticais e diagonais. Carga vertical nos nós "
        "internos mais uma força horizontal no nó superior da extremidade. O roleto em "
        "B3 não resiste a esforço horizontal, então toda a componente horizontal vai "
        "para o pino em B0."
    ),
    exercises=["carga inclinada/lateral", "reação horizontal", "tração/compressão alternada"],
    input={
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "B0", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B1", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "B2", "x": 4.0, "y": 0.0, "support": "none"},
            {"id": "B3", "x": 6.0, "y": 0.0, "support": "roller"},
            {"id": "T0", "x": 0.0, "y": 2.0, "support": "none"},
            {"id": "T1", "x": 2.0, "y": 2.0, "support": "none"},
            {"id": "T2", "x": 4.0, "y": 2.0, "support": "none"},
            {"id": "T3", "x": 6.0, "y": 2.0, "support": "none"},
        ],
        "members": [
            {"id": "B0B1", "a": "B0", "b": "B1", "EA": 1.0},
            {"id": "B1B2", "a": "B1", "b": "B2", "EA": 1.0},
            {"id": "B2B3", "a": "B2", "b": "B3", "EA": 1.0},
            {"id": "T0T1", "a": "T0", "b": "T1", "EA": 1.0},
            {"id": "T1T2", "a": "T1", "b": "T2", "EA": 1.0},
            {"id": "T2T3", "a": "T2", "b": "T3", "EA": 1.0},
            {"id": "B0T0", "a": "B0", "b": "T0", "EA": 1.0},
            {"id": "B1T1", "a": "B1", "b": "T1", "EA": 1.0},
            {"id": "B2T2", "a": "B2", "b": "T2", "EA": 1.0},
            {"id": "B3T3", "a": "B3", "b": "T3", "EA": 1.0},
            {"id": "T0B1", "a": "T0", "b": "B1", "EA": 1.0},
            {"id": "T1B2", "a": "T1", "b": "B2", "EA": 1.0},
            {"id": "T2B3", "a": "T2", "b": "B3", "EA": 1.0},
        ],
        "loads": [
            {"node": "T1", "Fx": 0.0, "Fy": -10.0},
            {"node": "T2", "Fx": 0.0, "Fy": -10.0},
            {"node": "T3", "Fx": 8.0, "Fy": 0.0},
        ],
    },
)

# ---------------------------------------------------------------- 5
case(
    slug="05-forca-zero-T",
    name="Treliça com barras de força zero (regra R2)",
    description=(
        "Painel quadrado com uma diagonal e um nó superior sem carga e sem vínculo "
        "(nó D). Pela regra R2, as duas barras que chegam em D (CD e DA) têm força "
        "zero. Serve para mostrar que a regra é geométrica e não depende da carga."
    ),
    exercises=["barras de força zero", "regra R2"],
    input={
        "units": {"force": "kN", "length": "m"},
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
            {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
        ],
        "loads": [{"node": "C", "Fx": 6.0, "Fy": -10.0}],
    },
    exact={
        "members": {"AB": 0.0, "BC": -14.5, "CD": 0.0, "DA": 0.0, "AC": 7.5},
        "reactions": {"A": {"Rx": -6.0, "Ry": -4.5}, "B": {"Ry": 14.5}},
    },
)

# ---------------------------------------------------------------- 6
case(
    slug="06-forca-zero-R3",
    name="Treliça com barras de força zero (regra R3)",
    description=(
        "Nó C no meio do banzo inferior recebe três barras, sendo duas colineares "
        "(AC e CB). Pela regra R3, a terceira barra (CT, o montante central) tem força "
        "zero — mas continua com rigidez, o que é uma distinção importante."
    ),
    exercises=["barras de força zero", "regra R3"],
    input={
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "T", "x": 2.0, "y": 3.0, "support": "none"},
        ],
        "members": [
            {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
            {"id": "CB", "a": "C", "b": "B", "EA": 1.0},
            {"id": "CT", "a": "C", "b": "T", "EA": 1.0},
            {"id": "AT", "a": "A", "b": "T", "EA": 1.0},
            {"id": "BT", "a": "B", "b": "T", "EA": 1.0},
        ],
        "loads": [{"node": "T", "Fx": 0.0, "Fy": -10.0}],
    },
    exact={
        "members": {
            "AC": 10.0 / 3.0,
            "CB": 10.0 / 3.0,
            "CT": 0.0,
            "AT": -5.0 * math.sqrt(13) / 3.0,
            "BT": -5.0 * math.sqrt(13) / 3.0,
        },
        "reactions": {"A": {"Rx": 0.0, "Ry": 5.0}, "B": {"Ry": 5.0}},
    },
)

# ---------------------------------------------------------------- 7
case(
    slug="07-geometria-irregular",
    name="Geometria irregular (ângulos não triviais)",
    description=(
        "Treliça com nós fora de alinhamento ortogonal: ângulos não triviais nos "
        "cossenos diretores e duas cargas inclinadas em nós distintos."
    ),
    exercises=["cossenos diretores", "decomposição de forças"],
    input={
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 5.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 1.0, "y": 3.0, "support": "none"},
            {"id": "D", "x": 4.0, "y": 2.0, "support": "none"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
            {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
            {"id": "CD", "a": "C", "b": "D", "EA": 1.0},
            {"id": "DB", "a": "D", "b": "B", "EA": 1.0},
            {"id": "AD", "a": "A", "b": "D", "EA": 1.0},
        ],
        "loads": [
            {"node": "C", "Fx": -4.0, "Fy": -10.0},
            {"node": "D", "Fx": 3.0, "Fy": -6.0},
        ],
    },
)

# ---------------------------------------------------------------- 8
case(
    slug="08-hiperestatica",
    name="Treliça hiperestática de grau 1",
    description=(
        "Quadrado com as duas diagonais: b + r = 6 + 3 = 9 > 2n = 8, grau 1. "
        "O método dos nós não resolve (sistema não quadrado); o método da rigidez "
        "resolve, mas os esforços passam a depender de EA."
    ),
    exercises=["hiperestaticidade", "método matricial", "dependência de EA"],
    hyperstatic=True,
    input={
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
    },
)

# ---------------------------------------------------------------- 9
case(
    slug="09-hipostatica",
    name="Treliça hipostática (deve falhar com mensagem)",
    description=(
        "Triângulo com pino em A e nenhum vínculo em B: b + r = 3 + 2 = 5 < 2n = 6. "
        "Falta um vínculo — é um mecanismo. O programa deve recusar o cálculo com "
        "mensagem clara, não devolver números absurdos."
    ),
    exercises=["caso de erro", "estaticidade"],
    expect_error="hypostatic",
    input={
        "units": {"force": "kN", "length": "m"},
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "none"},
            {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
            {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
            {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
        ],
        "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
    },
)

# ---------------------------------------------------------------- 10
case(
    slug="10-mecanismo",
    name="Mecanismo interno com g = 0 (deve falhar com mensagem)",
    description=(
        "Nó B no meio de dois pinos A e C, com apenas as barras AB e CB, ambas "
        "colineares. A contagem dá b + r = 2 + 4 = 6 = 2n, ou seja g = 0, mas B pode "
        "se deslocar verticalmente sem resistência de primeira ordem: a matriz de "
        "rigidez é singular. Prova que a contagem não garante estabilidade."
    ),
    exercises=["caso de erro", "mecanismo", "limite da contagem b+r vs 2n"],
    expect_error="mechanism",
    input={
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
    },
)

# ---------------------------------------------------------------- 11
case(
    slug="11-sem-carga",
    name="Estado trivial: treliça válida sem carregamento",
    description=(
        "Mesma geometria do caso 1, sem nenhuma carga aplicada. Todas as barras devem "
        "ficar com força zero e todas as reações nulas."
    ),
    exercises=["estado trivial", "barras de força zero"],
    input={
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
        "loads": [],
    },
)

# ---------------------------------------------------------------- 12
case(
    slug="12-pratt-grande",
    name="Treliça de maior porte: Pratt com 6 painéis (14 nós, 25 barras)",
    description=(
        "Treliça de ponte com 6 painéis, 14 nós e 25 barras, carga distribuída "
        "convertida em cargas nodais no banzo superior. Verifica escala, legibilidade "
        "do diagrama e desempenho."
    ),
    exercises=["escala", "desempenho", "padrão global de esforços"],
    input=None,  # preenchido abaixo
)

_bottom = [(f"B{i}", 2.0 * i, 0.0) for i in range(7)]
_top = [(f"T{i}", 2.0 * i, 3.0) for i in range(7)]
_nodes = [
    {"id": "B0", "x": 0.0, "y": 0.0, "support": "pin"},
    {"id": "B6", "x": 12.0, "y": 0.0, "support": "roller"},
]
for name, x, y in _bottom[1:6]:
    _nodes.append({"id": name, "x": x, "y": y, "support": "none"})
for name, x, y in _top:
    _nodes.append({"id": name, "x": x, "y": y, "support": "none"})

_members = []
for i in range(6):
    _members.append({"id": f"B{i}B{i+1}", "a": f"B{i}", "b": f"B{i+1}", "EA": 1.0})
    _members.append({"id": f"T{i}T{i+1}", "a": f"T{i}", "b": f"T{i+1}", "EA": 1.0})
for i in range(7):
    _members.append({"id": f"B{i}T{i}", "a": f"B{i}", "b": f"T{i}", "EA": 1.0})
for i in range(3):
    _members.append({"id": f"T{i}B{i+1}", "a": f"T{i}", "b": f"B{i+1}", "EA": 1.0})
    _members.append({"id": f"T{6-i}B{5-i}", "a": f"T{6-i}", "b": f"B{5-i}", "EA": 1.0})

_loads = [{"node": f"T{i}", "Fx": 0.0, "Fy": -8.0} for i in range(1, 6)]

CASES[-1]["input"] = {
    "units": {"force": "kN", "length": "m"},
    "nodes": _nodes,
    "members": _members,
    "loads": _loads,
}


def main():
    outdir = os.path.join("data", "cases")
    os.makedirs(outdir, exist_ok=True)
    problems = []

    for entry in CASES:
        slug = entry["slug"]
        payload = entry["input"]
        out = solve_payload(payload)

        print("=" * 78)
        print(slug, "-", entry["name"])

        expected_error = entry.get("expect_error")
        if expected_error:
            codes = [e["code"] for e in out.get("errors", [])]
            ok = out["status"] == "error" and expected_error in codes
            print("  status:", out["status"], "| erros:", codes, "| OK" if ok else "| FALHOU")
            if not ok:
                problems.append(f"{slug}: esperava erro {expected_error}, veio {codes}")
            record = {
                "name": entry["name"],
                "description": entry["description"],
                "exercises": entry.get("exercises", []),
                "input": payload,
                "expect": {"status": "error", "errorCode": expected_error},
            }
        else:
            if out["status"] != "ok":
                problems.append(f"{slug}: solver falhou -> {out['errors']}")
                print("  FALHOU:", out["errors"])
                continue

            det = out["determinacy"]
            print(f"  n={det['n']} b={det['b']} r={det['r']} g={det['degree']} ({det['label']})")

            member_forces = {m["id"]: m["N"] for m in out["members"]}
            reactions = {
                r["node"]: {"Rx": r["Rx"], "Ry": r["Ry"]} for r in out["reactions"]
            }

            # conferência independente
            if not entry.get("hyperstatic"):
                truss = parse_truss(payload)
                ref = method_of_joints(truss)
                worst = max(
                    abs(member_forces[k] - v) for k, v in ref.member_forces.items()
                )
                print(f"  método dos nós: diferença máxima = {worst:.3e}")
                if worst > 1e-9:
                    problems.append(f"{slug}: rigidez x nós divergem ({worst:.3e})")

            # equilíbrio
            checks = out["checks"]
            print(
                "  equilíbrio: ΣFx=%.2e ΣFy=%.2e ΣM=%.2e residual nodal=%.2e (%s)"
                % (
                    checks["sumFx"],
                    checks["sumFy"],
                    checks["sumM"],
                    checks["maxNodalResidual"],
                    "ok" if checks["passed"] else "FALHOU",
                )
            )
            if not checks["passed"]:
                problems.append(f"{slug}: equilíbrio não fechou")

            # gabarito exato, quando existe
            if entry.get("exact"):
                for mid, value in entry["exact"]["members"].items():
                    delta = abs(member_forces[mid] - value)
                    flag = "ok" if delta < 1e-9 else f"DIFERENÇA {delta:.2e}"
                    print(f"  exato {mid}: {member_forces[mid]:+.6f} (esperado {value:+.6f}) {flag}")
                    if delta >= 1e-9:
                        problems.append(f"{slug}: {mid} fora do gabarito exato")
                for node, comps in entry["exact"]["reactions"].items():
                    for comp, value in comps.items():
                        got = reactions[node][comp]
                        delta = abs(got - value)
                        if delta >= 1e-9:
                            problems.append(f"{slug}: reação {node}.{comp} fora do gabarito")
                        print(f"  exato R{node}.{comp}: {got:+.6f} (esperado {value:+.6f})")

            record = {
                "name": entry["name"],
                "description": entry["description"],
                "exercises": entry.get("exercises", []),
                "input": payload,
                "expect": {
                    "status": "ok",
                    "determinacy": {
                        "n": det["n"],
                        "b": det["b"],
                        "r": det["r"],
                        "degree": det["degree"],
                        "label": det["label"],
                    },
                    "members": member_forces,
                    "reactions": reactions,
                    "zeroForce": sorted(z["member"] for z in out["zero_force"]),
                    "tolerance": 1e-6,
                },
            }

        with open(os.path.join(outdir, slug + ".json"), "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    print("=" * 78)
    if problems:
        print("PROBLEMAS:")
        for item in problems:
            print(" -", item)
        return 1
    print(f"OK — {len(CASES)} casos gerados e verificados em {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
