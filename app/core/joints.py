"""Método dos nós em forma matricial — conferência **independente** do solver.

Por que existe: o método da rigidez resolve o problema em termos de
*deslocamentos*. Se houver um erro de formulação na matriz de rigidez, ele pode
passar despercebido. Aqui montamos apenas as **equações de equilíbrio nodal**:

    para cada nó:  Σ (N da barra · versor saindo do nó) + carga + reação = 0

São `2n` equações com `b + r` incógnitas (`N` das barras e reações). Em treliça
isostática `b + r = 2n`, o sistema é quadrado e a solução é única — sem usar `EA`
e sem usar deslocamentos. Se os dois métodos concordam, o resultado é confiável.

Este módulo é usado pelos testes e pelo painel de verificações da interface.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .errors import InputError
from .model import Truss


@dataclass(frozen=True)
class JointsResult:
    member_forces: dict[str, float]
    reactions: dict[str, dict[str, float]]

    def reaction(self, node_id: str, component: str) -> float:
        return float(self.reactions.get(node_id, {}).get(component, 0.0))


def _equilibrium_matrix(truss: Truss) -> tuple[np.ndarray, list[tuple[str, str]], list[tuple[str, str]]]:
    """Monta `A` tal que `A · [N..., R...] = -F_aplicado`."""
    member_columns: list[tuple[str, str]] = [("N", member.id) for member in truss.members]
    reaction_columns: list[tuple[str, str]] = []
    for node in truss.nodes:
        for component in node.restraints:
            reaction_columns.append((node.id, component))

    columns = member_columns + reaction_columns
    A = np.zeros((truss.n_dof, len(columns)), dtype=float)

    for index, member in enumerate(truss.members):
        _, c, s = truss.member_geometry(member)
        ax, ay = truss.dof(member.a, "ux"), truss.dof(member.a, "uy")
        bx, by = truss.dof(member.b, "ux"), truss.dof(member.b, "uy")
        A[ax, index] += c
        A[ay, index] += s
        A[bx, index] += -c
        A[by, index] += -s

    offset = len(member_columns)
    for position, (node_id, component) in enumerate(reaction_columns):
        A[truss.dof(node_id, component), offset + position] = 1.0

    return A, member_columns, reaction_columns


def method_of_joints(truss: Truss) -> JointsResult:
    """Resolve a treliça apenas por equilíbrio nodal.

    Levanta `InputError` se o sistema não for quadrado (hiperestática) ou se a
    matriz de equilíbrio for singular (mecanismo).
    """
    A, member_columns, reaction_columns = _equilibrium_matrix(truss)
    if A.shape[0] != A.shape[1]:
        raise InputError(
            f"o método dos nós exige treliça isostática: b + r = {A.shape[1]}, "
            f"2n = {A.shape[0]}.",
            code="joints_not_isostatic",
        )

    rhs = np.zeros(truss.n_dof, dtype=float)
    for load in truss.loads:
        rhs[truss.dof(load.node, "ux")] -= load.Fx
        rhs[truss.dof(load.node, "uy")] -= load.Fy

    if np.linalg.matrix_rank(A) < A.shape[1]:
        raise InputError(
            "matriz de equilíbrio singular: a treliça tem mecanismo.",
            code="joints_singular",
        )

    solution = np.linalg.solve(A, rhs)

    member_forces = {
        member_id: float(solution[index])
        for index, (_, member_id) in enumerate(member_columns)
    }

    reactions: dict[str, dict[str, float]] = {}
    offset = len(member_columns)
    for position, (node_id, component) in enumerate(reaction_columns):
        reactions.setdefault(node_id, {})[component] = float(solution[offset + position])

    return JointsResult(member_forces=member_forces, reactions=reactions)


def cross_check(truss: Truss, member_forces: dict[str, float], tol: float = 1e-7) -> dict:
    """Compara o resultado do método da rigidez com o do método dos nós."""
    try:
        reference = method_of_joints(truss)
    except InputError as exc:
        return {
            "available": False,
            "reason": exc.message,
            "passed": None,
            "maxDifference": None,
            "members": {},
        }

    differences: dict[str, float] = {}
    peak = max((abs(value) for value in member_forces.values()), default=0.0)
    threshold = tol * max(1.0, peak)

    for member_id, reference_force in reference.member_forces.items():
        value = member_forces.get(member_id, 0.0)
        differences[member_id] = value - reference_force

    worst = max((abs(value) for value in differences.values()), default=0.0)

    reaction_differences: dict[str, dict[str, float]] = {}
    for node in truss.nodes:
        if not node.is_support:
            continue
        reaction_differences[node.id] = {}
        for component in node.restraints:
            reaction_differences[node.id][component] = reference.reaction(node.id, component)

    return {
        "available": True,
        "method": "método dos nós (equilíbrio nodal)",
        "passed": worst <= threshold,
        "maxDifference": worst,
        "tolerance": threshold,
        "members": differences,
        "referenceReactions": reaction_differences,
    }
