"""Método matricial da rigidez para treliças planas.

Dedução em três passos (a mesma que vai para a apresentação teórica):

1. **Relação constitutiva da barra.** Uma barra biarticulada de rigidez axial
   `EA` e comprimento `L` só transmite força normal. O alongamento vale
   `ΔL = u_b·n̂ - u_a·n̂`, onde `n̂ = (c, s)` é o versor do eixo da barra. Logo
   `N = (EA/L)·ΔL` — e `N > 0` significa **tração**.

2. **Matriz de rigidez da barra.** Escrevendo `ΔL` em função dos 4 deslocamentos
   nodais e aplicando o princípio dos trabalhos virtuais, obtém-se

       k = (EA/L) · [[ c²,  cs, -c², -cs],
                     [ cs,  s², -cs, -s²],
                     [-c², -cs,  c²,  cs],
                     [-cs, -s²,  cs,  s²]]

3. **Montagem e solução.** Somam-se as contribuições em `K` (2n × 2n), impõem-se
   os deslocamentos nulos nos apoios (reduzindo o sistema aos GDL livres) e
   resolve-se `K_ff · u_f = F_f`. As reações saem de `R = K·u - F` e o esforço
   normal de `N = (EA/L)·[-c, -s, c, s]·[u_ax, u_ay, u_bx, u_by]`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .determinacy import Determinacy, analyze_determinacy
from .errors import DeterminacyError, MechanismError
from .model import Member, Truss

TENSION = "tração"
COMPRESSION = "compressão"
ZERO = "força zero"

_EIGEN_TOL = 1e-10   # tolerância relativa para considerar autovalor nulo


@dataclass(frozen=True)
class MemberResult:
    id: str
    a: str
    b: str
    length: float
    c: float
    s: float
    EA: float
    N: float          # kN — positivo = tração
    state: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "a": self.a,
            "b": self.b,
            "length": self.length,
            "EA": self.EA,
            "N": self.N,
            "state": self.state,
            "zero_force": self.state == ZERO,
        }


@dataclass(frozen=True)
class StiffnessResult:
    truss: Truss
    determinacy: Determinacy
    K: np.ndarray
    K_ff: np.ndarray
    F: np.ndarray
    free_dofs: tuple[int, ...]
    restrained_dofs: tuple[int, ...]
    u: np.ndarray
    reaction_values: dict[int, float]
    members: tuple[MemberResult, ...]

    def displacement(self, node_id: str) -> tuple[float, float]:
        index = self.truss.node_index(node_id)
        return float(self.u[2 * index]), float(self.u[2 * index + 1])

    def reaction(self, node_id: str, component: str) -> float:
        dof = self.truss.dof(node_id, component)
        return float(self.reaction_values.get(dof, 0.0))


def member_stiffness(EA: float, length: float, c: float, s: float) -> np.ndarray:
    """Matriz de rigidez 4×4 da barra no sistema global (já rotacionada)."""
    cc, ss, cs = c * c, s * s, c * s
    factor = EA / length
    return factor * np.array(
        [
            [cc, cs, -cc, -cs],
            [cs, ss, -cs, -ss],
            [-cc, -cs, cc, cs],
            [-cs, -ss, cs, ss],
        ],
        dtype=float,
    )


def assemble(truss: Truss) -> tuple[np.ndarray, np.ndarray]:
    """Monta a matriz de rigidez global `K` e o vetor de cargas nodais `F`."""
    n_dof = truss.n_dof
    K = np.zeros((n_dof, n_dof), dtype=float)
    F = np.zeros(n_dof, dtype=float)

    for member in truss.members:
        length, c, s = truss.member_geometry(member)
        k_local = member_stiffness(member.EA, length, c, s)
        dofs = [
            truss.dof(member.a, "ux"),
            truss.dof(member.a, "uy"),
            truss.dof(member.b, "ux"),
            truss.dof(member.b, "uy"),
        ]
        K[np.ix_(dofs, dofs)] += k_local

    for load in truss.loads:
        F[truss.dof(load.node, "ux")] += load.Fx
        F[truss.dof(load.node, "uy")] += load.Fy

    return K, F


def _describe_dof(truss: Truss, dof: int) -> str:
    node = truss.nodes[dof // 2]
    component = "ux" if dof % 2 == 0 else "uy"
    return f"{node.id}.{component}"


def find_mechanism_dofs(
    K_ff: np.ndarray, free_dofs: tuple[int, ...], tol_rel: float = _EIGEN_TOL
) -> list[int]:
    """GDL que participam de um modo de deslocamento livre (autovalor nulo)."""
    if K_ff.size == 0:
        return []
    eigenvalues, eigenvectors = np.linalg.eigh(K_ff)
    scale = float(np.max(np.abs(eigenvalues)))
    if scale <= 0.0:
        return list(free_dofs)

    threshold = tol_rel * scale
    suspects: set[int] = set()
    for column in np.nonzero(eigenvalues <= threshold)[0]:
        vector = eigenvectors[:, column]
        peak = float(np.max(np.abs(vector))) or 1.0
        for row in np.nonzero(np.abs(vector) > 1e-6 * peak)[0]:
            suspects.add(free_dofs[int(row)])
    return sorted(suspects)


def analyze(truss: Truss) -> StiffnessResult:
    """Resolve a treliça. Levanta `DeterminacyError`/`MechanismError` se instável."""
    determinacy = analyze_determinacy(truss)
    if determinacy.is_hypostatic:
        raise DeterminacyError(
            f"A treliça é hipostática (grau {determinacy.degree}). {determinacy.detail}",
            code="hypostatic",
        )

    K, F = assemble(truss)
    restrained = tuple(truss.restrained_dofs)
    free_dofs = tuple(dof for dof in range(truss.n_dof) if dof not in set(restrained))

    K_ff = K[np.ix_(list(free_dofs), list(free_dofs))] if free_dofs else np.zeros((0, 0))
    F_f = F[list(free_dofs)] if free_dofs else np.zeros(0)

    mechanism = find_mechanism_dofs(K_ff, free_dofs)
    if mechanism:
        names = ", ".join(_describe_dof(truss, dof) for dof in mechanism)
        raise MechanismError(
            "A treliça tem mecanismo interno: a matriz de rigidez é singular, ou seja, "
            f"existe deslocamento sem resistência nos GDL [{names}]. "
            "A contagem b + r - 2n não garante estabilidade; adicione barras ou vínculos.",
            code="mechanism",
        )

    u = np.zeros(truss.n_dof, dtype=float)
    if free_dofs:
        u_f = np.linalg.solve(K_ff, F_f)
        u[list(free_dofs)] = u_f

    residual = K @ u - F
    reaction_values = {dof: float(residual[dof]) for dof in restrained}

    raw_forces: list[tuple[Member, float, float, float, float]] = []
    for member in truss.members:
        length, c, s = truss.member_geometry(member)
        dofs = [
            truss.dof(member.a, "ux"),
            truss.dof(member.a, "uy"),
            truss.dof(member.b, "ux"),
            truss.dof(member.b, "uy"),
        ]
        elongation = float(np.dot(np.array([-c, -s, c, s]), u[dofs]))
        raw_forces.append((member, length, c, s, member.EA / length * elongation))

    peak = max((abs(item[4]) for item in raw_forces), default=0.0)
    zero_tol = 1e-9 * max(1.0, peak)

    results: list[MemberResult] = []
    for member, length, c, s, force in raw_forces:
        if abs(force) <= zero_tol:
            state = ZERO
            force = 0.0
        elif force > 0:
            state = TENSION
        else:
            state = COMPRESSION
        results.append(
            MemberResult(
                id=member.id,
                a=member.a,
                b=member.b,
                length=length,
                c=c,
                s=s,
                EA=member.EA,
                N=float(force),
                state=state,
            )
        )

    return StiffnessResult(
        truss=truss,
        determinacy=determinacy,
        K=K,
        K_ff=K_ff,
        F=F,
        free_dofs=free_dofs,
        restrained_dofs=restrained,
        u=u,
        reaction_values=reaction_values,
        members=tuple(results),
    )
