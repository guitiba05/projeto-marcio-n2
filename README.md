# Projeto Márcio — N2

Versão própria do módulo **Trusses (Treliças)** do software
[MdSolids](https://static-archives.git-pages.mst.edu/mdsolids/), desenvolvida como
trabalho da avaliação N2 (CEFSA).

O programa recebe uma treliça plana (nós, barras, apoios e cargas nodais) e
devolve reações de apoio, esforços normais em todas as barras com classificação
tração/compressão, barras de força zero, deslocamentos, **tensão normal
(σ = N/A) e área requerida** para uma tensão admissível, além das verificações
de equilíbrio — com conferência por um método independente.

## Como rodar

```powershell
pip install -r requirements.txt
python serve.py
```

Abre a interface em <http://127.0.0.1:8000/>. Requisitos: Python 3.11+.

Opções: `python serve.py --port 8123 --no-browser`.
A documentação automática da API fica em `/docs`.

## O que o programa faz

| Funcionalidade | Onde |
| --- | --- |
| Entrada de geometria: **grade por espaçamento e nº de intervalos**, nós e **barras por arraste** | editor + JSON |
| Apoios: articulação fixa, roleto vertical e horizontal, livre | inspetor do nó |
| Cargas nodais (Fx, Fy) | inspetor do nó |
| Estaticidade `b + r` vs `2n` (iso / hipo / hiperestática) | painel de resultados |
| Reações de apoio por equilíbrio global | tabela de reações |
| Esforços normais em todas as barras (método matricial da rigidez) | tabela + diagrama |
| Classificação automática tração / compressão / força zero | tabela + cores no diagrama |
| Barras de força zero com a regra geométrica justificada | bloco "força zero" |
| **Tensão normal σ = N/A** por barra (área informada no inspetor) | painel "tensões normais" |
| **Área requerida** para uma tensão admissível (`A = abs(N)/σ_adm`) | painel "tensões normais" |
| **Paleta MdSolids opcional** (tração ciano, compressão ouro, força zero magenta) | seletor "Paleta" |
| Deslocamentos nodais | resumo + diagrama opcional |
| Verificações: `ΣFx`, `ΣFy`, `ΣM`, resíduo nodal | bloco "verificações" |
| Conferência independente pelo método dos nós | bloco "verificações" |
| Casos de erro: hipostática, mecanismo, entrada inválida | mensagens no painel |
| Relatório imprimível (salvar em PDF) | botão "Relatório" |
| Importar / exportar JSON | barra superior |
| 12 casos prontos (incluindo 2 casos de erro) | seletor "Caso pronto" |
| Operação por teclado no quadro (setas + Enter) e foco visível | editor |
| Paleta padrão com contraste WCAG AA no texto | diagrama + relatório |

Convenção fixada em todo o projeto: **N > 0 é tração, N < 0 é compressão**.

## Estrutura

```
app/
  core/          domínio puro (sem I/O) — onde mora o cálculo
    model.py         nós, barras, cargas, validação da entrada
    determinacy.py   g = b + r − 2n
    stiffness.py     matriz de rigidez, solução, reações, esforços normais
    joints.py        método dos nós (conferência independente)
    equilibrium.py   verificações de equilíbrio global e nodal
    zero_force.py    regras R1/R2/R3 de barras de força zero
    stress.py        tensão normal σ = N/A e área requerida
    units.py         conversão (interno sempre kN, m, N e mm²)
    solver.py        monta o contrato de saída
  api/
    server.py        rotas FastAPI (solve, stress, figure, report, presets)
    report.py        relatório HTML imprimível
  render/
    svg.py           diagrama da treliça em SVG (+ SVG de erro e paletas)
  web/               interface (HTML + CSS + JS, sem framework)
data/cases/          12 casos com gabarito (fonte única de testes e presets)
tests/               suíte pytest (unitários, integração, adversariais, segurança, E2E)
tools/               geradores (casos, validação, relatórios)
docs/                enunciado, escopo, plano, teoria, validação, paridade MdSolids
docs/apresentacao/   slides interativos e roteiro de defesa
docs/relatorios/     12 relatórios HTML de contingência (gerados)
```

**Regra de ouro:** nenhuma conta de engenharia em JavaScript. O front apenas
edita e desenha; quem calcula é `app/core`, em Python. Assim existe um único
lugar para auditar e testar.

## Testes

```powershell
python -m pytest -q
```

A suíte (474 testes) cobre: os 12 casos da bateria (esforços, reações,
estaticidade, equilíbrio, conferência cruzada e barras de força zero), validação
de entrada, propriedades da matriz de rigidez, independência de `EA` na
isostática e dependência na hiperestática, unidades, regras de força zero, a API
HTTP, casos adversariais (geometria extrema, mecanismos, entradas hostis) e
regressões de segurança (escape de HTML/SVG, paleta, dimensões inválidas).

Ferramentas auxiliares:

```powershell
python tools/build_cases.py        # regera os gabaritos e revalida os 12 casos
python tools/build_validation.py   # regera docs/validacao.md
python tools/build_reports.py      # regera docs/relatorios/*.html
```

## Rotas da API

| Rota | Para que serve |
| --- | --- |
| `POST /api/solve` | esforços, reações, verificações, deslocamentos e o bloco de tensão |
| `POST /api/stress` | `mode="stress"` (σ = N/A com a área de cada barra) ou `mode="area"` (área requerida para uma tensão admissível) |
| `POST /api/figure` | diagrama SVG; aceita `palette` (`padrao` \| `mdsolids`) e `showStress` |
| `POST /api/report` | relatório HTML imprimível, com a tabela de tensões quando há áreas |
| `GET /api/presets` | lista dos 12 casos prontos |
| `GET /api/health` | estado do serviço |

## Documentação

- [`docs/enunciado.md`](docs/enunciado.md) — texto original da proposta
- [`docs/plano.md`](docs/plano.md) — plano de execução (fases, arquitetura, riscos)
- [`docs/escopo-tecnico.md`](docs/escopo-tecnico.md) — escopo funcional e base teórica
- [`docs/teoria.md`](docs/teoria.md) — **base teórica para a apresentação (4,0 pts)**
- [`docs/validacao.md`](docs/validacao.md) — registro de validação dos 12 casos
- [`docs/mdsolids-truss.md`](docs/mdsolids-truss.md) — **evidência do binário oficial e matriz de paridade item a item**
- [`docs/apresentacao/slides.html`](docs/apresentacao/slides.html) — slides da defesa
- [`docs/relatorios/index.html`](docs/relatorios/index.html) — dossiê de contingência
- [`TEST_INFRA.md`](TEST_INFRA.md) — metodologia da suíte de testes
- [`docs/verificacao-manual.md`](docs/verificacao-manual.md) — checklist de verificação no navegador (roteiro da defesa)

## Requisitos do trabalho (resumo)

| Item | Peso / observação |
| --- | --- |
| Apresentação da parte teórica do modelo | 4,0 pontos — parte mais importante da nota |
| Bateria de 8 exercícios (funcionalidade e taxa de acerto) | 2,0 pontos — só ocorre se a parte teórica for aprovada |
| Trabalho em duplas (no máximo) | — |
| Entrega na semana das avaliações N2 (quarta ou quinta, horário alternativo) | Avisar antecipadamente |
| Presença na prova N2 + assinatura da lista | Condição para a nota |

Detalhes completos em [`docs/enunciado.md`](docs/enunciado.md).
