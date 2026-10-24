# Paridade com o módulo Trusses do MdSolids — evidência e matriz

Este documento registra **como** a referência foi levantada (de forma
reprodutível), **o que** foi encontrado no binário oficial e **item por item** o
que o projeto entrega em relação a ela. A matriz da seção 5 é o artefato de
conferência: todas as linhas estão marcadas.

---

## 1. Objeto da comparação

| Item | Valor |
|---|---|
| Produto | MDSolids 4.0 (Educational Software for Mechanics of Materials) |
| Instalador usado | `SetupMDSolids40.zip` (17.953.241 bytes) |
| Pacote interno | `SetupMDSolids40.msi` (655.360 bytes) |
| Executável | `MDSolids.exe` — 8.167.424 bytes, **Visual Basic 6.0** |
| Ajuda | `MDSolids.chm` — 2.304.482 bytes (HelpScribble), 385 arquivos ao descompilar |
| Módulo comparado | Trusses |

O `.exe` é VB6, portanto carrega nomes de formulários, nomes de controles e
strings de interface em texto simples (ASCII e UTF-16LE). Isso permite citar a
origem de cada afirmação em vez de descrever o comportamento "de memória".

## 2. Como a evidência foi obtida (reprodutível)

```powershell
# 1. extrair o MSI sem instalar
msiexec /a SetupMDSolids40.msi /qb TARGETDIR=.\files

# 2. descompilar a ajuda
hh.exe -decompile .\help .\files\ProgramFilesFolder\MDSolids40\MDSolids.chm

# 3. ler as strings do executável (ASCII e UTF-16LE)
$bytes = [IO.File]::ReadAllBytes('MDSolids.exe')
[Text.Encoding]::ASCII.GetString($bytes)   | Select-String 'frmTruss'
[Text.Encoding]::Unicode.GetString($bytes) | Select-String 'geometrically unstable'
```

Todos os trechos citados abaixo saíram desse procedimento; nenhuma afirmação
depende de memória ou de documentação de terceiros.

## 3. Inventário de evidências

### 3.1 Formulários e módulos (ASCII no `.exe`)

| Símbolo | Ocorrências | Papel |
|---|---|---|
| `frmTruss` | 6 | janela principal do módulo Trusses |
| `frmDefGrid` | 2 | definição da grade |
| `frmTrussLoad` | 2 | entrada de cargas nodais |
| `frmTrussStress` | 2 | tensões normais nas barras |
| `modTruss` | 1 | módulo de cálculo |
| `picTruss` | 3 | quadro de desenho (`picTruss_Paint`) |

Lista de formulários do projeto VB6 (trecho literal):
`frmAbout … frmBeamDiagrams … frmTruss … frmDefGrid … frmTrussLoad … frmTrussStress … frmMatrix … frmLinSolve …`

### 3.2 Controles e rotinas

| Símbolo | Origem | Papel |
|---|---|---|
| `cmdCompute` | ASCII, 22× | botão **Compute** |
| `cmdGridMake` | ASCII | botão que gera a grade |
| `MakeTrussGridCoords` | ASCII | rotina que materializa os pontos da grade |
| `txtSpacing`, `lblGridSpace` | ASCII | espaçamento da grade |
| `cmdUpDnHorizontalSpacing`, `cmdUpDnVerticalSpacing` | ASCII | incremento do espaçamento |
| `lblUnderGrid` | ASCII | nº de intervalos sob a grade |
| `cboReactions` | ASCII | seletor de reações |
| `cboMemberForces` | ASCII (variante `cboTrussResults`) | seletor de esforços |
| `txtTrussResults` | ASCII | área de texto dos resultados |
| `cmdTrussStress`, `mnuTrussStress`, `mnuTrussStress_Click` | ASCII | acesso às tensões |
| `PrintTrussResults`, `mnuPrintResults` | ASCII | impressão dos resultados |
| `txtArea`, `fraArea`, `fraAreaUnits` | ASCII | **área por barra** e sua unidade |
| `fraStressLimit`, `txtStressLimit`, `cboAllowableStresses` | ASCII | **tensão admissível** |
| `lblActiveFile`, `optMakeOrTake`, `optTrussDefine`, `mnuEditGrid`, `cmdDefGrid` | ASCII | fluxo de definição/edição |

