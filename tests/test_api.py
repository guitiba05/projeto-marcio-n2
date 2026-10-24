"""API HTTP: contrato das rotas, códigos de erro e integridade das respostas."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.api.server import PRESETS, app  # noqa: E402

client = TestClient(app)

TRIANGLE = {
    "units": {"force": "kN", "length": "m"},
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


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["presets"] == len(PRESETS) == 12


def test_lista_de_presets() -> None:
    response = client.get("/api/presets")
    assert response.status_code == 200
    presets = response.json()["presets"]
    assert len(presets) == 12
    for preset in presets:
        assert preset["slug"]
        assert preset["name"]
        # o seletor não precisa carregar o modelo inteiro
        assert "input" not in preset


def test_preset_individual() -> None:
    response = client.get("/api/presets/01-triangulo")
    assert response.status_code == 200
    preset = response.json()
    assert preset["slug"] == "01-triangulo"
    assert len(preset["input"]["nodes"]) == 3
    assert len(preset["input"]["members"]) == 3


def test_preset_inexistente() -> None:
    response = client.get("/api/presets/nao-existe")
    assert response.status_code == 404


@pytest.mark.parametrize("slug", [preset["slug"] for preset in PRESETS])
def test_todos_os_presets_sao_aceitos_pela_api(slug: str) -> None:
    preset = client.get(f"/api/presets/{slug}").json()
    response = client.post("/api/solve", json=preset["input"])
    assert response.status_code == 200
    body = response.json()
    # casos marcados como erro precisam voltar como erro; os demais como ok
    if preset.get("expectError"):
        assert body["status"] == "error"
        assert body["errors"][0]["code"] == preset["expectError"]
    else:
        assert body["status"] == "ok", body.get("errors")


def test_solve_contrato_completo() -> None:
    response = client.post("/api/solve", json=TRIANGLE)
    assert response.status_code == 200
    body = response.json()

    for key in (
        "status",
        "units",
        "determinacy",
        "reactions",
        "members",
        "displacements",
        "checks",
        "crossCheck",
        "zero_force",
        "summary",
        "warnings",
        "errors",
        "matrix",
    ):
        assert key in body, f"campo ausente na resposta: {key}"

    assert body["status"] == "ok"
    assert body["determinacy"]["label"] == "isostática"
    assert body["determinacy"]["degree"] == 0
    assert body["checks"]["passed"] is True
    assert body["crossCheck"]["available"] is True
    assert body["crossCheck"]["passed"] is True
    assert body["errors"] == []

    forces = {member["id"]: member["N"] for member in body["members"]}
    assert forces["AB"] == pytest.approx(10 / 3, abs=1e-6)
    assert forces["AC"] == pytest.approx(-5 * 13 ** 0.5 / 3, abs=1e-6)


def test_solve_erro_de_modelo_volta_como_200() -> None:
    """Erro de domínio é uma resposta válida do ponto de vista HTTP."""
    bad = json.loads(json.dumps(TRIANGLE))
    bad["nodes"][1]["support"] = "none"
    response = client.post("/api/solve", json=bad)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["errors"][0]["code"] == "hypostatic"
    assert body["members"] == []


def test_solve_corpo_invalido() -> None:
    response = client.post("/api/solve", json={"nodes": [], "members": []})
    assert response.status_code == 200
    assert response.json()["status"] == "error"


def test_figure_devolve_svg() -> None:
    response = client.post("/api/figure", json={"model": TRIANGLE, "width": 800, "height": 480})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    svg = response.text
    assert svg.startswith("<svg")
    assert 'viewBox="0 0 800 480"' in svg
    assert "tração" in svg and "compressão" in svg
    # os valores dos esforços aparecem rotulados
    assert "3.33" in svg or "3,33" in svg


def test_figure_sem_solucao_ainda_desenha() -> None:
    bad = json.loads(json.dumps(TRIANGLE))
    bad["nodes"][1]["support"] = "none"
    response = client.post("/api/figure", json={"model": bad})
    assert response.status_code == 200
    assert response.text.startswith("<svg")


def test_relatorio_html() -> None:
    response = client.post("/api/report", json={"model": TRIANGLE, "title": "Caso de teste"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "Caso de teste" in html
    assert "Esforços normais" in html
    assert "Reações de apoio" in html
    assert "Verificações" in html
    assert "método dos nós" in html
    assert "<svg" in html
    # precisa ser imprimível
    assert "@media print" in html


def test_relatorio_recusa_modelo_invalido() -> None:
    response = client.post("/api/report", json={"model": {"nodes": [], "members": []}})
    assert response.status_code == 200
    assert "Não foi possível gerar o relatório" in response.text


def test_interface_web_na_raiz() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Treliças" in response.text
    assert "js/app.js" in response.text


def test_arquivos_estaticos_da_interface() -> None:
    for path in ("/css/app.css", "/js/state.js", "/js/editor.js", "/js/results.js", "/js/app.js"):
        response = client.get(path)
        assert response.status_code == 200, f"não encontrado: {path}"
        assert len(response.text) > 100


# ------------------------------------------------------- tensão normal (σ = N/A)
TRIANGLE_AREAS = json.loads(json.dumps(TRIANGLE))
for _member in TRIANGLE_AREAS["members"]:
    _member["area"] = 100.0


def test_stress_modo_tensao_por_area() -> None:
    response = client.post("/api/stress", json={"model": TRIANGLE_AREAS, "mode": "stress"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "stress"
    assert body["units"]["area"] == "mm²"
    assert body["units"]["stress"] == "MPa"

    by_id = {entry["id"]: entry for entry in body["stress"]["entries"]}
    assert by_id["AB"]["sigma"] == pytest.approx(10 / 3 * 1000 / 100, abs=1e-6)
    assert by_id["AB"]["state"] == "tração"
    assert by_id["AC"]["sigma"] < 0


def test_stress_modo_area_requerida() -> None:
    response = client.post(
        "/api/stress",
        json={"model": TRIANGLE, "mode": "area", "allowable": 50.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "area"

    by_id = {entry["id"]: entry for entry in body["stress"]["entries"]}
    assert by_id["AB"]["requiredArea"] == pytest.approx(10 / 3 * 1000 / 50, abs=1e-6)
    assert body["stress"]["summary"]["governing"]["id"] in {"AC", "BC"}


def test_stress_modo_area_sem_tensao_admissivel() -> None:
    response = client.post("/api/stress", json={"model": TRIANGLE, "mode": "area"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["errors"][0]["code"] == "bad_allowable"


def test_stress_modo_invalido_responde_400() -> None:
    response = client.post("/api/stress", json={"model": TRIANGLE, "mode": "torsao"})
    assert response.status_code == 400
    assert "modo inválido" in response.json()["detail"]


@pytest.mark.parametrize("bad_area", [0, -50])
def test_stress_recusa_area_nula_ou_negativa(bad_area: float) -> None:
    bad = json.loads(json.dumps(TRIANGLE))
    bad["members"][0]["area"] = bad_area
    response = client.post("/api/stress", json={"model": bad, "mode": "stress"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["errors"][0]["code"] == "invalid_input"


def test_stress_modelo_invalido() -> None:
    response = client.post("/api/stress", json={"model": {"nodes": [], "members": []}})
    assert response.status_code == 200
    assert response.json()["status"] == "error"


def test_solve_devolve_bloco_de_tensao() -> None:
    body = client.post("/api/solve", json=TRIANGLE_AREAS).json()
    assert body["status"] == "ok"
    assert body["units"]["area"] == "mm²"
    assert body["stress"]["available"] is True
    members = {member["id"]: member for member in body["members"]}
    assert members["AB"]["area"] == pytest.approx(100.0)


# ------------------------------------------------------------------- paletas
def test_figure_paleta_mdsolids() -> None:
    response = client.post(
        "/api/figure",
        json={"model": TRIANGLE, "width": 800, "height": 480, "palette": "mdsolids"},
    )
    assert response.status_code == 200
    svg = response.text
    assert "#00b8d4" in svg  # tração (ciano)
    assert "#b8860b" in svg  # compressão (ouro)
    assert "#d81b9b" in svg  # força zero (magenta)
    # a legenda usa as cores da paleta escolhida
    assert "tração" in svg and "compressão" in svg


def test_figure_paleta_padrao_diferente_da_mdsolids() -> None:
    response = client.post("/api/figure", json={"model": TRIANGLE, "palette": "padrao"})
    svg = response.text
    assert "#2563eb" in svg or "#dc2626" in svg
    assert "#00b8d4" not in svg


def test_figure_com_rotulo_de_tensao() -> None:
    response = client.post(
        "/api/figure",
        json={"model": TRIANGLE_AREAS, "showStress": True},
    )
    assert response.status_code == 200
    assert "σ" in response.text


def test_figure_paleta_inexistente_cai_na_padrao() -> None:
    response = client.post("/api/figure", json={"model": TRIANGLE, "palette": "neon"})
    assert response.status_code == 200
    assert response.text.startswith("<svg")


# ---------------------------------------------------------------- relatório
def test_relatorio_inclui_tabela_de_tensoes() -> None:
    response = client.post(
        "/api/report",
        json={"model": TRIANGLE_AREAS, "title": "Caso com áreas"},
    )
    assert response.status_code == 200
    html = response.text
    assert "Tensões normais" in html
    assert "33.333" in html or "33,333" in html
    # o sigma precisa continuar minúsculo (não virar Σ de somatório)
    assert 'class="sigma"' in html
    assert "Σ = N/A" not in html


def test_relatorio_sem_areas_pede_a_area_em_vez_de_inventar_tensoes() -> None:
    response = client.post("/api/report", json={"model": TRIANGLE})
    assert response.status_code == 200
    html = response.text
    # a seção existe, mas apenas com a instrução — nenhuma tensão é inventada
    assert "Tensões normais" in html
    assert "Informe a área da seção de cada barra" in html
    assert "33.333" not in html


# ------------------------------------------------------- interface (estático)
def test_interface_tem_controles_de_grade_e_tensao() -> None:
    html = client.get("/").text
    for element_id in (
        'id="grid-dx"',
        'id="grid-dy"',
        'id="grid-nx"',
        'id="grid-ny"',
        'id="btn-grid"',
        'id="unit-area"',
        'id="unit-stress"',
        'id="palette-select"',
        'id="stress-mode"',
        'id="stress-allowable"',
        'id="stress-body"',
    ):
        assert element_id in html, f"controle ausente na interface: {element_id}"


def test_interface_protege_o_simbolo_sigma() -> None:
    """`text-transform: uppercase` converte σ (U+03C3) em Σ (U+03A3)."""
    index = client.get("/").text
    assert 'class="sigma"' in index
    css = client.get("/css/app.css").text
    assert ".sigma, .unit, .math { text-transform: none; }" in css
    results = client.get("/js/results.js").text
    assert 'class="sigma"' in results


def test_interface_cria_barra_por_arraste() -> None:
    """O editor precisa ter a linha fantasma e o encaixe na grade."""
    editor = client.get("/js/editor.js").text
    assert "rubber" in editor
    assert "setGrid" in editor
    assert "nearestNode" in editor
    assert "member-line pending" in editor
