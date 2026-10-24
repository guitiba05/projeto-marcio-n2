"""Relatório imprimível de um caso (HTML autocontido, pronto para imprimir/salvar PDF).

Este é o documento que fica com o grupo: entrada, diagrama, reações, esforços
normais, barras de força zero e as verificações de equilíbrio. Serve tanto de
registro de validação quanto de plano B para a apresentação caso a máquina falhe.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from app.core.units import format_number
from app.render.svg import render_truss_svg

_CSS = """
* { box-sizing: border-box; }
body {
  margin: 0; padding: 28px 32px 56px;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  color: #0f172a; background: #fff; line-height: 1.45;
}
h1 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
     color: #475569; margin: 26px 0 8px; padding-bottom: 5px;
     border-bottom: 1px solid #e2e8f0; }
.sub { color: #64748b; font-size: 12.5px; margin: 0 0 18px; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
th, td { text-align: left; padding: 5px 9px; border-bottom: 1px solid #eef2f7; }
th { background: #f8fafc; font-weight: 600; color: #334155; font-size: 11.5px;
     text-transform: uppercase; letter-spacing: 0.04em; }
.sigma { text-transform: none; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
/* unidades e símbolos não podem ser maiusculizados (kN ≠ KN, σ ≠ Σ) */
th.num { text-transform: none; }
.tração { color: #2563eb; font-weight: 600; }
.compressão { color: #dc2626; font-weight: 600; }
.força-zero { color: #94a3b8; }
.fig { border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px; margin: 6px 0 0; }
.meta { display: flex; flex-wrap: wrap; gap: 6px 22px; font-size: 12.5px;
        color: #475569; margin-top: 10px; }
.meta b { color: #0f172a; }
.chip { display: inline-block; padding: 1px 9px; border-radius: 999px;
        font-size: 11.5px; font-weight: 600; }
.chip.ok { background: #dcfce7; color: #166534; }
.chip.bad { background: #fee2e2; color: #991b1b; }
.note { font-size: 12px; color: #475569; background: #f8fafc; border-left: 3px solid #cbd5e1;
        padding: 8px 12px; margin: 8px 0 0; border-radius: 0 6px 6px 0; }
ul.plain { margin: 6px 0 0; padding-left: 18px; font-size: 12.5px; }
ul.plain li { margin-bottom: 3px; }
.bar { display: flex; justify-content: space-between; align-items: baseline;
       gap: 16px; flex-wrap: wrap; }
.actions { margin-top: 24px; }
button {
  font: inherit; font-size: 13px; padding: 7px 16px; border-radius: 7px; cursor: pointer;
  border: 1px solid #cbd5e1; background: #fff; color: #0f172a;
}
button.primary { background: #0f172a; border-color: #0f172a; color: #fff; }
@page { size: A4; margin: 14mm; }
@media print {
  body { padding: 0; }
  .no-print { display: none !important; }
  h2 { break-after: avoid; }
  table { break-inside: auto; }
  tr { break-inside: avoid; }
}
"""


def _state_class(state: str) -> str:
    if state == "tração":
        return "tração"
    if state == "compressão":
        return "compressão"
    return "força-zero"


def _reactions_table(solution: dict, units: dict) -> str:
    rows = []
    for entry in solution.get("reactions") or []:
        components = entry.get("components") or []
        rx = format_number(entry["Rx"]) if "ux" in components else "—"
        ry = format_number(entry["Ry"]) if "uy" in components else "—"
        rows.append(
            "<tr>"
            f"<td>{escape(entry['node'])}</td>"
            f"<td>{escape(entry.get('support', ''))}</td>"
            f'<td class="num">{rx}</td>'
            f'<td class="num">{ry}</td>'
            "</tr>"
        )
    if not rows:
        return '<p class="note">sem reações a reportar.</p>'
    return (
        "<table><thead><tr>"
        "<th>nó</th><th>apoio</th>"
        f'<th class="num">Rx [{escape(units.get("force", ""))}]</th>'
        f'<th class="num">Ry [{escape(units.get("force", ""))}]</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _members_table(solution: dict, units: dict) -> str:
    rows = []
    for member in solution.get("members") or []:
        rows.append(
            "<tr>"
            f"<td>{escape(member['id'])}</td>"
            f"<td>{escape(member['a'])}–{escape(member['b'])}</td>"
            f'<td class="num">{format_number(member["length"])}</td>'
            f'<td class="num {_state_class(member["state"])}">{format_number(member["N"])}</td>'
            f'<td class="{_state_class(member["state"])}">{escape(member["state"])}</td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>barra</th><th>nós</th>"
        f'<th class="num">L [{escape(units.get("length", ""))}]</th>'
        f'<th class="num">N [{escape(units.get("force", ""))}]</th>'
        "<th>estado</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _input_table(model: dict, units: dict) -> str:
    nodes = model.get("nodes") or []
    loads = model.get("loads") or []
    rows = []
    load_by_node: dict[str, list[dict]] = {}
    for load in loads:
        load_by_node.setdefault(load.get("node"), []).append(load)

    for node in nodes:
        applied = load_by_node.get(node.get("id"), [])
        text = (
            "; ".join(
                f"Fx={format_number(item.get('Fx', 0))}, Fy={format_number(item.get('Fy', 0))}"
                for item in applied
            )
            or "—"
        )
        rows.append(
            "<tr>"
            f"<td>{escape(str(node.get('id')))}</td>"
            f'<td class="num">{format_number(node.get("x", 0))}</td>'
            f'<td class="num">{format_number(node.get("y", 0))}</td>'
            f"<td>{escape(str(node.get('support') or 'none'))}</td>"
            f"<td>{escape(text)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>nó</th>"
        f'<th class="num">x [{escape(units.get("length", ""))}]</th>'
        f'<th class="num">y [{escape(units.get("length", ""))}]</th>'
        "<th>apoio</th><th>cargas aplicadas</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )

def _stress_table(solution: dict, units: dict) -> str:
    stress = solution.get("stress") or {}
    entries = stress.get("entries") or []
    if not entries:
        return ""
    rows = []
    for entry in entries:
        rows.append(
            "<tr>"
            f"<td>{escape(entry['id'])}</td>"
            f"<td>{escape(entry['a'])}–{escape(entry['b'])}</td>"
            f'<td class="num">{format_number(entry["N"])}</td>'
            f'<td class="num">{format_number(entry["area"])}</td>'
            f'<td class="num {_state_class(entry["state"])}">{format_number(entry["sigma"])}</td>'
            f'<td class="{_state_class(entry["state"])}">{escape(entry["state"])}</td>'
            "</tr>"
        )
    summary = stress.get("summary") or {}
    critical = summary.get("critical")
    note = ""
    if critical:
        note = (
            f'<p class="note">Barra mais solicitada: <b>{escape(critical["id"])}</b> com '
            f'σ = {format_number(critical["sigma"])} {escape(units.get("stress", ""))}.</p>'
        )
    if stress.get("missing"):
        note += (
            '<p class="note warn">Barras sem área informada (não entram na tabela): '
            + ", ".join(escape(item) for item in stress["missing"])
            + ".</p>"
        )
    return (
        "<table><thead><tr>"
        "<th>barra</th><th>nós</th>"
        f'<th class="num">N [{escape(units.get("force", ""))}]</th>'
        f'<th class="num">A [{escape(units.get("area", ""))}]</th>'
        f'<th class="num"><span class="sigma">σ</span> = N/A [{escape(units.get("stress", ""))}]</th>'
        "<th>estado</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>" + note
    )

def render_report(
    model: dict,
    solution: dict,
    *,
    title: str | None = None,
    palette: str | dict | None = "padrao",
    show_stress: bool = False,
) -> str:
    """Gera o documento HTML completo do relatório."""
    units = solution.get("units") or {"force": "kN", "length": "m"}
    determinacy = solution.get("determinacy") or {}
    checks = solution.get("checks") or {}
    summary = solution.get("summary") or {}
    cross = solution.get("crossCheck") or {}

    heading = title or "Treliça plana — relatório de cálculo"
    svg = render_truss_svg(
        model,
        solution,
        width=880,
        height=520,
        palette=palette,
        show_stress=show_stress,
    )
    stress_html = _stress_table(solution, units)

    passed = checks.get("passed")
    chip = (
        '<span class="chip ok">equilíbrio verificado</span>'
        if passed
        else '<span class="chip bad">equilíbrio NÃO fechou</span>'
    )

    if cross.get("available"):
        if cross.get("passed"):
            cross_text = (
                "conferido pelo método dos nós: diferença máxima "
                f"{format_number(cross.get('maxDifference', 0), 6)} "
                f"{units.get('force', '')} (dentro da tolerância)."
            )
        else:
            cross_text = (
                "ATENÇÃO: divergência de "
                f"{format_number(cross.get('maxDifference', 0), 6)} "
                "em relação ao método dos nós."
            )
    else:
        cross_text = f"método dos nós não aplicável: {cross.get('reason', '—')}"

    zero_force = solution.get("zero_force") or []
    if zero_force:
        zero_items = "".join(
            f"<li><b>{escape(entry['member'])}</b> — {escape(entry.get('reason') or '')}</li>"
            for entry in zero_force
        )
        zero_html = f'<ul class="plain">{zero_items}</ul>'
    else:
        zero_html = '<p class="note">nenhuma barra de força zero neste caso.</p>'

    warnings = solution.get("warnings") or []
    warnings_html = (
        '<ul class="plain">'
        + "".join(f"<li>{escape(item)}</li>" for item in warnings)
        + "</ul>"
        if warnings
        else '<p class="note">nenhum aviso.</p>'
    )

    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(heading)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="bar">
  <div>
    <h1>{escape(heading)}</h1>
    <p class="sub">Módulo Trusses — versão própria do MdSolids · gerado em {stamp}</p>
  </div>
  <div class="actions no-print">
    <button class="primary" onclick="window.print()">Imprimir / salvar PDF</button>
  </div>
</div>

<h2>Modelo</h2>
{_input_table(model, units)}
<div class="meta">
  <span>nós: <b>{determinacy.get('n', '—')}</b></span>
  <span>barras: <b>{determinacy.get('b', '—')}</b></span>
  <span>reações: <b>{determinacy.get('r', '—')}</b></span>
  <span>grau g = b + r − 2n: <b>{determinacy.get('degree', '—')}</b></span>
  <span>classificação: <b>{escape(str(determinacy.get('label', '—')))}</b></span>
  <span>{chip}</span>
</div>
<p class="note">{escape(str(determinacy.get('detail', '')))}</p>

<h2>Diagrama de esforços normais</h2>
<div class="fig">{svg}</div>
<p class="note">Convenção: <b>N &gt; 0 é tração</b> e <b>N &lt; 0 é compressão</b>.
Espessura proporcional ao módulo do esforço. Barras tracejadas em cinza são de força zero.</p>

<h2>Reações de apoio</h2>
{_reactions_table(solution, units)}

<h2>Esforços normais nas barras</h2>
{_members_table(solution, units)}
<div class="meta">
  <span>tração: <b>{summary.get('tension', 0)}</b></span>
  <span>compressão: <b>{summary.get('compression', 0)}</b></span>
  <span>força zero: <b>{summary.get('zero', 0)}</b></span>
  <span>maior |N|: <b>{format_number(summary.get('maxAbsForce', 0))} {escape(units.get('force', ''))}</b></span>
  <span>maior deslocamento: <b>{format_number(summary.get('maxDisplacement', 0), 6)} {escape(units.get('length', ''))}</b></span>
</div>

<h2>Tensões normais (<span class="sigma">σ</span> = N/A)</h2>
{stress_html or '<p class="note">Informe a área da seção de cada barra para obter as tensões normais.</p>'}
<h2>Barras de força zero</h2>
{zero_html}

<h2>Verificações</h2>
<table>
<thead><tr><th>verificação</th><th class="num">valor</th><th>situação</th></tr></thead>
<tbody>
<tr><td>ΣFx (cargas + reações)</td>
    <td class="num">{format_number(checks.get('sumFx', 0), 6)}</td>
    <td>{'ok' if abs(checks.get('sumFx', 0)) < 1e-6 else 'fora'}</td></tr>
<tr><td>ΣFy (cargas + reações)</td>
    <td class="num">{format_number(checks.get('sumFy', 0), 6)}</td>
    <td>{'ok' if abs(checks.get('sumFy', 0)) < 1e-6 else 'fora'}</td></tr>
<tr><td>ΣM na origem</td>
    <td class="num">{format_number(checks.get('sumM', 0), 6)}</td>
    <td>{'ok' if abs(checks.get('sumM', 0)) < 1e-6 else 'fora'}</td></tr>
<tr><td>maior resíduo nodal (nó {escape(str(checks.get('worstNode') or '—'))})</td>
    <td class="num">{format_number(checks.get('maxNodalResidual', 0), 6)}</td>
    <td>{'ok' if abs(checks.get('maxNodalResidual', 0)) < 1e-6 else 'fora'}</td></tr>
</tbody>
</table>
<p class="note">{escape(cross_text)}</p>

<h2>Avisos</h2>
{warnings_html}

<p class="note">Resíduos diferentes de zero na casa de 1e−15 são ruído de ponto
flutuante, não erro de formulação. Os valores de esforço normal foram conferidos
contra o método dos nós, que é um algoritmo independente do método da rigidez.</p>
</body>
</html>
"""