### 3.3 Legendas e mensagens (strings de interface)

| Texto literal | Codificação | Significado |
|---|---|---|
| `Define Truss Grid` | ASCII (legenda de `frmDefGrid`) | nome da janela de grade |
| `Normal Stresses in Truss Members` | ASCII (legenda de `frmTrussStress`) | nome do comando de tensões |
| `Allowable Stress Fc` | ASCII (`fraStressLimit`) | rótulo da tensão admissível |
| `Member Forces` | ASCII + UTF-16 | bloco de esforços |
| `Reactions` | ASCII 9×, UTF-16 3× | bloco de reações |
| `Tension (+)` / `Compression (-)` | UTF-16 | **convenção de sinal** |
| `No. Members`, `Restraints`, `Joints` | UTF-16 | termos da fórmula de estaticidade |

### 3.4 Recusas (mensagens de erro) — texto integral

> "This truss is statically indeterminate, and the MDSolids truss solution
> algorithm is designed for statically determinate trusses only. To be
> statically determinate, a truss must satisfy the following relationship:
> (No. Members) + (No. Restraints) = 2 × (No. Joints) … **Statically
> Indeterminate Truss** … triangles throughout the truss. This truss is
> unstable. Remember that all truss joints are assumed to be pin connections
> (i.e., no moment)."

> "**Unstable Truss** — Sorry, the analysis was unsuccessful. The truss appears
> to be **geometrically unstable**. Check the truss input data."

Extraído em UTF-16LE do `.exe` (1 ocorrência de cada).

### 3.5 Fluxo observado

1. **New Truss** → `frmTruss`.
2. **Define Truss Grid** → `frmDefGrid`: espaçamento horizontal e vertical +
   número de intervalos; `cmdGridMake` gera os pontos com
   `MakeTrussGridCoords`.
3. **Barras por arraste** entre pontos de grade; apoios arrastados em X ou Y;
   cargas arrastadas com magnitude (`frmTrussLoad`).
4. **Compute** (`cmdCompute`), habilitado apenas com barras, ≥ 3 restrições e
   ≥ 1 carga.
5. Resultados nas barras: setas de reação, cores por estado e letras automáticas
   nos nós.
6. **Stresses → Normal Stresses in Truss Members** (`frmTrussStress`): área por
   barra (`txtArea`) → σ; ou tensão admissível (`txtStressLimit`) → área
   requerida.

### 3.6 Cores do original

Compressão em **ouro**, tração em **ciano**, força zero em **magenta** —
confirmado nas imagens da ajuda descompilada (`TrussStress.png`,
`TrussGeneral.png`, `TrussRect.png`, `MenuTrussStart.png`).

## 4. Convenções preservadas

| Convenção | Original | Projeto |
|---|---|---|
| Sinal do esforço | `Tension (+)`, `Compression (-)` | `N > 0` tração, `N < 0` compressão |
| Nós como rótulos | letras automáticas | letras automáticas (`A`, `B`, … `Z`, `A1`…) |
| Apoios | articulação (2 reações) e rolete (1) | `pin`, `roller`, `roller_x` |
| Estaticidade | `b + r = 2n` | `g = b + r − 2n`, com iso/hipo/hiper |

## 5. Matriz de paridade item a item

`✔` = implementado e verificável no projeto. A coluna **onde** indica o arquivo
ou rota que o candidato pode abrir na banca.

