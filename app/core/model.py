"""Modelo de dados da treliça (domínio puro, sem I/O).

Hipóteses da idealização (as mesmas do MdSolids/Trusses):

* barras biarticuladas — só transmitem esforço normal (tração/compressão);
* cargas aplicadas exclusivamente nos nós;
* material elástico linear, pequenas deformações;
* treliça plana (2D).

Convenção de sinal fixada aqui e usada em todo o projeto:
**N > 0 → tração**, **N < 0 → compressão**.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .errors import InputError
from .units import (
    DEFAULT_AREA_UNIT,
    DEFAULT_FORCE_UNIT,
    DEFAULT_LENGTH_UNIT,
    DEFAULT_STRESS_UNIT,
    area_factor,
    force_factor,
    length_factor,
    stress_factor,
)

# --- apoios -----------------------------------------------------------------
# chaves canônicas -> componentes de deslocamento restringidas
SUPPORT_RESTRAINTS: dict[str, tuple[str, ...]] = {
    "none": (),
    "pin": ("ux", "uy"),      # articulação fixa: 2 reações
    "roller": ("uy",),        # apoio móvel / roleto: reação vertical
    "roller_x": ("ux",),      # apoio móvel com rolete horizontal: reação horizontal
}

SUPPORT_ALIASES: dict[str, str] = {
    "": "none",
    "none": "none",
    "livre": "none",
    "free": "none",
    "pin": "pin",
    "pino": "pin",
    "articulacao": "pin",
    "articulação": "pin",
    "apoio_fixo": "pin",
    "fixo": "pin",
    "roller": "roller",
    "roleto": "roller",
    "movel": "roller",
    "móvel": "roller",
    "apoio_movel": "roller",
    "roller_x": "roller_x",
    "roleto_x": "roller_x",
}

COMPONENTS = ("ux", "uy")


def normalize_support(value: object) -> str:
    key = str(value or "none").strip().lower()
    if key not in SUPPORT_ALIASES:
        raise InputError(
            f"apoio desconhecido: {value!r}. Use 'none', 'pin', 'roller' ou 'roller_x'.",
            code="bad_support",
        )
    return SUPPORT_ALIASES[key]


def _as_float(value: object, what: str) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise InputError(f"{what} deve ser numérico, recebido {value!r}.", code="bad_number")
    if not math.isfinite(number):
        raise InputError(f"{what} deve ser finito, recebido {value!r}.", code="bad_number")
    return number


@dataclass(frozen=True)
class Node:
    """Nó da treliça. Coordenadas em metros (interno)."""

    id: str
    x: float
    y: float
    support: str = "none"

    @property
    def is_support(self) -> bool:
        return self.support != "none"

    @property
    def restraints(self) -> tuple[str, ...]:
        return SUPPORT_RESTRAINTS[self.support]

    @property
    def n_reactions(self) -> int:
        return len(self.restraints)


@dataclass(frozen=True)
class Member:
    """Barra biarticulada. `EA` em kN (rigidez axial), comprimento em metros."""

    id: str
    a: str
    b: str
    EA: float = 1.0
    # Área da seção transversal em mm². `None` significa "não informada":
    # nesse caso o programa calcula esforços mas não calcula tensão.
    area_mm2: float | None = None


@dataclass(frozen=True)
class Load:
    """Carga nodal em kN."""

    node: str
    Fx: float = 0.0
    Fy: float = 0.0


@dataclass(frozen=True)
class Truss:
    """Treliça pronta para cálculo, já convertida para kN e m."""

    nodes: tuple[Node, ...]
    members: tuple[Member, ...]
    loads: tuple[Load, ...]
    units_force: str = DEFAULT_FORCE_UNIT
    units_length: str = DEFAULT_LENGTH_UNIT
    units_area: str = DEFAULT_AREA_UNIT
    units_stress: str = DEFAULT_STRESS_UNIT
    warnings: tuple[str, ...] = field(default=())

    # -- índices e utilidades ------------------------------------------------
    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.id for node in self.nodes)

    @property
    def node_map(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    @property
    def n(self) -> int:
        return len(self.nodes)

    @property
    def b(self) -> int:
        return len(self.members)

    @property
    def r(self) -> int:
        """Número de reações de apoio (restrições)."""
        return sum(node.n_reactions for node in self.nodes)

    @property
    def n_dof(self) -> int:
        return 2 * self.n

    def node_index(self, node_id: str) -> int:
        for index, node in enumerate(self.nodes):
            if node.id == node_id:
                return index
        raise InputError(f"nó inexistente: {node_id!r}.", code="unknown_node")

    def dof(self, node_id: str, component: str) -> int:
        """Índice do grau de liberdade global: 2*i para ux, 2*i+1 para uy."""
        return 2 * self.node_index(node_id) + COMPONENTS.index(component)

    @property
    def restrained_dofs(self) -> list[int]:
        dofs: list[int] = []
        for node in self.nodes:
            for component in node.restraints:
                dofs.append(self.dof(node.id, component))
        return sorted(dofs)

    def member_by_id(self, member_id: str) -> Member:
        for member in self.members:
            if member.id == member_id:
                return member
        raise InputError(f"barra inexistente: {member_id!r}.", code="unknown_member")

    def member_geometry(self, member: Member) -> tuple[float, float, float]:
        """Retorna `(L, c, s)` — comprimento e cossenos diretores da barra."""
        nodes = self.node_map
        a, b = nodes[member.a], nodes[member.b]
        dx, dy = b.x - a.x, b.y - a.y
        length = math.hypot(dx, dy)
        if length <= 0.0:
            raise InputError(
                f"barra {member.id}: comprimento nulo (nós {member.a} e {member.b} "
                "coincidem).",
                code="zero_length_member",
            )
        return length, dx / length, dy / length

    def load_at(self, node_id: str) -> tuple[float, float]:
        """Soma das cargas aplicadas em um nó."""
        fx = sum(load.Fx for load in self.loads if load.node == node_id)
        fy = sum(load.Fy for load in self.loads if load.node == node_id)
        return fx, fy

    # -- serialização --------------------------------------------------------
    def to_dict(self) -> dict:
        """Reconstrói o dicionário de entrada, nas unidades originais."""
        f_factor = force_factor(self.units_force)
        l_factor = length_factor(self.units_length)
        a_factor = area_factor(self.units_area)
        return {
            "units": {
                "force": self.units_force,
                "length": self.units_length,
                "area": self.units_area,
                "stress": self.units_stress,
            },
            "nodes": [
                {
                    "id": node.id,
                    "x": node.x / l_factor,
                    "y": node.y / l_factor,
                    "support": node.support,
                }
                for node in self.nodes
            ],
            "members": [
                {
                    "id": member.id,
                    "a": member.a,
                    "b": member.b,
                    "EA": member.EA / f_factor,
                    "area": (
                        None if member.area_mm2 is None else member.area_mm2 / a_factor
                    ),
                }
                for member in self.members
            ],
            "loads": [
                {"node": load.node, "Fx": load.Fx / f_factor, "Fy": load.Fy / f_factor}
                for load in self.loads
            ],
        }


def parse_truss(data: dict) -> Truss:
    """Valida e converte um dicionário de entrada em `Truss` (kN, m).

    Levanta `InputError` com todas as mensagens encontradas de uma vez.
    """
    if not isinstance(data, dict):
        raise InputError("a entrada deve ser um objeto JSON.", code="bad_payload")

    problems: list[str] = []
    warnings: list[str] = []

    units = data.get("units") or {}
    if not isinstance(units, dict):
        units = {}
    try:
        units_force = str(units.get("force") or DEFAULT_FORCE_UNIT)
        f_factor = force_factor(units_force)
        units_length = str(units.get("length") or DEFAULT_LENGTH_UNIT)
        l_factor = length_factor(units_length)
        units_area = str(units.get("area") or DEFAULT_AREA_UNIT)
        a_factor = area_factor(units_area)
        units_stress = str(units.get("stress") or DEFAULT_STRESS_UNIT)
        stress_factor(units_stress)  # valida a unidade já na entrada
    except InputError as exc:
        raise InputError(exc.message, code=exc.code) from exc

    # -- nós -----------------------------------------------------------------
    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise InputError("a treliça precisa de pelo menos um nó.", code="no_nodes")

    nodes: list[Node] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_nodes):
        if not isinstance(raw, dict):
            problems.append(f"nó #{index + 1}: formato inválido.")
            continue
        node_id = str(raw.get("id") or f"N{index + 1}").strip()
        if not node_id:
            problems.append(f"nó #{index + 1}: id vazio.")
            continue
        if node_id in seen_ids:
            problems.append(f"nó {node_id}: id repetido.")
            continue
        seen_ids.add(node_id)
        try:
            x = _as_float(raw.get("x", 0.0), f"nó {node_id}: x") * l_factor
            y = _as_float(raw.get("y", 0.0), f"nó {node_id}: y") * l_factor
            support = normalize_support(raw.get("support", "none"))
        except InputError as exc:
            problems.append(exc.message)
            continue
        nodes.append(Node(id=node_id, x=x, y=y, support=support))

    if not nodes:
        raise InputError(
            "nenhum nó válido na entrada.\n- " + "\n- ".join(problems),
            code="no_nodes",
        )

    # -- barras --------------------------------------------------------------
    raw_members = data.get("members")
    if not isinstance(raw_members, list) or not raw_members:
        raise InputError("a treliça precisa de pelo menos uma barra.", code="no_members")

    node_ids = {node.id for node in nodes}
    nodes_by_id = {node.id: node for node in nodes}
    members: list[Member] = []
    seen_members: set[frozenset[str]] = set()
    for index, raw in enumerate(raw_members):
        if not isinstance(raw, dict):
            problems.append(f"barra #{index + 1}: formato inválido.")
            continue
        a = str(raw.get("a") or "").strip()
        b = str(raw.get("b") or "").strip()
        member_id = str(raw.get("id") or f"{a}{b}").strip() or f"M{index + 1}"
        if a not in node_ids:
            problems.append(f"barra {member_id}: nó inicial inexistente ({a!r}).")
            continue
        if b not in node_ids:
            problems.append(f"barra {member_id}: nó final inexistente ({b!r}).")
            continue
        if a == b:
            problems.append(f"barra {member_id}: os dois nós são o mesmo ({a}).")
            continue
        start, end = nodes_by_id[a], nodes_by_id[b]
        if math.hypot(end.x - start.x, end.y - start.y) <= 0.0:
            problems.append(
                f"barra {member_id}: comprimento nulo — os nós {a} e {b} têm as "
                "mesmas coordenadas."
            )
            continue
        pair = frozenset((a, b))
        if pair in seen_members:
            problems.append(
                f"barra {member_id}: ligação {a}-{b} já existe (barra duplicada)."
            )
            continue
        seen_members.add(pair)
        try:
            ea = _as_float(raw.get("EA", 1.0), f"barra {member_id}: EA") * f_factor
        except InputError as exc:
            problems.append(exc.message)
            continue
        if ea <= 0:
            problems.append(f"barra {member_id}: EA deve ser positivo (recebido {ea:g}).")
            continue

        area_mm2: float | None = None
        raw_area = raw.get("area")
        if raw_area is not None and str(raw_area).strip() != "":
            try:
                area_value = _as_float(raw_area, f"barra {member_id}: área") * a_factor
            except InputError as exc:
                problems.append(exc.message)
                continue
            if area_value <= 0:
                problems.append(
                    f"barra {member_id}: a área da seção deve ser positiva "
                    f"(recebido {area_value:g} mm²)."
                )
                continue
            area_mm2 = area_value

        members.append(Member(id=member_id, a=a, b=b, EA=ea, area_mm2=area_mm2))

    if problems:
        raise InputError(
            "a entrada tem problemas:\n- " + "\n- ".join(problems),
            code="invalid_input",
        )
    if not members:
        raise InputError("nenhuma barra válida na entrada.", code="no_members")

    # -- cargas --------------------------------------------------------------
    loads: list[Load] = []
    raw_loads = data.get("loads") or []
    if not isinstance(raw_loads, list):
        raise InputError("'loads' deve ser uma lista.", code="bad_loads")
    for index, raw in enumerate(raw_loads):
        if not isinstance(raw, dict):
            raise InputError(f"carga #{index + 1}: formato inválido.", code="bad_loads")
        node_id = str(raw.get("node") or "").strip()
        if node_id not in node_ids:
            raise InputError(
                f"carga #{index + 1}: nó inexistente ({node_id!r}).",
                code="unknown_node",
            )
        try:
            fx = _as_float(raw.get("Fx", 0.0), f"carga #{index + 1}: Fx") * f_factor
            fy = _as_float(raw.get("Fy", 0.0), f"carga #{index + 1}: Fy") * f_factor
        except InputError as exc:
            raise InputError(exc.message, code=exc.code) from exc
        loads.append(Load(node=node_id, Fx=fx, Fy=fy))

    # -- avisos geométricos --------------------------------------------------
    used = {member.a for member in members} | {member.b for member in members}
    for node in nodes:
        if node.id not in used:
            warnings.append(f"nó {node.id}: sem barras conectadas (nó isolado).")
    if not any(node.is_support for node in nodes):
        raise InputError(
            "a treliça não tem nenhum apoio — o corpo não está vinculado.",
            code="no_supports",
        )

    return Truss(
        nodes=tuple(nodes),
        members=tuple(members),
        loads=tuple(loads),
        units_force=units_force,
        units_length=units_length,
        units_area=units_area,
        units_stress=units_stress,
        warnings=tuple(warnings),
    )
