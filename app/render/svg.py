"""Desenho do diagrama da treliça em SVG, gerado no servidor.

Vantagem de desenhar no servidor: o **mesmo** diagrama aparece na interface e no
relatório impresso, e não existe conta de engenharia (nem geometria de resultado)
duplicada em JavaScript.

Convenções visuais:

* **azul** = tração, **vermelho** = compressão, **cinza tracejado** = força zero;
* a espessura da barra cresce com o módulo do esforço normal;
* setas de carga (para dentro do nó) e de reação (para fora) com rótulo numérico.
"""

from __future__ import annotations

import math
from html import escape

# Paleta padrão: acessível e legível em projeção e impressão.
TENSION_COLOR = "#2563eb"
COMPRESSION_COLOR = "#dc2626"
ZERO_COLOR = "#94a3b8"

# Paleta do MdSolids original (documentada no help oficial e extraída do binário
# 4.0): tração em ciano, compressão em ouro, força zero em magenta.
# Disponível como opção explícita para quem precisa reconhecer a tela original.
PALETTES: dict[str, dict[str, str]] = {
    "padrao": {
        "tension": "#2563eb",
        "compression": "#dc2626",
        "zero": "#94a3b8",
    },
    "mdsolids": {
        "tension": "#00b8d4",
        "compression": "#b8860b",
        "zero": "#d81b9b",
    },
}
DEFAULT_PALETTE = "padrao"

NODE_COLOR = "#0f172a"
LOAD_COLOR = "#7c3aed"
REACTION_COLOR = "#059669"
LABEL_COLOR = "#0f172a"
MUTED_COLOR = "#64748b"

_FONT = "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


def _fmt(value: float, decimals: int = 2) -> str:
    rounded = round(float(value), decimals)
    if rounded == 0:
        rounded = 0.0
    text = f"{rounded:.{decimals}f}"
    return text.replace("-", "\u2212")  # sinal de menos tipográfico


