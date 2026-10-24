"""Núcleo de cálculo do módulo Trusses — domínio puro, sem I/O."""

from .determinacy import Determinacy, analyze_determinacy
from .errors import (
    DeterminacyError,
    InputError,
    MechanismError,
    TrussError,
)
from .model import Load, Member, Node, Truss, parse_truss
from .solver import build_solution, solve_payload, stress_payload
from .stiffness import MemberResult, StiffnessResult, analyze, assemble
from .stress import analyze_stress, normal_stress_mpa, required_area_mm2, required_areas

__all__ = [
    "Determinacy",
    "DeterminacyError",
    "InputError",
    "Load",
    "MechanismError",
    "Member",
    "MemberResult",
    "Node",
    "StiffnessResult",
    "Truss",
    "TrussError",
    "analyze",
    "analyze_determinacy",
    "assemble",
    "build_solution",
    "parse_truss",
    "solve_payload",
    "stress_payload",
    "analyze_stress",
    "normal_stress_mpa",
    "required_area_mm2",
    "required_areas",
]
