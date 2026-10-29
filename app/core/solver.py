"""Orquestração: da entrada JSON à saída completa (o contrato do projeto).

Todo o cálculo acontece em **kN e m**. Na saída, os valores são convertidos de
volta para as unidades que o usuário informou, de modo que o rótulo `units` da
resposta sempre corresponde aos números entregues.
"""

from __future__ import annotations

import numpy as np

from . import equilibrium
from .determinacy import analyze_determinacy
from .errors import InputError, TrussError
from .joints import cross_check
from .model import Truss, parse_truss
from .stiffness import _ILL_CONDITIONED, StiffnessResult, analyze
from .stress import analyze_stress, required_areas
from .topology import analyze_topology
from .units import area_factor, force_factor, length_factor, stress_factor
from .zero_force import collinearity_warning, summarize_zero_force


class _Converter:
    """Converte valores internos (kN, m) para as unidades de entrada."""

    def __init__(self, truss: Truss) -> None:
        self.force = force_factor(truss.units_force)    # kN por unidade de entrada
        self.length = length_factor(truss.units_length)  # m por unidade de entrada
        self.area = area_factor(truss.units_area)        # mm² por unidade de entrada
        self.stress = stress_factor(truss.units_stress)  # MPa por unidade de entrada

    def force_value(self, value: float) -> float:
        return float(value) / self.force

    def length_value(self, value: float) -> float:
        return float(value) / self.length

    def moment_value(self, value: float) -> float:
        return float(value) / (self.force * self.length)

    def stiffness_value(self, value: float) -> float:
        # rigidez = força / comprimento
        return float(value) * self.length / self.force


    def area_value(self, value: float | None) -> float | None:
        return None if value is None else float(value) / self.area

    def stress_value(self, value: float) -> float:
        return float(value) / self.stress
    def displacement_value(self, value: float) -> float:
        return float(value) / self.length


def _reaction_entries(truss: Truss, result: StiffnessResult, conv: _Converter) -> list[dict]:
    entries: list[dict] = []
    for node in truss.nodes:
        if not node.is_support:
            continue
        rx = result.reaction(node.id, "ux") if "ux" in node.restraints else 0.0
        ry = result.reaction(node.id, "uy") if "uy" in node.restraints else 0.0
        entries.append(
            {
                "node": node.id,
                "support": node.support,
                "Rx": conv.force_value(rx),
                "Ry": conv.force_value(ry),
                "components": list(node.restraints),
            }
        )
    return entries


def _member_entries(truss: Truss, result: StiffnessResult, conv: _Converter) -> list[dict]:
    areas = {member.id: member.area_mm2 for member in truss.members}
    entries: list[dict] = []
    for member in result.members:
        entries.append(
            {
                "id": member.id,
                "a": member.a,
                "b": member.b,
                "length": conv.length_value(member.length),
                "EA": conv.force_value(member.EA),
                "area": conv.area_value(areas.get(member.id)),
                "N": conv.force_value(member.N),
                "state": member.state,
                "zero_force": member.state == "força zero",
            }
        )
    return entries


def _convert_stress(payload: dict, conv: _Converter) -> dict:
    """Leva tensão (MPa) e área (mm²) para as unidades de entrada."""
    def convert_entry(entry: dict) -> dict:
        converted = dict(entry)
        if "N" in converted and converted["N"] is not None:
            converted["N"] = conv.force_value(converted["N"])
        for key in ("area", "currentArea", "requiredArea"):
            if converted.get(key) is not None:
                converted[key] = conv.area_value(converted[key])
        for key in ("sigma", "allowable"):
            if converted.get(key) is not None:
                converted[key] = conv.stress_value(converted[key])
        return converted

    entries = [convert_entry(entry) for entry in payload.get("entries", [])]

    summary = dict(payload.get("summary") or {})
    for key in ("maxTension", "maxCompression", "critical"):
        if summary.get(key):
            summary[key] = {
                **summary[key],
                "sigma": conv.stress_value(summary[key]["sigma"]),
            }
    if "maxAbsStress" in summary:
        summary["maxAbsStress"] = conv.stress_value(summary["maxAbsStress"])
    if summary.get("totalRequiredArea") is not None:
        summary["totalRequiredArea"] = conv.area_value(summary["totalRequiredArea"])
    if summary.get("governing"):
        summary["governing"] = {
            **summary["governing"],
            "requiredArea": conv.area_value(summary["governing"]["requiredArea"]),
        }

    res = {**payload, "entries": entries, "summary": summary}
    if "allowable" in payload and payload["allowable"] is not None:
        if isinstance(payload["allowable"], dict):
            res["allowable"] = {
                k: (conv.stress_value(v) if v is not None else None)
                for k, v in payload["allowable"].items()
            }
        else:
            res["allowable"] = conv.stress_value(payload["allowable"])

    return res