class _Projection:
    """Converte coordenadas do modelo em coordenadas de tela (y para baixo)."""

    def __init__(self, nodes: list[dict], width: float, height: float, pad: float = 54.0) -> None:
        xs = [float(node["x"]) for node in nodes]
        ys = [float(node["y"]) for node in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max_x - min_x
        span_y = max_y - min_y
        usable_w = max(width - 2 * pad, 10.0)
        usable_h = max(height - 2 * pad, 10.0)

        if span_x <= 1e-12 and span_y <= 1e-12:
            self.scale = 1.0
        elif span_x <= 1e-12:
            self.scale = usable_h / span_y
        elif span_y <= 1e-12:
            self.scale = usable_w / span_x
        else:
            self.scale = min(usable_w / span_x, usable_h / span_y)

        self.min_x, self.min_y = min_x, min_y
        self.width, self.height, self.pad = width, height, pad
        # centraliza o desenho na área útil
        self.offset_x = pad + (usable_w - span_x * self.scale) / 2
        self.offset_y = pad + (usable_h - span_y * self.scale) / 2

    def point(self, x: float, y: float) -> tuple[float, float]:
        return (
            self.offset_x + (float(x) - self.min_x) * self.scale,
            self.height - self.offset_y - (float(y) - self.min_y) * self.scale,
        )


def _arrow_head(x1: float, y1: float, x2: float, y2: float, size: float = 9.0) -> str:
    angle = math.atan2(y2 - y1, x2 - x1)
    left = angle + math.radians(150)
    right = angle - math.radians(150)
    points = [
        (x2, y2),
        (x2 + size * math.cos(left), y2 + size * math.sin(left)),
        (x2 + size * math.cos(right), y2 + size * math.sin(right)),
    ]
    return " ".join(f"{px:.2f},{py:.2f}" for px, py in points)


def _support_symbol(support: str, x: float, y: float, color: str = REACTION_COLOR) -> str:
    """Símbolo do apoio desenhado abaixo (ou ao lado) do nó."""
    parts: list[str] = []
    base_y = y + 13.0
    if support in {"pin", "roller", "roller_x"}:
        parts.append(
            f'<polygon points="{x:.2f},{y:.2f} {x - 9:.2f},{base_y:.2f} {x + 9:.2f},{base_y:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="1.8"/>'
        )
    if support == "roller":
        for offset in (-5.0, 5.0):
            parts.append(
                f'<circle cx="{x + offset:.2f}" cy="{base_y + 3.4:.2f}" r="2.6" '
                f'fill="none" stroke="{color}" stroke-width="1.4"/>'
            )
        parts.append(
            f'<line x1="{x - 13:.2f}" y1="{base_y + 6.6:.2f}" x2="{x + 13:.2f}" '
            f'y2="{base_y + 6.6:.2f}" stroke="{color}" stroke-width="1.4"/>'
        )
    elif support == "roller_x":
        for offset in (-5.0, 5.0):
            parts.append(
                f'<circle cx="{x - 13.4:.2f}" cy="{y + offset:.2f}" r="2.6" '
                f'fill="none" stroke="{color}" stroke-width="1.4"/>'
            )
        parts.append(
            f'<line x1="{x - 16.6:.2f}" y1="{y - 13:.2f}" x2="{x - 16.6:.2f}" '
            f'y2="{y + 13:.2f}" stroke="{color}" stroke-width="1.4"/>'
        )
    elif support == "pin":
        parts.append(
            f'<line x1="{x - 13:.2f}" y1="{base_y + 4:.2f}" x2="{x + 13:.2f}" '
            f'y2="{base_y + 4:.2f}" stroke="{color}" stroke-width="1.4"/>'
        )
    return "".join(parts)


def _member_style(
    state: str, magnitude: float, peak: float, palette: dict[str, str]
) -> tuple[str, str, float]:
    if state == "tração":
        color, dash = palette["tension"], ""
    elif state == "compressão":
        color, dash = palette["compression"], ""
    else:
        color, dash = palette["zero"], ' stroke-dasharray="5 4"'
    ratio = 0.0 if peak <= 0 else min(abs(magnitude) / peak, 1.0)
    width = 1.6 + 2.6 * ratio
    return color, dash, width


def resolve_palette(palette) -> dict[str, str]:
    """Aceita o nome da paleta ('padrao' | 'mdsolids') ou um dicionário de cores."""
    if isinstance(palette, dict):
        merged = dict(PALETTES[DEFAULT_PALETTE])
        merged.update({key: str(value) for key, value in palette.items()})
        return merged
    key = str(palette or DEFAULT_PALETTE).strip().lower()
    return dict(PALETTES.get(key, PALETTES[DEFAULT_PALETTE]))


def render_truss_svg(
    model: dict,
    solution: dict | None = None,
    *,
    width: int = 780,
    height: int = 470,
    show_values: bool = True,
    show_reactions: bool = True,
    show_loads: bool = True,
    show_displacements: bool = False,
    palette: str | dict | None = DEFAULT_PALETTE,
    show_stress: bool = False,
) -> str:
    """Desenha a treliça. Com `solution`, colore e rotula por estado das barras.

    `palette="mdsolids"` reproduz as cores do software original (tração em ciano,
    compressão em ouro, força zero em magenta). Com `show_stress=True` e tensões
    disponíveis, o rótulo de cada barra passa a mostrar a tensão em vez do
    esforço normal.
    """
    nodes = model.get("nodes") or []
    members = model.get("members") or []
    loads = model.get("loads") or []
    colors = resolve_palette(palette)
    if not nodes:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="100%" role="img"><text x="{width / 2}" y="{height / 2}" '
            f'text-anchor="middle" fill="{MUTED_COLOR}" font-family="{_FONT}" '
            f'font-size="14">sem geometria para desenhar</text></svg>'
        )

    proj = _Projection(nodes, width, height)
    coords = {node["id"]: proj.point(node["x"], node["y"]) for node in nodes}

    force_by_member: dict[str, float] = {}
    state_by_member: dict[str, str] = {}
    stress_by_member: dict[str, float] = {}
    if solution and solution.get("members"):
        for entry in solution["members"]:
            force_by_member[entry["id"]] = float(entry["N"])
            state_by_member[entry["id"]] = entry["state"]

    stress_units = ""
    if solution and solution.get("stress") and solution["stress"].get("entries"):
        for entry in solution["stress"]["entries"]:
            stress_by_member[entry["id"]] = float(entry["sigma"])
        stress_units = str((solution.get("units") or {}).get("stress", ""))

    stress_mode = bool(show_stress and stress_by_member)

    peak = max((abs(value) for value in force_by_member.values()), default=0.0)
    parts: list[str] = []

    parts.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>'
    )

    # -- barras --------------------------------------------------------------
    for member in members:
        member_id = member.get("id") or f"{member.get('a')}{member.get('b')}"
        a, b = member.get("a"), member.get("b")
        if a not in coords or b not in coords:
            continue
        x1, y1 = coords[a]
        x2, y2 = coords[b]
        force = force_by_member.get(member_id, 0.0)
        state = state_by_member.get(member_id, "")
        color, dash, stroke_width = _member_style(state, force, peak, colors)
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{stroke_width:.2f}" stroke-linecap="round"{dash}/>'
        )

        if show_values and solution:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / length, dx / length
            if ny > 0:
                nx, ny = -nx, -ny
            lx, ly = mx + nx * 13, my + ny * 13
            if stress_mode and member_id in stress_by_member:
                label = f"σ {_fmt(stress_by_member[member_id], 1)}"
            else:
                label = f"{_fmt(force)}"
            parts.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-family="{_FONT}" font-size="10.5" '
                f'font-weight="600" fill="{color}">{escape(label)}</text>'
            )

    # -- cargas aplicadas ----------------------------------------------------
    if show_loads:
        for load in loads:
            node_id = load.get("node")
            if node_id not in coords:
                continue
            fx, fy = float(load.get("Fx") or 0.0), float(load.get("Fy") or 0.0)
            magnitude = math.hypot(fx, fy)
            if magnitude <= 0:
                continue
            x, y = coords[node_id]
            ux, uy = fx / magnitude, -fy / magnitude  # y do SVG é invertido
            length = 44.0
            sx, sy = x - ux * length, y - uy * length
            parts.append(
                f'<line x1="{sx:.2f}" y1="{sy:.2f}" x2="{x - ux * 9:.2f}" '
                f'y2="{y - uy * 9:.2f}" stroke="{LOAD_COLOR}" stroke-width="1.9"/>'
            )
            parts.append(
                f'<polygon points="{_arrow_head(sx, sy, x - ux * 9, y - uy * 9)}" '
                f'fill="{LOAD_COLOR}"/>'
            )
            parts.append(
                f'<text x="{sx - ux * 6:.2f}" y="{sy - uy * 6:.2f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-family="{_FONT}" font-size="10.5" '
                f'font-weight="600" fill="{LOAD_COLOR}">{escape(_fmt(magnitude, 1))}</text>'
            )

    # -- reações de apoio ----------------------------------------------------
    if show_reactions and solution:
        for entry in solution.get("reactions") or []:
            node_id = entry["node"]
            if node_id not in coords:
                continue
            x, y = coords[node_id]
            for component, key in (("ux", "Rx"), ("uy", "Ry")):
                value = float(entry.get(key) or 0.0)
                if abs(value) < 1e-9:
                    continue
                if component == "ux":
                    ux, uy = (1.0 if value > 0 else -1.0), 0.0
                else:
                    ux, uy = 0.0, (-1.0 if value > 0 else 1.0)
                length = 40.0
                ex, ey = x + ux * length, y + uy * length
                parts.append(
                    f'<line x1="{x + ux * 9:.2f}" y1="{y + uy * 9:.2f}" x2="{ex:.2f}" '
                    f'y2="{ey:.2f}" stroke="{REACTION_COLOR}" stroke-width="1.7"/>'
                )
                parts.append(
                    f'<polygon points="{_arrow_head(x + ux * 9, y + uy * 9, ex, ey)}" '
                    f'fill="{REACTION_COLOR}"/>'
                )
                parts.append(
                    f'<text x="{ex + ux * 9:.2f}" y="{ey + uy * 9:.2f}" text-anchor="middle" '
                    f'dominant-baseline="middle" font-family="{_FONT}" font-size="10" '
                    f'font-weight="600" fill="{REACTION_COLOR}">{escape(_fmt(value, 1))}</text>'
                )

    # -- deslocamentos -------------------------------------------------------
    if show_displacements and solution and solution.get("displacements"):
        magnitudes = [
            math.hypot(d["ux"], d["uy"]) for d in solution["displacements"]
        ]
        biggest = max(magnitudes, default=0.0)
        if biggest > 0:
            for entry in solution["displacements"]:
                x, y = coords[entry["node"]]
                ux, uy = float(entry["ux"]), float(entry["uy"])
                scale = 26.0 / biggest
                ex, ey = x + ux * scale, y - uy * scale
                parts.append(
                    f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" '
                    f'stroke="{MUTED_COLOR}" stroke-width="1" stroke-dasharray="3 3"/>'
                )
                parts.append(f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="1.8" fill="{MUTED_COLOR}"/>')

    # -- apoios --------------------------------------------------------------
    for node in nodes:
        support = node.get("support") or "none"
        if support == "none":
            continue
        x, y = coords[node["id"]]
        parts.append(_support_symbol(support, x, y))

    # -- nós e rótulos -------------------------------------------------------
    for node in nodes:
        x, y = coords[node["id"]]
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.2" fill="{NODE_COLOR}"/>'
        )
        label = str(node["id"])
        parts.append(
            f'<text x="{x + 8:.2f}" y="{y - 8:.2f}" font-family="{_FONT}" font-size="11.5" '
            f'font-weight="700" fill="{LABEL_COLOR}">{escape(label)}</text>'
        )

    # -- legenda -------------------------------------------------------------
    legend_y = height - 14
    legend = [
        (colors["tension"], "tração"),
        (colors["compression"], "compressão"),
        (colors["zero"], "força zero"),
    ]
    offset = 16.0
    for color, text in legend:
        dash = ' stroke-dasharray="5 4"' if text == "força zero" else ""
        parts.append(
            f'<line x1="{offset:.2f}" y1="{legend_y:.2f}" x2="{offset + 20:.2f}" '
            f'y2="{legend_y:.2f}" stroke="{color}" stroke-width="2.6"{dash}/>'
        )
        parts.append(
            f'<text x="{offset + 26:.2f}" y="{legend_y + 3.6:.2f}" font-family="{_FONT}" '
            f'font-size="10.5" fill="{MUTED_COLOR}">{escape(text)}</text>'
        )
        offset += 118.0
    if solution:
        units = (solution.get("units") or {})
        if stress_mode:
            caption = f"tensão em {units.get('stress', '')}"
        else:
            caption = f"esforços em {units.get('force', '')}"
        parts.append(
            f'<text x="{width - 12:.2f}" y="{legend_y + 3.6:.2f}" text-anchor="end" '
            f'font-family="{_FONT}" font-size="10.5" fill="{MUTED_COLOR}">'
            f'{escape(caption)}</text>'
        )

    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="diagrama da treliça com esforços normais">{body}</svg>'
    )