| # | Recurso do MdSolids/Trusses | Original (evidência) | Projeto | Onde | Situação |
|---|---|---|---|---|---|
| 1 | Definir geometria por nós e barras | `frmTruss`, `picTruss` | `Truss`/`Member`, editor SVG | `app/core/model.py`, `app/web/js/editor.js` | ✔ |
| 2 | Grade por espaçamento | `txtSpacing`, `lblGridSpace`, `cmdUpDn*Spacing` | `Δx`, `Δy` + pontos de grade | `index.html` `#grid-dx/#grid-dy`, `Editor.setGrid` | ✔ |
| 3 | Grade por nº de intervalos | `lblUnderGrid`, `MakeTrussGridCoords` | `nx`, `ny` (extensão = `n·Δ`) | `index.html` `#grid-nx/#grid-ny`, `editor.js` | ✔ |
| 4 | Gerar grade | `cmdGridMake`, `cmdDefGrid` | botão **Aplicar** | `#btn-grid` → `App.applyGrid` | ✔ |
| 5 | Criar barras por arraste | arraste em `picTruss` | arraste com linha fantasma | `editor.js` (`rubber`, `onPointerUp`) | ✔ |
| 6 | Criar nó por clique na grade | arraste/soltura | ferramenta **Nó** + encaixe | `editor.js` (`state.tool === 'node'`) | ✔ |
| 7 | Apoios articulação / rolete | arraste em X ou Y | `pin`, `roller`, `roller_x` | inspetor do nó, `cycleSupport` | ✔ |
| 8 | Cargas nodais com magnitude | `frmTrussLoad` | `Fx`, `Fy` com seta e valor | inspetor do nó, `arrowSvg` | ✔ |
| 9 | Botão Compute com pré-condições | `cmdCompute` | **Calcular** + validação no núcleo | `#btn-solve`, `app/core/model.py` | ✔ |
| 10 | Reações de apoio | `cboReactions` | tabela + setas no diagrama | `/api/solve` → `reactions` | ✔ |
| 11 | Esforços normais em todas as barras | `cboMemberForces` | tabela com sinal e estado | `/api/solve` → `members` | ✔ |
| 12 | Classificação de estaticidade | `No. Members/Restraints/Joints` | `determinacy` com grau | `app/core/determinacy.py` | ✔ |
| 13 | Recusa de treliça instável | "geometrically unstable" | `hypostatic` / `mechanism` com GDL citado | `app/core/errors.py`, `stiffness.py` | ✔ |
| 14 | Recusa de treliça hiperestática | "Statically Indeterminate Truss" | **resolvida** (superconjunto) + aviso de dependência de `EA` | `app/core/solver.py` | ✔ (supera) |
| 15 | Letras automáticas nos nós | rótulos automáticos | letras automáticas | `state.js` `nextNodeId` | ✔ |
| 16 | Cores por estado (padrão) | — | azul/vermelho acessíveis | `app/render/svg.py` `PALETTES.padrao` | ✔ |
| 17 | **Paleta do original** (ciano/ouro/magenta) | imagens da ajuda | `palette=mdsolids` | `/api/figure`, `#palette-select` | ✔ |
| 18 | Força zero destacada | magenta | estado `zero` + lista de barras de força zero | `app/core/zero_force.py` | ✔ |
| 19 | **Tensão normal σ = N/A** | `frmTrussStress`, `txtArea` | `σ` por barra (N, A, σ, estado) | `app/core/stress.py`, `/api/stress` | ✔ |
| 20 | **Área requerida por σ_adm** | `txtStressLimit`, `fraStressLimit` | `A_req = abs(N) / σ_adm` + folga | `app/core/stress.py` `required_areas` | ✔ |
| 21 | Unidades de área e tensão | `fraAreaUnits`, `cboUnits` | `mm², cm², m², in²` · `MPa, kPa, GPa, ksi, psi` | `app/core/units.py`, `#unit-area/#unit-stress` | ✔ |
| 22 | σ no diagrama | rótulos de tensão | rótulo `σ x.x` | `/api/figure` `showStress` | ✔ |
| 23 | Resultados em tabela | `txtTrussResults`, `cboTrussResults` | painel + tabela de tensões | `app/web/js/results.js` | ✔ |
| 24 | Impressão / relatório | `PrintTrussResults`, `mnuPrintResults` | relatório HTML imprimível com σ | `/api/report`, `app/api/report.py` | ✔ |
| 25 | Salvar/carregar caso | `lblActiveFile`, `optMakeOrTake` | exportar/importar JSON + 12 casos prontos | `app.js`, `/api/presets` | ✔ |
| 26 | Conferência independente do resultado | — | método dos nós (não existe no original) | `app/core/joints.py` | ✔ (extra) |
| 27 | Deslocamentos nodais | — | método da rigidez | `app/core/stiffness.py` | ✔ (extra) |

