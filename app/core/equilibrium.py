"""Verificações de equilíbrio — a "prova" de que o resultado está coerente.

Duas checagens independentes do solver:

1. **Equilíbrio global**: somatório de forças aplicadas + reações = 0 em `Fx`, `Fy`
   e momento em relação à origem.
2. **Equilíbrio nodal**: em cada nó, a soma vetorial dos esforços das barras
   (tração puxa o nó para dentro da barra) mais a carga aplicada deve anular.

Se ambas fecham, o par (reações, esforços normais) é a solução de equilíbrio.
"""

from __future__ import annotations

import math

from .stiffness import StiffnessResult
from .model import Truss


def global_equilibrium(truss: Truss, result: StiffnessResult) -> dict:
    """Resíduos de força e momento para o sistema inteiro (kN, kN·m)."""
    sum_fx = 0.0
    sum_fy = 0.0
    sum_m = 0.0

    for load in truss.loads:
        node = truss.node_map[load.node]
        sum_fx += load.Fx
        sum_fy += load.Fy
        sum_m += node.x * load.Fy - node.y * load.Fx

    for node in truss.nodes:
        for component in node.restraints:
            value = result.reaction(node.id, component)
            if component == "ux":
                sum_fx += value
                sum_m += -node.y * value
            else:
                sum_fy += value
                sum_m += node.x * value

    return {"sumFx": sum_fx, "sumFy": sum_fy, "sumM": sum_m}


def nodal_residuals(truss: Truss, result: StiffnessResult) -> dict[str, tuple[float, float]]:
    """Resíduo de equilíbrio em cada nó (kN). Zero = nó equilibrado."""
    residuals: dict[str, tuple[float, float]] = {
        node.id: (0.0, 0.0) for node in truss.nodes
    }

    for member in result.members:
        # tração puxa o nó inicial na direção a->b e o nó final na direção b->a
        fx, fy = member.N * member.c, member.N * member.s
        ax, ay = residuals[member.a]
        residuals[member.a] = (ax + fx, ay + fy)
        bx, by = residuals[member.b]
        residuals[member.b] = (bx - fx, by - fy)

    for load in truss.loads:
        rx, ry = residuals[load.node]
        residuals[load.node] = (rx + load.Fx, ry + load.Fy)

    for node in truss.nodes:
        rx, ry = residuals[node.id]
        for component in node.restraints:
            value = result.reaction(node.id, component)
            if component == "ux":
                rx += value
            else:
                ry += value
        residuals[node.id] = (rx, ry)

    return residuals


def max_nodal_residual(residuals: dict[str, tuple[float, float]]) -> float:
    return max(
        (math.hypot(rx, ry) for rx, ry in residuals.values()),
        default=0.0,
    )


def summarize(truss: Truss, result: StiffnessResult, tolerance: float = 1e-6) -> dict:
    """Pacote de verificações para a saída e para o painel da interface."""
    forces = global_equilibrium(truss, result)
    residuals = nodal_residuals(truss, result)
    worst_node = None
    worst = 0.0
    for node_id, (rx, ry) in residuals.items():
        magnitude = math.hypot(rx, ry)
        if magnitude > worst:
            worst, worst_node = magnitude, node_id

    peak_force = max((abs(member.N) for member in result.members), default=0.0)
    scale = max(1.0, peak_force)
    passed = (
        abs(forces["sumFx"]) <= tolerance * scale
        and abs(forces["sumFy"]) <= tolerance * scale
        and abs(forces["sumM"]) <= tolerance * scale * 10.0
        and worst <= tolerance * scale
    )

    return {
        "sumFx": forces["sumFx"],
        "sumFy": forces["sumFy"],
        "sumM": forces["sumM"],
        "maxNodalResidual": worst,
        "worstNode": worst_node,
        "passed": passed,
        "tolerance": tolerance,
        "nodal": {
            node_id: {"rx": rx, "ry": ry} for node_id, (rx, ry) in residuals.items()
        },
    }
