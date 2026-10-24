"""Unidades e formatação.

Regra do projeto: **todo cálculo interno é feito em kN e m**. A conversão existe
apenas na borda (entrada/saída), o que elimina a classe de bug mais comum em
software de engenharia: misturar unidades no meio da conta.
"""

from __future__ import annotations

from .errors import InputError

# fatores para converter *de* a unidade *para* kN / m
FORCE_TO_KN: dict[str, float] = {
    "kN": 1.0,
    "N": 1.0e-3,
    "kgf": 9.80665e-3,
    "tf": 9.80665,
    "lbf": 4.4482216152605e-3,
    "kip": 4.4482216152605,
}

LENGTH_TO_M: dict[str, float] = {
    "m": 1.0,
    "cm": 1.0e-2,
    "mm": 1.0e-3,
    "ft": 0.3048,
    "in": 0.0254,
}

# Para tensão e área adotamos uma segunda base interna: **N e mm²**, porque é a
# base em que a tensão sai naturalmente em MPa (1 MPa = 1 N/mm²). A força
# continua sendo convertida para kN no cálculo estrutural; só a tensão usa N/mm².
AREA_TO_MM2: dict[str, float] = {
    "mm2": 1.0,
    "mm²": 1.0,
    "cm2": 1.0e2,
    "cm²": 1.0e2,
    "m2": 1.0e6,
    "m²": 1.0e6,
    "in2": 645.16,
    "in²": 645.16,
}

STRESS_TO_MPA: dict[str, float] = {
    "MPa": 1.0,
    "N/mm2": 1.0,
    "N/mm²": 1.0,
    "kPa": 1.0e-3,
    "GPa": 1.0e3,
    "psi": 6.894757293168361e-3,
    "ksi": 6.894757293168361,
}

DEFAULT_FORCE_UNIT = "kN"
DEFAULT_LENGTH_UNIT = "m"
DEFAULT_AREA_UNIT = "mm²"
DEFAULT_STRESS_UNIT = "MPa"

def force_factor(unit: str) -> float:
    """Fator multiplicativo para levar `unit` até kN."""
    key = (unit or DEFAULT_FORCE_UNIT).strip()
    if key not in FORCE_TO_KN:
        raise InputError(
            f"unidade de força desconhecida: {unit!r}. "
            f"Use uma de: {', '.join(FORCE_TO_KN)}",
            code="bad_units",
        )
    return FORCE_TO_KN[key]


def length_factor(unit: str) -> float:
    """Fator multiplicativo para levar `unit` até m."""
    key = (unit or DEFAULT_LENGTH_UNIT).strip()
    if key not in LENGTH_TO_M:
        raise InputError(
            f"unidade de comprimento desconhecida: {unit!r}. "
            f"Use uma de: {', '.join(LENGTH_TO_M)}",
            code="bad_units",
        )
    return LENGTH_TO_M[key]


def area_factor(unit: str) -> float:
    """Fator multiplicativo para levar `unit` até mm²."""
    key = (unit or DEFAULT_AREA_UNIT).strip()
    if key not in AREA_TO_MM2:
        raise InputError(
            f"unidade de área desconhecida: {unit!r}. "
            f"Use uma de: {', '.join(AREA_TO_MM2)}",
            code="bad_units",
        )
    return AREA_TO_MM2[key]


def stress_factor(unit: str) -> float:
    """Fator multiplicativo para levar `unit` até MPa."""
    key = (unit or DEFAULT_STRESS_UNIT).strip()
    if key not in STRESS_TO_MPA:
        raise InputError(
            f"unidade de tensão desconhecida: {unit!r}. "
            f"Use uma de: {', '.join(STRESS_TO_MPA)}",
            code="bad_units",
        )
    return STRESS_TO_MPA[key]


def format_number(value: float, decimals: int = 3) -> str:
    """Formata número para exibição, evitando `-0.000`."""
    rounded = round(float(value), decimals)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.{decimals}f}"
