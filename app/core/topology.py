"""Topologia da treliça: conectividade e avisos estruturais."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Truss


@dataclass(frozen=True)
class TopologyReport:
    components: tuple[tuple[str, ...], ...]   # subestruturas desconexas
    isolated_nodes: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def is_connected(self) -> bool:
        return len(self.components) <= 1


def analyze_topology(truss: Truss) -> TopologyReport:
    """Encontra componentes conexos do grafo nó-barra."""
    adjacency: dict[str, set[str]] = {node.id: set() for node in truss.nodes}
    for member in truss.members:
        adjacency[member.a].add(member.b)
        adjacency[member.b].add(member.a)

    visited: set[str] = set()
    components: list[tuple[str, ...]] = []
    for node_id in truss.node_ids:
        if node_id in visited:
            continue
        stack = [node_id]
        group: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            group.append(current)
            stack.extend(sorted(adjacency[current] - visited))
        components.append(tuple(sorted(group)))

    isolated = tuple(sorted(node_id for node_id, links in adjacency.items() if not links))
    warnings: list[str] = []
    if len(components) > 1:
        parts = " | ".join("{" + ", ".join(group) + "}" for group in components)
        warnings.append(
            f"a treliça está dividida em {len(components)} subestruturas desconexas: {parts}."
        )
    return TopologyReport(
        components=tuple(components),
        isolated_nodes=isolated,
        warnings=tuple(warnings),
    )
