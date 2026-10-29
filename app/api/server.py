"""Servidor local (FastAPI) do módulo Trusses.

Rotas:

* `GET  /`                 — interface web (editor + resultados)
* `GET  /api/health`       — estado do serviço
* `GET  /api/presets`      — lista de casos prontos (sem o modelo completo)
* `GET  /api/presets/{id}` — caso pronto completo
* `POST /api/solve`        — resolve a treliça (contrato em `docs/plano.md` §4)
* `POST /api/figure`       — devolve o diagrama em SVG
* `POST /api/report`       — devolve o relatório imprimível em HTML

O cálculo é **sempre** delegado a `app.core`; nada de engenharia aqui.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.report import render_report
from app.core.errors import TrussError
from app.core.model import parse_truss
from app.core.solver import solve_payload, stress_payload
from app.render.svg import render_error_svg, render_truss_svg

VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = ROOT / "data" / "cases"
WEB_DIR = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(
    title="Trusses — versão própria do MdSolids",
    description=(
        "Cálculo de treliças planas: reações de apoio, esforços normais "
        "(tração/compressão) e barras de força zero pelo método matricial da "
        "rigidez, com conferência independente pelo método dos nós."
    ),
    version=VERSION,
)


def _load_presets() -> list[dict]:
    presets: list[dict] = []
    if not CASES_DIR.is_dir():
        return presets
    for path in sorted(CASES_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        presets.append(
            {
                "slug": path.stem,
                "name": record.get("name", path.stem),
                "description": record.get("description", ""),
                "exercises": record.get("exercises", []),
                "input": record.get("input"),
                "expectError": (record.get("expect") or {}).get("errorCode"),
            }
        )
    return presets


PRESETS = _load_presets()
PRESETS_BY_SLUG = {preset["slug"]: preset for preset in PRESETS}


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": VERSION,
        "presets": len(PRESETS),
        "engine": "método matricial da rigidez (numpy)",
    }


@app.get("/api/presets")
def list_presets() -> dict:
    """Lista os casos prontos, sem o modelo completo (para o seletor da interface)."""
    return {
        "presets": [
            {key: value for key, value in preset.items() if key != "input"}
            for preset in PRESETS
        ]
    }


@app.get("/api/presets/{slug}")
def get_preset(slug: str) -> dict:
    preset = PRESETS_BY_SLUG.get(slug)
    if preset is None:
        raise HTTPException(status_code=404, detail=f"caso não encontrado: {slug}")
    return preset


@app.post("/api/solve")
def solve(payload: dict = Body(...)) -> dict:
    """Resolve a treliça. Erros de modelo voltam em `errors` com `status = "error"`."""
    try:
        return solve_payload(payload)
    except TrussError as err:
        return JSONResponse(
            content={"status": "error", "code": err.code, "message": str(err)},
            status_code=200,
        )

def _dimension(value, default: int) -> int:
    """Dimensão do SVG: inteiro entre 16 e 4000, com fallback seguro.

    `OverflowError` cobre JSON com `1e999` (lido como `inf`), que não pode
    derrubar a rota com HTTP 500.
    """
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return max(16, min(number, 4000))


def _flag(value, default: bool = False) -> bool:
    """Booleano tolerante: `bool("false")` seria `True`, o que inverteria flags."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


@app.post("/api/figure")
def figure(payload: dict = Body(...)) -> Response:
    """Diagrama da treliça em SVG (com esforços, se o modelo for resolvível)."""
    model = payload.get("model") or {}
    width = _dimension(payload.get("width"), 880)
    height = _dimension(payload.get("height"), 520)
    palette = payload.get("palette") or "padrao"
    show_stress = _flag(payload.get("showStress"), False)

    try:
        parse_truss(model)
    except TrussError as exc:
        # Modelo inválido não pode derrubar a rota: devolve um SVG explicativo.
        svg = render_error_svg(exc.message, width=width, height=height)
        return Response(content=svg, media_type="image/svg+xml")

    solution = solve_payload(model)
    svg = render_truss_svg(
        model,
        solution if solution.get("status") == "ok" else None,
        width=width,
        height=height,
        show_values=_flag(payload.get("showValues"), True),
        show_displacements=_flag(payload.get("showDisplacements"), False),
        palette=palette,
        show_stress=show_stress,
    )
    return Response(content=svg, media_type="image/svg+xml")


@app.post("/api/stress")
def stress(payload: dict = Body(...)) -> dict:
    """Tensão normal nas barras (sigma = N/A) ou área necessária.

    Corpo: `{"model": {...}, "mode": "stress"|"area", "allowable": 50}`.
    `mode` padrão é `"stress"`, que usa as áreas já informadas em cada barra.
    Em `mode="area"`, `allowable` é a tensão admissível — um número na unidade de
    tensão do modelo, ou `{"tension": .., "compression": ..}`.
    """
    model = payload.get("model") or {}
    mode = str(payload.get("mode") or "stress").strip().lower()
    if mode not in {"stress", "area"}:
        raise HTTPException(
            status_code=400,
            detail=f"modo inválido: {mode!r}. Use 'stress' ou 'area'.",
        )
    try:
        return stress_payload(model, mode=mode, allowable=payload.get("allowable"))
    except TrussError as err:
        return JSONResponse(
            content={"status": "error", "code": err.code, "message": str(err)},
            status_code=200,
        )


@app.post("/api/report", response_class=HTMLResponse)
def report(payload: dict = Body(...)) -> HTMLResponse:
    """Relatório imprimível do caso (HTML)."""
    model = payload.get("model") or {}
    solution = solve_payload(model)

    if solution.get("status") != "ok":
        errors = solution.get("errors") or [{"message": "modelo inválido"}]
        messages = "".join(f"<li>{escape(str(item['message']))}</li>" for item in errors)
        return HTMLResponse(
            "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<title>Relatório — modelo inválido</title></head><body "
            "style=\"font-family:system-ui,sans-serif;padding:32px;max-width:720px\">"
            "<h1 style='font-size:19px'>Não foi possível gerar o relatório</h1>"
            f"<ul style='font-size:14px;line-height:1.6'>{messages}</ul>"
            "</body></html>",
            status_code=200,
        )

    html = render_report(
        model,
        solution,
        title=payload.get("title"),
        palette=payload.get("palette") or "padrao",
        show_stress=_flag(payload.get("showStress"), False),
    )
    return HTMLResponse(html)


# A interface web fica na raiz — precisa ser montada por último.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