def _summary(result: StiffnessResult, conv: _Converter) -> dict:
    tension = [member for member in result.members if member.N > 0]
    compression = [member for member in result.members if member.N < 0]
    zero = [member for member in result.members if member.N == 0]

    def pick(items: list, key) -> dict | None:
        if not items:
            return None
        best = max(items, key=key)
        return {"id": best.id, "N": conv.force_value(best.N)}

    return {
        "members": len(result.members),
        "tension": len(tension),
        "compression": len(compression),
        "zero": len(zero),
        "maxTension": pick(tension, lambda member: member.N),
        "maxCompression": pick(compression, lambda member: -member.N),
        "maxAbsForce": conv.force_value(
            max((abs(member.N) for member in result.members), default=0.0)
        ),
        "maxDisplacement": conv.displacement_value(
            max(
                (
                    float(np.hypot(result.u[2 * i], result.u[2 * i + 1]))
                    for i in range(result.truss.n)
                ),
                default=0.0,
            )
        ),
    }


def _checks_payload(truss: Truss, result: StiffnessResult, conv: _Converter) -> dict:
    raw = equilibrium.summarize(truss, result)
    nodal = {
        node_id: {
            "rx": conv.force_value(values["rx"]),
            "ry": conv.force_value(values["ry"]),
        }
        for node_id, values in raw["nodal"].items()
    }
    return {
        "sumFx": conv.force_value(raw["sumFx"]),
        "sumFy": conv.force_value(raw["sumFy"]),
        "sumM": conv.moment_value(raw["sumM"]),
        "maxNodalResidual": conv.force_value(raw["maxNodalResidual"]),
        "worstNode": raw["worstNode"],
        "passed": raw["passed"],
        "tolerance": raw["tolerance"],
        "nodal": nodal,
    }


def build_solution(truss: Truss, result: StiffnessResult) -> dict:
    """Monta o dicionário de saída a partir de um resultado válido."""
    conv = _Converter(truss)
    topology = analyze_topology(truss)
    member_forces = {member.id: member.N for member in result.members}

    warnings = list(truss.warnings)
    warnings.extend(topology.warnings)
    warnings.extend(collinearity_warning(truss))
    if result.determinacy.degree > 0:
        warnings.append(
            "Treliça hiperestática: os esforços normais dependem da rigidez relativa "
            "das barras (EA). Confira os valores de EA usados."
        )
    if result.condition > _ILL_CONDITIONED:
        warnings.append(
            "A matriz de rigidez é mal condicionada "
            f"(cond(K_ff) ≈ {result.condition:.1e}). O resultado está correto dentro "
            "da precisão disponível, mas perde dígitos significativos — evite EA com "
            "contraste extremo entre as barras."
        )

    displacements = []
    for node in truss.nodes:
        ux, uy = result.displacement(node.id)
        displacements.append(
            {
                "node": node.id,
                "ux": conv.displacement_value(ux),
                "uy": conv.displacement_value(uy),
            }
        )

    zero_force = [
        {**entry, "N": conv.force_value(entry["N"])}
        for entry in summarize_zero_force(truss, member_forces)
    ]

    cross = cross_check(truss, member_forces)
    if cross.get("members"):
        cross = {
            **cross,
            "members": {
                key: conv.force_value(value) for key, value in cross["members"].items()
            },
            "maxDifference": conv.force_value(cross["maxDifference"]),
            "tolerance": conv.force_value(cross["tolerance"]),
        }

    # A conferência pelo método dos nós é independente do método da rigidez: se
    # ela diverge numa treliça isostática, o resultado não é confiável mesmo com
    # o equilíbrio fechando (pode ser condicionamento extremo). Não rebaixamos o
    # status — o contrato devolve o cálculo —, mas o aviso é explícito.
    if cross.get("available") and cross.get("passed") is False:
        warnings.append(
            "A conferência pelo método dos nós divergiu "
            f"({cross.get('maxDifference', 0):.3g} contra tolerância "
            f"{cross.get('tolerance', 0):.3g}): trate os esforços como aproximados. "
            "Isso costuma indicar rigidez (EA) muito contrastada entre as barras."
        )

    stress = analyze_stress(truss, member_forces)
    stress = _convert_stress(stress, conv)

    return {
        "status": "ok",
        "units": {
            "force": truss.units_force,
            "length": truss.units_length,
            "area": truss.units_area,
            "stress": truss.units_stress,
        },
        "determinacy": result.determinacy.to_dict(),
        "reactions": _reaction_entries(truss, result, conv),
        "members": _member_entries(truss, result, conv),
        "stress": stress,
        "displacements": displacements,
        "checks": _checks_payload(truss, result, conv),
        "crossCheck": cross,
        "zero_force": zero_force,
        "summary": _summary(result, conv),
        "warnings": warnings,
        "errors": [],
        "matrix": {
            "size": int(result.K.shape[0]),
            "freeDofs": list(result.free_dofs),
            "restrainedDofs": list(result.restrained_dofs),
            "K": [
                [conv.stiffness_value(value) for value in row] for row in result.K
            ],
        },
    }


