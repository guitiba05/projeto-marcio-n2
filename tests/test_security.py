"""Regressão dos achados da auditoria (injeção, 500 evitáveis e falso mecanismo).

Cada teste aqui reproduz um defeito que foi observado antes da correção:
* ids/unidades vindos de JSON importado não podem virar HTML/SVG executável;
* a paleta aceita apenas cores hexadecimais, nunca atributos;
* `/api/figure` não devolve 500 para dimensões ou modelos inválidos;
* rigidez muito contrastada não é mecanismo: `cond(K_ff)` separa os dois casos.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.api.server import app  # noqa: E402
from app.core.solver import solve_payload  # noqa: E402
from app.render.svg import PALETTES, render_truss_svg  # noqa: E402

client = TestClient(app)

TRIANGLE = {
    "nodes": [
        {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
        {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
        {"id": "C", "x": 2.0, "y": 3.0, "support": "none"},
    ],
    "members": [
        {"id": "AB", "a": "A", "b": "B", "EA": 1.0},
        {"id": "AC", "a": "A", "b": "C", "EA": 1.0},
        {"id": "BC", "a": "B", "b": "C", "EA": 1.0},
    ],
    "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
}


def clone(model: dict) -> dict:
    return json.loads(json.dumps(model))


# ------------------------------------------------------------- XSS / injeção
def test_relatorio_de_erro_escapa_o_id_do_no() -> None:
    """O id hostil aparece na mensagem de erro — precisa vir escapado."""
    evil = '<img src=x onerror=alert(1)>'
    model = {
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
        ],
        "members": [{"id": "AB", "a": "A", "b": "B"}],
        "loads": [{"node": evil, "Fx": 0.0, "Fy": -10.0}],
    }
    response = client.post("/api/report", json={"model": model})
    assert response.status_code == 200
    assert evil not in response.text          # nada de HTML cru
    assert "&lt;img" in response.text         # aparece como texto
    assert "Não foi possível gerar o relatório" in response.text


def test_relatorio_valido_escapa_titulo_e_ids() -> None:
    model = clone(TRIANGLE)
    model["nodes"][2]["id"] = "<b>C</b>"
    for member in model["members"]:
        if member["a"] == "C":
            member["a"] = "<b>C</b>"
        if member["b"] == "C":
            member["b"] = "<b>C</b>"
    response = client.post("/api/report", json={"model": model, "title": "<script>x</script>"})
    assert response.status_code == 200
    assert "<script>x</script>" not in response.text
    assert "<b>C</b>" not in response.text


def test_palette_como_dict_nao_injeta_atributos() -> None:
    response = client.post(
        "/api/figure",
        json={"model": TRIANGLE, "palette": {"tension": 'red" onload="alert(1)'}},
    )
    assert response.status_code == 200
    assert "onload" not in response.text
    assert "alert(" not in response.text


def test_palette_dict_com_cor_valida_e_aplicada() -> None:
    response = client.post(
        "/api/figure", json={"model": TRIANGLE, "palette": {"tension": "#00b8d4"}}
    )
    assert response.status_code == 200
    assert "#00b8d4" in response.text


def test_palette_com_chave_desconhecida_e_ignorada() -> None:
    svg = render_truss_svg(
        TRIANGLE,
        None,
        palette={"background": "#000000", "tension": "#2563eb"},
    )
    assert 'fill="#000000"' not in svg


# ------------------------------------------------------- 500 evitáveis (API)
def test_figure_com_largura_nao_numerica_nao_quebra() -> None:
    response = client.post("/api/figure", json={"model": TRIANGLE, "width": "abc"})
    assert response.status_code == 200
    assert response.text.startswith("<svg")
    assert 'viewBox="0 0 880 520"' in response.text  # cai no padrão


def test_figure_com_dimensoes_fora_da_faixa_sao_limitadas() -> None:
    response = client.post("/api/figure", json={"model": TRIANGLE, "width": -5, "height": 10**9})
    assert response.status_code == 200
    assert 'viewBox="0 0 16 4000"' in response.text


def test_figure_com_modelo_invalido_nao_quebra() -> None:
    bad = clone(TRIANGLE)
    bad["nodes"][0]["x"] = "abc"
    response = client.post("/api/figure", json={"model": bad})
    assert response.status_code == 200
    assert response.text.startswith("<svg")
    assert 'aria-label="modelo inválido"' in response.text


def test_figure_sem_solucao_continua_desenhando() -> None:
    """Modelo válido mas hipostático: desenha a geometria (não é o caso de erro)."""
    bad = clone(TRIANGLE)
    bad["nodes"][1]["support"] = "none"
    response = client.post("/api/figure", json={"model": bad})
    assert response.status_code == 200
    assert response.text.startswith("<svg")
    assert 'aria-label="modelo inválido"' not in response.text


def test_figure_com_id_hostil_escapa_no_svg() -> None:
    model = clone(TRIANGLE)
    model["nodes"][0]["id"] = '<script>alert(1)</script>'
    model["members"][0]["a"] = '<script>alert(1)</script>'
    model["members"][1]["a"] = '<script>alert(1)</script>'
    response = client.post("/api/figure", json={"model": model})
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text


# ------------------------------------------------------ falso mecanismo
@pytest.mark.parametrize("ea_bottom", [1e-2, 1e-4, 1e-6, 1e-8])
def test_rigidez_contrastada_nao_e_mecanismo(ea_bottom: float) -> None:
    """Treliça isostática e estável com EA muito contrastado tem de resolver.

    Dois critérios errados recusavam estes casos: `lambda_min <= 1e-10 *
    lambda_max` e, depois, `cond > 1e14`. Ambos medem condicionamento, não
    estabilidade. O gate correto é a **deficiência de posto**: aqui o posto é
    cheio (3/3) mesmo com `cond ≈ 1e14`.
    """
    model = clone(TRIANGLE)
    model["members"][0]["EA"] = ea_bottom
    model["members"][1]["EA"] = 1e6
    model["members"][2]["EA"] = 1e6

    solution = solve_payload(model)
    assert solution["status"] == "ok", solution.get("errors")
    forces = {member["id"]: member["N"] for member in solution["members"]}
    # Isostática: o esforço não depende de EA, então o gabarito continua valendo.
    # A tolerância acompanha o condicionamento: em contraste de 1e14 (EA=1e-8)
    # A tolerância acompanha o condicionamento: em contraste de 1e14 (EA=1e-8)
    # o resultado perde dígitos significativos e fica ~0,4% fora — por isso o
    # programa emite o aviso de "mal condicionada".
    tolerance = 1e-3 if ea_bottom >= 1e-6 else 5e-2
    assert forces["AB"] == pytest.approx(10 / 3, abs=tolerance)
    assert forces["AC"] == pytest.approx(-5 * 13**0.5 / 3, abs=tolerance)



def test_gate_de_mecanismo_e_deficiencia_de_posto() -> None:
    """O gate distingue posto deficiente de simples mau condicionamento."""
    import numpy as np

    from app.core.stiffness import _rank_analysis

    assert _rank_analysis(np.zeros((0, 0)))[0] is False       # nada a resolver
    assert _rank_analysis(np.eye(3))[0] is False              # cond = 1
    # mal condicionada, mas posto cheio: resolve (apenas avisa)
    for scale in (1e-6, 1e-9, 1e-12, 1e-15):
        singular, cond = _rank_analysis(np.diag([1.0, scale, scale]))
        assert singular is False, scale
        assert cond >= 1e6
    # posto deficiente: recusa
    assert _rank_analysis(np.array([[1.0, 1.0], [1.0, 1.0]]))[0] is True
    assert _rank_analysis(np.array([[1.0, 0.0], [0.0, 0.0]]))[0] is True


def test_condicionamento_alto_gera_aviso_sem_recusar() -> None:
    """Mal condicionado: entrega o resultado, mas avisa explicitamente."""
    model = clone(TRIANGLE)
    model["members"][0]["EA"] = 1e-8
    model["members"][1]["EA"] = 1e6
    model["members"][2]["EA"] = 1e6
    solution = solve_payload(model)
    assert solution["status"] == "ok"
    assert any("mal condicionada" in warning for warning in solution["warnings"])


def test_rigidez_contrastada_moderada_fecha_equilibrio() -> None:
    model = clone(TRIANGLE)
    model["members"][0]["EA"] = 1e-4
    model["members"][1]["EA"] = 1e6
    model["members"][2]["EA"] = 1e6
    solution = solve_payload(model)
    assert solution["status"] == "ok"
    assert solution["checks"]["passed"] is True
    # O método dos nós (exato por equilíbrio) continua concordando com a rigidez.
    # A tolerância do crossCheck é ~6e-7 kN; neste regime de condicionamento o
    # resíduo fica na casa de 1e-6 kN, então comparamos o valor, não a bandeira.
    assert solution["crossCheck"]["available"] is True
    assert solution["crossCheck"]["maxDifference"] < 1e-4


def test_mecanismo_real_continua_sendo_detectado() -> None:
    """Arco de três dobradiças colineares: g = 0, mas há mecanismo interno."""
    model = {
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "pin"},
            {"id": "C", "x": 2.0, "y": 0.0, "support": "none"},
            {"id": "D", "x": 0.0, "y": 2.0, "support": "none"},
            {"id": "E", "x": 4.0, "y": 2.0, "support": "none"},
        ],
        "members": [
            {"id": "AC", "a": "A", "b": "C", "EA": 1000.0},
            {"id": "AD", "a": "A", "b": "D", "EA": 1000.0},
            {"id": "CD", "a": "C", "b": "D", "EA": 1000.0},
            {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            {"id": "BE", "a": "B", "b": "E", "EA": 1000.0},
            {"id": "CE", "a": "C", "b": "E", "EA": 1000.0},
        ],
        "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
    }
    solution = solve_payload(model)
    assert solution["status"] == "error"
    assert solution["errors"][0]["code"] == "mechanism"


def test_caso_10_mecanismo_continua_recusado() -> None:
    preset = client.get("/api/presets/10-mecanismo").json()
    solution = client.post("/api/solve", json=preset["input"]).json()
    assert solution["status"] == "error"
    assert solution["errors"][0]["code"] == "mechanism"



# ------------------------------------------- attribute breakout (todos os sinks)
PAYLOADS = [
    '"><script>alert(1)</script>',
    '" onload="alert(1)',
    "' onmouseover='alert(1)",
    '<svg onload=alert(1)>',
    '</text><script>alert(1)</script>',
]


@pytest.mark.parametrize("payload", PAYLOADS)
def test_ids_hostis_nao_quebram_atributo_no_svg(payload: str) -> None:
    """Sink de atributo SVG: o payload vira **texto**, nunca marcação.

    A verificação usa um parser XML de verdade em vez de busca textual: o id
    hostil pode (e deve) aparecer como conteúdo de `<text>`, escapado. O que não
    pode existir é atributo de evento ou elemento `<script>`.
    """
    from xml.etree import ElementTree

    model = clone(TRIANGLE)
    model["nodes"][0]["id"] = payload
    model["members"][0]["a"] = payload
    model["members"][1]["a"] = payload
    response = client.post("/api/figure", json={"model": model})
    assert response.status_code == 200
    text = response.text

    assert payload not in text          # o valor cru nunca aparece
    assert "<script" not in text

    root = ElementTree.fromstring(text)  # SVG bem-formado
    for element in root.iter():
        assert not element.tag.endswith("script")
        for name in element.attrib:
            assert not name.lower().startswith("on"), f"atributo de evento: {name}"
    # o id hostil sobrevive como TEXTO, não como marcação
    labels = [node.text for node in root.iter() if node.text]
    assert any(payload == label for label in labels)


@pytest.mark.parametrize("payload", PAYLOADS)
def test_ids_hostis_nao_quebram_o_relatorio(payload: str) -> None:
    """Sink de HTML: tabelas, título e mensagens de erro."""
    model = clone(TRIANGLE)
    model["nodes"][2]["id"] = payload
    for member in model["members"]:
        if member["a"] == "C":
            member["a"] = payload
        if member["b"] == "C":
            member["b"] = payload
    response = client.post("/api/report", json={"model": model, "title": payload})
    assert response.status_code == 200
    text = response.text
    assert "<script" not in text
    assert "onmouseover" not in text
    assert payload not in text


@pytest.mark.parametrize("payload", PAYLOADS)
def test_unidades_hostis_nao_injetam_marcacao(payload: str) -> None:
    """Unidade inválida é recusada antes de chegar a HTML/SVG.

    A mensagem de erro *pode* citar o valor recebido (é texto de diagnóstico em
    JSON); o que não pode haver é marcação executável na saída HTML.
    """
    model = clone(TRIANGLE)
    model["units"] = {"force": payload, "length": "m"}
    solve = client.post("/api/solve", json=model).json()
    assert solve["status"] == "error"
    assert solve["errors"][0]["code"] == "bad_units"

    report = client.post("/api/report", json={"model": model})
    assert report.status_code == 200
    assert "<script" not in report.text
    assert payload not in report.text
    # o relatório de erro continua sendo HTML bem-formado com o valor escapado
    assert "&lt;" in report.text or "unidade" in report.text


@pytest.mark.parametrize("payload", PAYLOADS)
def test_editor_nao_interpola_payload_em_atributo(payload: str) -> None:
    """O editor precisa escapar ids/unidades em atributo e em conteúdo."""
    source = client.get("/js/editor.js").text
    # nenhuma interpolação crua de id/unidade sobrevive no template
    for unsafe in (
        'data-member="${member.id}"',
        'data-node="${node.id}"',
        "${node.id}</text>",
        "${member.a}",
        "${units.length}]",
        "${units.force}]",
        "${units.area}]",
    ):
        assert unsafe not in source, f"interpolação crua: {unsafe}"

# ---------------------------------------------------------- editor (estático)
def test_editor_escapa_ids_e_unidades_no_html() -> None:
    """Guarda de regressão: o editor não pode interpolar ids crus no innerHTML."""
    source = client.get("/js/editor.js").text
    assert "const esc = (value)" in source
    for unsafe in (
        'data-member="${member.id}"',
        'data-node="${node.id}"',
        "${node.id}</text>",
        "<h3>Nó ${node.id}</h3>",
        "<h3>Barra ${member.id}</h3>",
        "${member.a} — ${member.b}",
    ):
        assert unsafe not in source, f"interpolação crua de volta: {unsafe}"
    for safe in ('data-member="${esc(member.id)}"', 'data-node="${esc(node.id)}"'):
        assert safe in source


# ------------------------------------------------------ contraste (WCAG AA)
def _luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(color: str, background: str = "#ffffff") -> float:
    first, second = _luminance(color), _luminance(background)
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def test_cores_de_texto_da_paleta_padrao_tem_contraste_aa() -> None:
    for key in ("tension", "compression", "zero"):
        assert _contrast(PALETTES["padrao"][key]) >= 4.5, key


def test_mdsolids_barras_fieis_e_texto_legivel() -> None:
    """As barras guardam as cores exatas do original; o texto usa variante escura."""
    palette = PALETTES["mdsolids"]
    assert palette["tension"] == "#00b8d4"
    assert palette["compression"] == "#b8860b"
    assert palette["zero"] == "#d81b9b"
    for key in ("tensionText", "compressionText", "zeroText"):
        assert _contrast(palette[key]) >= 4.5, key


# ------------------------------------------- robustez apontada na revisão
def test_figure_com_dimensao_infinita_nao_quebra() -> None:
    """JSON `1e999` é lido como `inf`; `int(inf)` levanta OverflowError."""
    body = json.dumps({"model": TRIANGLE}).replace(
        '"model"', '"width": 1e999, "height": -1e999, "model"'
    )
    response = client.post(
        "/api/figure", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.text.startswith("<svg")
    assert 'viewBox="0 0 880 520"' in response.text


def test_flags_booleanas_sao_interpretadas_corretamente() -> None:
    """`bool("false")` seria `True`; o valor textual precisa ser respeitado."""
    model = clone(TRIANGLE)
    for member in model["members"]:
        member["area"] = 100.0
    ligado = client.post("/api/figure", json={"model": model, "showStress": "true"})
    desligado = client.post("/api/figure", json={"model": model, "showStress": "false"})
    assert ligado.status_code == desligado.status_code == 200
    assert "σ" in ligado.text
    assert "σ" not in desligado.text


def test_modelo_grande_demais_e_recusado_sem_travar() -> None:
    nodes = [{"id": f"N{i}", "x": float(i), "y": 0.0, "support": "none"} for i in range(500)]
    nodes[0]["support"] = "pin"
    nodes[1]["support"] = "roller"
    members = [{"id": f"M{i}", "a": f"N{i}", "b": f"N{i + 1}"} for i in range(499)]
    model = {"nodes": nodes, "members": members, "loads": []}
    solution = client.post("/api/solve", json=model).json()
    assert solution["status"] == "error"
    assert solution["errors"][0]["code"] == "too_large"


def test_conferencia_divergente_gera_aviso_explicito() -> None:
    """Rigidez muito contrastada: resolve, mas o aviso não pode ficar implícito."""
    model = clone(TRIANGLE)
    model["members"][0]["EA"] = 1e-4
    model["members"][1]["EA"] = 1e6
    model["members"][2]["EA"] = 1e6
    solution = solve_payload(model)
    assert solution["status"] == "ok"
    assert solution["crossCheck"]["passed"] is False
    assert any("método dos nós divergiu" in warning for warning in solution["warnings"])


def test_mecanismo_em_trelica_colinear_e_recusado() -> None:
    """Nós colineares: a mensagem precisa apontar os GDL candidatos."""
    from app.core.errors import MechanismError
    from app.core.model import parse_truss
    from app.core.stiffness import analyze

    model = {
        "nodes": [
            {"id": "A", "x": 0.0, "y": 0.0, "support": "pin"},
            {"id": "B", "x": 4.0, "y": 0.0, "support": "roller"},
            {"id": "C", "x": 2.0, "y": 0.0, "support": "none"},
        ],
        "members": [
            {"id": "AB", "a": "A", "b": "B", "EA": 1000.0},
            {"id": "BC", "a": "B", "b": "C", "EA": 1000.0},
            {"id": "CA", "a": "C", "b": "A", "EA": 1000.0},
        ],
        "loads": [{"node": "C", "Fx": 0.0, "Fy": -10.0}],
    }
    truss = parse_truss(model)
    try:
        analyze(truss)
    except MechanismError as exc:
        assert "GDL" in exc.message
    else:  # pragma: no cover - a treliça é colinear e instável
        raise AssertionError("esperava MechanismError")
