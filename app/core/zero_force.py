"""Barras de força zero.

As três regras clássicas, todas condicionadas a **nó sem carga aplicada e sem
vínculo** (se houver reação de apoio no nó, a regra não vale):

* **R1** — nó com 1 barra: essa barra é de força zero.
* **R2** — nó com 2 barras **não colineares**: ambas são de força zero.
* **R3** — nó com 3 barras, sendo 2 colineares: a terceira é de força zero.

As regras são geométricas e independem do carregamento. O solver ainda confirma
numericamente (`|N| ≈ 0`), e a interface mostra as duas informações.
"""

from __future__ import annotations

from .model import Truss

_PARALLEL_TOL = 1e-9

def _direction(truss: Truss, member_id: str, node_id: str) -> tuple[float, float]:
    """Versor da barra apontando **para fora** do nó informado."""
    member = truss.member_by_id(member_id)
    length, c, s = truss.member_geometry(member)
    if member.a == node_id:
        return c, s
    return -c, -s


def _are_parallel(d1: tuple[float, float], d2: tuple[float, float]) -> bool:
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    return abs(cross) <= _PARALLEL_TOL


def _members_at(truss: Truss, node_id: str) -> list[str]:
    return [
        member.id
        for member in truss.members
        if member.a == node_id or member.b == node_id
    ]


def find_zero_force_rules(truss: Truss) -> dict[str, str]:
    """Retorna `{id_da_barra: justificativa}` pelas regras geométricas."""
    found: dict[str, str] = {}
    loaded_nodes = {load.node for load in truss.loads}

    for node in truss.nodes:
        if node.is_support or node.id in loaded_nodes:
            continue

        members = _members_at(truss, node.id)
        count = len(members)
        if count == 0:
            continue

        directions = {mid: _direction(truss, mid, node.id) for mid in members}

        if count == 1:
            found.setdefault(
                members[0],
                f"R1: nó {node.id} tem apenas esta barra e nenhuma carga/vínculo.",
            )
            continue

        if count == 2:
            first, second = members
            if not _are_parallel(directions[first], directions[second]):
                reason = (
                    f"R2: nó {node.id} tem só 2 barras não colineares, sem carga "
                    "nem vínculo — ambas ficam com força zero."
                )
                found.setdefault(first, reason)
                found.setdefault(second, reason)
            continue

        if count == 3:
            for candidate in members:
                others = [mid for mid in members if mid != candidate]
                if _are_parallel(directions[others[0]], directions[others[1]]):
                    if _are_parallel(directions[candidate], directions[others[0]]):
                        continue
                    found.setdefault(
                        candidate,
                        f"R3: nó {node.id} tem 3 barras, sendo 2 colineares "
                        f"({others[0]} e {others[1]}) — a terceira ({candidate}) é de força zero.",
                    )
                    break

    return found


def summarize_zero_force(truss: Truss, member_forces: dict[str, float], tol: float = 1e-9) -> list[dict]:
    """Lista as barras de força zero, cruzando regra geométrica e resultado numérico."""
    rules = find_zero_force_rules(truss)
    peak = max((abs(value) for value in member_forces.values()), default=0.0)
    threshold = tol * max(1.0, peak)

    entries: list[dict] = []
    for member in truss.members:
        force = member_forces.get(member.id, 0.0)
        numeric = abs(force) <= threshold
        rule = rules.get(member.id)
        if not numeric and rule is None:
            continue
        entries.append(
            {
                "member": member.id,
                "N": 0.0 if numeric else force,
                "numeric": numeric,
                "rule": rule,
                "confirmed": numeric and rule is not None,
                "reason": rule or "confirmado numericamente pelo solver (|N| ≈ 0)",
            }
        )

    # ordena por id para saída determinística
    entries.sort(key=lambda item: item["member"])
    return entries


def collinearity_warning(truss: Truss) -> list[str]:
    """Aviso quando duas barras do mesmo nó estão sobre a mesma reta (geometria degenerada)."""
    messages: list[str] = []
    for node in truss.nodes:
        members = _members_at(truss, node.id)
        if len(members) < 2:
            continue
        directions = {mid: _direction(truss, mid, node.id) for mid in members}
        for i, first in enumerate(members):
            for second in members[i + 1 :]:
                if _are_parallel(directions[first], directions[second]):
                    dot = (
                        directions[first][0] * directions[second][0]
                        + directions[first][1] * directions[second][1]
                    )
                    if dot < 0:
                        messages.append(
                            f"nó {node.id}: barras {first} e {second} são colineares "
                            "(sobrepostas na mesma reta)."
                        )
    return messages
