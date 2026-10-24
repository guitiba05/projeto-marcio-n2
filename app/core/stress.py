"""Tensão normal nas barras e dimensionamento inverso.

O módulo Trusses do MdSolids tem, além da análise de esforços, o comando
**Stresses → "Normal Stresses in Truss Members"**, que trabalha em dois sentidos:

1. **dado** a área da seção de cada barra, **calcular** a tensão normal
   `σ = N / A`;
2. **dado** uma tensão admissível, **calcular** a área necessária
   `A = |N| / σ_adm`.

Este módulo implementa os dois. A base interna de tensão é **N e mm²**, porque
assim a tensão sai diretamente em **MPa** (1 MPa = 1 N/mm²), que é a unidade em
que o resultado é lido na prática. O esforço normal chega em kN (base do
cálculo estrutural) e é convertido aqui.

Convenção herdada e mantida: `N > 0` é tração, `N < 0` é compressão. A tensão
segue o mesmo sinal — tração positiva, compressão negativa.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .errors import InputError
from .model import Truss
from .stiffness import COMPRESSION, TENSION, ZERO


def _as_float(value: object, what: str = "tensão admissível") -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise InputError(f"{what} inválida", code="bad_allowable")
    if not math.isfinite(number):
        raise InputError(f"{what} inválida", code="bad_allowable")
    return number


# 1 kN = 1000 N; a área já está em mm², então σ[MPa] = N[kN] * 1000 / A[mm²]
_KN_TO_N = 1000.0


def normal_stress_mpa(force_kn: float, area_mm2: float) -> float:
    """Tensão normal `σ = N/A` em MPa. Positiva em tração."""
    if area_mm2 is None or area_mm2 <= 0:
        raise InputError(
            "a área da seção deve ser maior que zero para calcular a tensão "
            f"(recebido {area_mm2!r}).",
            code="bad_area",
        )
    return float(force_kn) * _KN_TO_N / float(area_mm2)


def required_area_mm2(force_kn: float, allowable_mpa: float) -> float:
    """Área necessária para que `|σ| ≤ σ_adm`, em mm²."""
    if allowable_mpa is None or allowable_mpa <= 0:
        raise InputError(
            "a tensão admissível deve ser maior que zero para calcular a área "
            f"(recebido {allowable_mpa!r}).",
            code="bad_allowable",
        )
    return abs(float(force_kn)) * _KN_TO_N / float(allowable_mpa)


@dataclass(frozen=True)
class StressEntry:
    id: str
    a: str
    b: str
    force_kn: float
    area_mm2: float
    stress_mpa: float
    state: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "a": self.a,
            "b": self.b,
            "N": self.force_kn,
            "area": self.area_mm2,
            "sigma": self.stress_mpa,
            "state": self.state,
        }


def _state_of(force_kn: float) -> str:
    if force_kn > 0:
        return TENSION
    if force_kn < 0:
        return COMPRESSION
    return ZERO


def analyze_stress(truss: Truss, member_forces: dict[str, float]) -> dict:
    """Tensão em cada barra que tenha área informada.

    Retorna um dicionário pronto para a saída da API:

    * `available` — `True` se **todas** as barras têm área;
    * `partial`   — `True` se apenas algumas têm;
    * `entries`   — tensão por barra (apenas as que têm área);
    * `missing`   — barras sem área informada;
    * `summary`   — maior tração, maior compressão e barra crítica.
    """
    entries: list[StressEntry] = []
    missing: list[str] = []

    for member in truss.members:
        force = float(member_forces.get(member.id, 0.0))
        if member.area_mm2 is None or member.area_mm2 <= 0:
            missing.append(member.id)
            continue
        entries.append(
            StressEntry(
                id=member.id,
                a=member.a,
                b=member.b,
                force_kn=force,
                area_mm2=member.area_mm2,
                stress_mpa=normal_stress_mpa(force, member.area_mm2),
                state=_state_of(force),
            )
        )

    available = bool(entries) and not missing
    tension = [entry for entry in entries if entry.stress_mpa > 0]
    compression = [entry for entry in entries if entry.stress_mpa < 0]

    def extreme(items: list[StressEntry], key) -> dict | None:
        if not items:
            return None
        best = max(items, key=key)
        return {"id": best.id, "sigma": best.stress_mpa}

    critical = None
    if entries:
        worst = max(entries, key=lambda entry: abs(entry.stress_mpa))
        critical = {"id": worst.id, "sigma": worst.stress_mpa}

    return {
        "available": available,
        "partial": bool(entries) and bool(missing),
        "entries": [entry.to_dict() for entry in entries],
        "missing": missing,
        "summary": {
            "members": len(entries),
            "maxTension": extreme(tension, lambda entry: entry.stress_mpa),
            "maxCompression": extreme(compression, lambda entry: -entry.stress_mpa),
            "critical": critical,
            "maxAbsStress": max(
                (abs(entry.stress_mpa) for entry in entries), default=0.0
            ),
        },
    }


def required_areas(
    truss: Truss,
    member_forces: dict[str, float],
    allowable_mpa: float,
) -> dict:
    """Dimensionamento inverso: área necessária por barra para uma σ_adm.

    A área necessária é a mesma para tração e compressão do ponto de vista
    aritmético (`A = |N| / σ_adm`). Quando a tensão admissível de compressão for
    diferente (material com limites distintos), use `allowable_compression_mpa`.
    """
    allowable_tension = allowable_mpa
    allowable_compression = allowable_mpa
    if isinstance(allowable_mpa, dict):
        allowable_tension = allowable_mpa.get("tension", allowable_mpa.get("value"))
        allowable_compression = allowable_mpa.get(
            "compression", allowable_mpa.get("value")
        )

    entries: list[dict] = []
    for member in truss.members:
        force = float(member_forces.get(member.id, 0.0))
        limit = allowable_compression if force < 0 else allowable_tension
        if limit is None:
            raise InputError(
                f"barra {member.id}: tensão admissível não informada para "
                f"{'compressão' if force < 0 else 'tração'}.",
                code="bad_allowable",
            )
        limit_val = _as_float(limit, "tensão admissível")
        required = required_area_mm2(force, limit_val)
        current = member.area_mm2
        entries.append(
            {
                "id": member.id,
                "a": member.a,
                "b": member.b,
                "N": force,
                "state": _state_of(force),
                "allowable": limit_val,
                "requiredArea": required,
                "currentArea": current,
                # None quando a área atual não foi informada
                "utilisation": (
                    None if not current else abs(force) * _KN_TO_N / current / limit_val
                ),
                "ok": (None if not current else current >= required - 1e-9),
            }
        )

    total = sum(entry["requiredArea"] for entry in entries)
    worst = max(entries, key=lambda entry: entry["requiredArea"], default=None)

    return {
        "available": True,
        "allowable": {
            "tension": _as_float(allowable_tension, "tensão admissível") if allowable_tension is not None else None,
            "compression": (
                _as_float(allowable_compression, "tensão admissível") if allowable_compression is not None else None
            ),
        },
        "entries": entries,
        "summary": {
            "members": len(entries),
            "totalRequiredArea": total,
            "governing": (
                None
                if worst is None
                else {"id": worst["id"], "requiredArea": worst["requiredArea"]}
            ),
            "allSufficient": all(entry["ok"] for entry in entries if entry["ok"] is not None)
            if any(entry["ok"] is not None for entry in entries)
            else None,
        },
    }
