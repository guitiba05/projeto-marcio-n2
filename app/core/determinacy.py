"""Estaticidade da treliça: `b + r` versus `2n`.

O grau de indeterminação global é `g = b + r - 2n`:

* `g < 0` → **hipostática**: faltam vínculos, é um mecanismo. Não há solução de
  equilíbrio (o corpo pode se mover).
* `g = 0` → **isostática**: as equações de equilíbrio bastam. Os esforços normais
  não dependem de `EA`.
* `g > 0` → **hiperestática**: sobram vínculos. O método matricial resolve, mas os
  esforços passam a depender da rigidez relativa das barras (`EA`).

Atenção: a contagem é **condição necessária, não suficiente**. Uma treliça com
`g >= 0` ainda pode conter mecanismo interno — isso é detectado no solver pela
singularidade da matriz de rigidez reduzida.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Truss

ISOSTATIC = "isostática"
HYPOSOSTATIC = "hipostática"
HYPERSTATIC = "hiperestática"


@dataclass(frozen=True)
class Determinacy:
    n: int
    b: int
    r: int
    degree: int
    label: str
    detail: str

    @property
    def is_hypostatic(self) -> bool:
        return self.degree < 0

    @property
    def is_hyperstatic(self) -> bool:
        return self.degree > 0

    @property
    def is_isostatic(self) -> bool:
        return self.degree == 0

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "b": self.b,
            "r": self.r,
            "degree": self.degree,
            "label": self.label,
            "detail": self.detail,
        }


def analyze_determinacy(truss: Truss) -> Determinacy:
    n, b, r = truss.n, truss.b, truss.r
    degree = b + r - 2 * n

    if degree < 0:
        label = HYPOSOSTATIC
        detail = (
            f"b + r = {b} + {r} = {b + r} < 2n = {2 * n}. "
            f"Faltam {-degree} vínculo(s): a estrutura é um mecanismo e não pode "
            "ser resolvida apenas pelo equilíbrio."
        )
    elif degree == 0:
        label = ISOSTATIC
        detail = (
            f"b + r = {b} + {r} = {b + r} = 2n = {2 * n}. "
            "As equações de equilíbrio bastam; os esforços normais independem de EA."
        )
    else:
        label = HYPERSTATIC
        detail = (
            f"b + r = {b} + {r} = {b + r} > 2n = {2 * n}. "
            f"Grau de indeterminação {degree}: o método matricial resolve, mas os "
            "esforços dependem da rigidez relativa das barras (EA)."
        )

    return Determinacy(n=n, b=b, r=r, degree=degree, label=label, detail=detail)
