"""Erros de domínio do módulo Trusses.

Todos os erros carregam um `code` estável (usado nos testes e na API) e uma
mensagem em português pronta para ser mostrada ao usuário.
"""

from __future__ import annotations


class TrussError(Exception):
    """Erro base do domínio."""

    code = "truss_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


class InputError(TrussError):
    """Entrada inválida (geometria, cargas, unidades, referências)."""

    code = "input_error"


class DeterminacyError(TrussError):
    """Treliça hipostática: não é possível resolver por equilíbrio."""

    code = "hypostatic"


class MechanismError(TrussError):
    """Treliça com mecanismo interno (matriz de rigidez singular)."""

    code = "mechanism"
