"""Gera `docs/validacao.md` a partir dos casos em `data/cases/`.

Para cada caso o script roda o solver e o método dos nós, confere o equilíbrio e
escreve a tabela de resultados no documento. É assim que o registro de validação
fica sempre sincronizado com o código — não é escrito à mão.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from app.core.joints import method_of_joints
from app.core.model import parse_truss
from app.core.solver import solve_payload

CASES_DIR = Path("data/cases")
OUT = Path("docs/validacao.md")


def fmt(value: float, decimals: int = 3) -> str:
    rounded = round(float(value), decimals)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.{decimals}f}".replace("-", "−")


def main() -> int:
    records = []
    for path in sorted(CASES_DIR.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["slug"] = path.stem
        records.append(record)

    lines: list[str] = []
    lines.append("# Registro de validação")
    lines.append("")
    lines.append(
        "Documento gerado por `python tools/build_validation.py` a partir de "
        "`data/cases/`. Não editar à mão: rode o script."
    )
    lines.append("")
    lines.append("## Como cada caso é verificado")
    lines.append("")
    lines.append("Cada caso válido passa por seis verificações independentes:")
    lines.append("")
    lines.append("1. **estaticidade** — `g = b + r − 2n` coerente com o esperado;")
    lines.append("2. **esforços normais** — comparados com o gabarito gravado;")
    lines.append("3. **reações de apoio** — comparadas com o gabarito gravado;")
    lines.append("4. **equilíbrio global** — `ΣFx`, `ΣFy`, `ΣM` nulos;")
    lines.append("5. **equilíbrio nodal** — resíduo em cada nó nulo;")
    lines.append(
        "6. **conferência cruzada** — método dos nós (equações de equilíbrio apenas, "
        "sem `EA` e sem deslocamentos) reproduz os mesmos esforços."
    )
    lines.append("")
    lines.append(
        "Os casos de erro verificam que o programa **recusa** com o código esperado, "
        "em vez de devolver número absurdo."
    )
    lines.append("")

    summary_rows: list[str] = []
    detail_blocks: list[str] = []
    failures: list[str] = []

    for record in records:
        slug = record["slug"]
        payload = record["input"]
        out = solve_payload(payload)
        expected = record["expect"]

        if expected["status"] == "error":
            codes = [error["code"] for error in out.get("errors", [])]
            ok = out["status"] == "error" and expected["errorCode"] in codes
            if not ok:
                failures.append(f"{slug}: esperava `{expected['errorCode']}`, obteve {codes}")
            summary_rows.append(
                f"| `{slug}` | {record['name']} | erro esperado: "
                f"`{expected['errorCode']}` | {'✅' if ok else '❌'} |"
            )
            detail_blocks.append(f"### `{slug}` — {record['name']}")
            detail_blocks.append("")
            detail_blocks.append(record.get("description", ""))
            detail_blocks.append("")
            detail_blocks.append(
                "**Resultado:** recusado com código "
                f"`{codes[0] if codes else '—'}` — "
                + (out["errors"][0]["message"] if out.get("errors") else "")
            )
            detail_blocks.append("")
            continue

        checks = out["checks"]
        cross = out["crossCheck"]
        members = {m["id"]: m for m in out["members"]}
        reactions = {r["node"]: r for r in out["reactions"]}

        problems: list[str] = []
        for member_id, value in expected["members"].items():
            if abs(members[member_id]["N"] - value) > expected["tolerance"]:
                problems.append(f"{member_id} fora do gabarito")
        for node_id, comps in expected["reactions"].items():
            for component, value in comps.items():
                if abs(reactions[node_id][component] - value) > expected["tolerance"]:
                    problems.append(f"reação {node_id}.{component} fora do gabarito")
        if not checks["passed"]:
            problems.append("equilíbrio não fechou")

        cross_text = "n/a (hiperestática)"
        if cross.get("available"):
            if not cross.get("passed"):
                problems.append("divergência em relação ao método dos nós")
            cross_text = f"{cross['maxDifference']:.2e}".replace("-", "−")

        if problems:
            failures.append(f"{slug}: " + "; ".join(problems))

        summary_rows.append(
            f"| `{slug}` | {record['name']} | "
            f"{out['determinacy']['label']} (g = {out['determinacy']['degree']}) | "
            f"{'✅' if not problems else '❌'} |"
        )

        detail_blocks.append(f"### `{slug}` — {record['name']}")
        detail_blocks.append("")
        detail_blocks.append(record.get("description", ""))
        detail_blocks.append("")
        det = out["determinacy"]
        detail_blocks.append(
            f"Estaticidade: `b + r = {det['b']} + {det['r']} = {det['b'] + det['r']}` "
            f"versus `2n = {2 * det['n']}` → **{det['label']}**, grau `{det['degree']}`."
        )
        detail_blocks.append("")
        detail_blocks.append("| barra | L | N | estado |")
        detail_blocks.append("| --- | --- | --- | --- |")
        for member in out["members"]:
            detail_blocks.append(
                f"| `{member['id']}` | {fmt(member['length'])} | "
                f"{fmt(member['N'])} | {member['state']} |"
            )
        detail_blocks.append("")
        detail_blocks.append("| apoio | Rx | Ry |")
        detail_blocks.append("| --- | --- | --- |")
        for entry in out["reactions"]:
            components = entry.get("components") or []
            rx = fmt(entry["Rx"]) if "ux" in components else "—"
            ry = fmt(entry["Ry"]) if "uy" in components else "—"
            detail_blocks.append(f"| `{entry['node']}` | {rx} | {ry} |")
        detail_blocks.append("")
        detail_blocks.append(
            f"Verificações: `ΣFx = {checks['sumFx']:.2e}`, "
            f"`ΣFy = {checks['sumFy']:.2e}`, `ΣM = {checks['sumM']:.2e}`, "
            f"resíduo nodal máximo `{checks['maxNodalResidual']:.2e}` → "
            f"**{'equilíbrio verificado' if checks['passed'] else 'FALHOU'}**."
        )
        detail_blocks.append("")
        detail_blocks.append(f"Conferência pelo método dos nós: diferença máxima `{cross_text}`.")
        if out["zero_force"]:
            names = ", ".join(f"`{entry['member']}`" for entry in out["zero_force"])
            detail_blocks.append("")
            detail_blocks.append(f"Barras de força zero: {names}.")
        detail_blocks.append("")

    lines.append("## Resumo da bateria")
    lines.append("")
    lines.append("| caso | descrição | classificação | situação |")
    lines.append("| --- | --- | --- | --- |")
    lines.extend(summary_rows)
    lines.append("")

    lines.append("## Detalhe por caso")
    lines.append("")
    lines.extend(detail_blocks)

    lines.append("## Como reproduzir")
    lines.append("")
    lines.append("```powershell")
    lines.append("python -m pytest -q                 # toda a suíte")
    lines.append("python tools/build_cases.py         # regera os gabaritos e revalida")
    lines.append("python tools/build_validation.py    # regera este documento")
    lines.append("```")
    lines.append("")

    if failures:
        lines.append("## Falhas")
        lines.append("")
        for failure in failures:
            lines.append(f"- {failure}")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"escrito {OUT} ({len(records)} casos)")

    if failures:
        print("FALHAS:")
        for failure in failures:
            print(" -", failure)
        return 1
    print("todos os casos conferidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