def _error_payload(message_code: dict, **extra) -> dict:
    payload = {
        "status": "error",
        "code": message_code.get("code"),
        "message": message_code.get("message"),
        "units": None,
        "determinacy": None,
        "reactions": [],
        "members": [],
        "stress": None,
        "displacements": [],
        "checks": None,
        "crossCheck": None,
        "zero_force": [],
        "summary": None,
        "warnings": [],
        "errors": [message_code],
        "matrix": None,
    }
    payload.update(extra)
    return payload


def solve_payload(data: dict) -> dict:
    """Ponto de entrada principal: recebe a entrada bruta e devolve a saída.

    Erros de domínio (entrada inválida, treliça hipostática, mecanismo) voltam no
    campo `errors` com `status = "error"` — nunca como exceção solta.
    """
    try:
        truss = parse_truss(data)
    except TrussError as exc:
        return _error_payload(exc.to_dict())

    try:
        result = analyze(truss)
    except TrussError as exc:
        return _error_payload(
            exc.to_dict(),
            units={"force": truss.units_force, "length": truss.units_length},
            determinacy=analyze_determinacy(truss).to_dict(),
            warnings=list(truss.warnings),
        )

    return build_solution(truss, result)

def stress_payload(data: dict, mode: str = "stress", allowable=None) -> dict:
    """Calcula tensões normais ou áreas necessárias a partir do modelo.

    `mode="stress"`: usa as áreas já informadas em cada barra e devolve
    sigma = N/A. `mode="area"`: usa a tensão admissível informada e devolve a
    área necessária por barra. `allowable` pode ser um número (MPa) ou um
    dicionário `{"tension": ..., "compression": ...}`.

    Erros de modelo voltam em `errors`, com `status = "error"` — igual a
    `solve_payload`.
    """
    try:
        truss = parse_truss(data)
    except TrussError as exc:
        return _error_payload(exc.to_dict())

    try:
        result = analyze(truss)
    except TrussError as exc:
        return _error_payload(
            exc.to_dict(),
            units={"force": truss.units_force, "length": truss.units_length},
            determinacy=analyze_determinacy(truss).to_dict(),
        )

    conv = _Converter(truss)
    member_forces = {member.id: member.N for member in result.members}

    allowable_internal = allowable
    if allowable is not None:
        if isinstance(allowable, dict):
            allowable_internal = {}
            for k, v in allowable.items():
                if v is not None:
                    try:
                        allowable_internal[k] = float(v) * conv.stress
                    except (TypeError, ValueError):
                        return _error_payload(
                            {"message": "tensão admissível inválida", "code": "bad_allowable"}
                        )
                else:
                    allowable_internal[k] = None
        else:
            try:
                allowable_internal = float(allowable) * conv.stress
            except (TypeError, ValueError):
                return _error_payload(
                    {"message": "tensão admissível inválida", "code": "bad_allowable"}
                )

    try:
        if mode == "area":
            payload = required_areas(truss, member_forces, allowable_internal)
        else:
            payload = analyze_stress(truss, member_forces)
    except TrussError as exc:
        return _error_payload(exc.to_dict())

    return {
        "status": "ok",
        "mode": "area" if mode == "area" else "stress",
        "units": {
            "force": truss.units_force,
            "length": truss.units_length,
            "area": truss.units_area,
            "stress": truss.units_stress,
        },
        "stress": _convert_stress(payload, conv),
        "errors": [],
    }