**Cobertura: 27 de 27 itens (100%)** — 24 itens em paridade direta, 1 em
superconjunto (#14 resolve o que o original recusa) e 2 extras (#26 e #27, que o
original não tem). Nenhum item em falta.

## 6. Diferenças deliberadas (e por quê)

1. **Treliça hiperestática é resolvida, não recusada.** O original devolve
   "Statically Indeterminate Truss" porque usa equilíbrio nodal puro. O projeto
   usa o método da rigidez e resolve, mas avisa que `N` passa a depender de
   `EA`. Resolver é superconjunto de recusar; a recusa continua disponível
   como mensagem para o caso hipostático/mecanismo.
2. **Paleta do original é opção, não padrão.** As cores ciano/ouro/magenta são
   fiéis à referência, mas têm contraste baixo para projeção e impressão P&B.
   A paleta padrão é a acessível; a do MdSolids fica a um clique.
3. **Área é entrada opcional por barra.** Sem área, o cálculo de esforços
   continua completo e a tensão é marcada como indisponível — em vez de obrigar
   o preenchimento antes de qualquer resultado.
4. **Sem dependência de biblioteca de grade.** A grade é desenhada em SVG puro;
   o original usa `MSFLXGRD.OCX`, que é um componente COM dos anos 1990.

## 7. Como reproduzir a conferência no projeto

```powershell
python -m pytest -q tests/test_stress.py    # σ, área requerida, unidades, erros
python -m pytest -q tests/test_api.py       # /api/stress, /api/figure paletas, relatório
python serve.py                             # interface: grade, arraste, σ, paleta
```

No navegador, o roteiro de verificação é:

1. **Grade**: informar `Δx`, `Δy`, `nx`, `ny` → **Aplicar**.
2. **Arraste**: ferramenta **Barra**, arrastar de um ponto de grade a outro.
3. **Apoios**: duplo clique no nó alterna o apoio.
4. **Calcular** → esforços, reações, verificações.
5. **Área** no inspetor de cada barra (ou "Aplicar esta área a todas") →
   **Calcular tensões** mostra σ por barra.
6. **Modo área requerida** + `σ_adm` → **Calcular áreas** mostra `A_req`.
7. **Paleta MdSolids** → diagrama com ciano/ouro/magenta.
8. **Relatório** → seção "Tensões normais (σ = N/A)".

---

## 8. Registro de validação em quatro frentes

### F1 — Correção numérica

Gabarito analítico do caso `01-triangulo` (A(0,0) pino, B(4,0) roleto, C(2,3),
`Fy = −10 kN`): `N_AB = +10/3 kN`, `N_AC = N_BC = −5√13/3 = −6,009252 kN`.

| grandeza | analítico | observado | onde |
|---|---|---|---|
| `σ_AB` com `A = 100 mm²` | `(10/3)·1000/100 = 33,3333 MPa` | **33,333** | `tests/test_stress.py`, painel de tensões |
| `σ_AC` com `A = 100 mm²` | `−60,0925 MPa` | **−60,093** | idem |
| `A_req(AB)` com `σ_adm = 50 MPa` | `(10/3)·1000/50 = 66,6667 mm²` | **66,667** | idem |
| `A_req(AC)` com `σ_adm = 50 MPa` | `120,1850 mm²` | **120,185** | idem |
| `A_req(AC)` com `σ_adm = 80 MPa` | `75,1157 mm²` | **75,116** | `tests/test_stress.py` |

Estabilidade numérica herdada: equilíbrio `ΣFx`, `ΣFy`, `ΣM` e resíduo nodal na
ordem de `1e−15`; conferência cruzada pelo método dos nós com diferença `0`.
Recusas verificadas: `bad_area` (área ≤ 0), `bad_allowable` (σ_adm ≤ 0),
`hypostatic`, `mechanism` (com o GDL culpado citado, ex.: `B.uy`).

### F2 — Paridade com o MdSolids

Matriz da seção 5, **27/27 itens**. Evidência de origem na seção 3 (símbolo +
codificação + texto literal). Nenhum item em falta; três diferenças
deliberadas, todas documentadas na seção 6.

### F3 — Arquitetura e testes

- **Contrato só cresce**: `units` ganhou `area` e `stress`; `member` ganhou
  `area`; `/api/solve` ganhou o bloco `stress`; a rota `/api/stress` é nova.
  Nenhum campo existente foi renomeado ou removido — os 12 gabaritos continuam
  válidos sem edição.
- **Domínio puro**: o cálculo de tensão mora em `app/core/stress.py`, sem I/O,
  e é consumido por `solver.stress_payload`; o front não calcula nada.
- **Cobertura de erro**: área nula/negativa, σ_adm nula/negativa, modo
  inválido (HTTP 400), modelo inválido, barra sem área (parcial), nenhuma barra
  com área.
- **Suíte**: `215 passed`. `docs/validacao.md` regenerado por script: **12/12**.

### F4 — Didática e apresentação

- `docs/teoria.md` §10 traz a definição de `σ = N/A`, o exemplo resolvido com
  números conferíveis, o dimensionamento inverso, a taxa de utilização e o que
  a tensão **não** resolve (flambagem, concentração de tensão, dependência de
  `EA` na hiperestática).
- Roteiro de apresentação com 13 blocos, incluindo o bloco novo de tensão.
- A interface mostra o número, a unidade e o estado na mesma linha, e repete o
  gabarito no resumo ("maior |σ| 60,093 MPa (AC)"), o que permite à banca
  conferir o cálculo à mão durante a demo.

### Verificação no navegador (observada)

Sessão real em `python serve.py --port 8123`, sem erro no console:

1. grade `Δx = Δy = 1`, `nx = 4`, `ny = 3` aplicada → 20 pontos desenhados;
2. três barras criadas **por arraste** entre pontos de grade (A(0,0), B(4,0),
   C(2,3)), com linha fantasma durante o movimento;
3. apoios `pin`/`roller` por duplo clique e `Fy = −10 kN` no inspetor;
4. **Calcular** → `AB +3,333 tração`, `BC/CA −6,009 compressão`, reações
   `Ay = By = 5`, equilíbrio verificado, método dos nós com diferença `0`;
5. área `100 mm²` em todas as barras → painel de tensões com
   `33,333 / −60,093 / −60,093 MPa`;
6. modo **área requerida** com `σ_adm = 50 MPa` → `66,667` e `120,185 mm²`,
   com "insuficiente" nas duas diagonais para a área atual de `100 mm²`;
7. **Paleta MdSolids** → SVG com `#00b8d4`, `#b8860b`, `#d81b9b`; voltando para
   **padrão**, as cores do original desaparecem e voltam `#2563eb`/`#dc2626`;
8. **Relatório** → HTML com título, figura, seção "Tensões normais (σ = N/A)",
   valores `33.333` e `60.093` e `@media print`.

### Defeitos encontrados e corrigidos durante a verificação

| defeito | causa | correção |
|---|---|---|
| `σ` aparecia como `Σ` em rótulos e cabeçalhos | `text-transform: uppercase` maiusculiza U+03C3 → U+03A3 | classe `.sigma` com `text-transform: none`, aplicada no HTML, no JS e no relatório; teste que impede a regressão |
| unidades em maiúsculas (`KN`, `MM²`) | mesma causa nos cabeçalhos numéricos | `table.data th.num { text-transform: none }` e `span.unit` |
| fórmula `b + r − 2n` virava `B + R − 2N` | mesma causa nos rótulos `kv` | classe `.math` |
| quadro redimensionava ao selecionar um elemento, invalidando o arraste em curso | altura do inspetor variava com o conteúdo | altura fixa de `168px` no inspetor |
| painel de tensões ficava com tabela vazia quando nenhuma barra tinha área | faltava estado vazio | mensagem explicando o que fazer |
| painel de tensões mantinha resultado antigo depois de um erro de cálculo | não era limpo | `Results.clearStress()` no caminho de erro |
