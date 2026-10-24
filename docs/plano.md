# Plano de execução — Módulo Trusses (N2)

Plano estruturado para construir a versão própria do módulo **Trusses** do MdSolids,
com foco nos dois blocos de nota: **apresentação teórica (4,0 pts)** e **bateria de
8 exercícios (2,0 pts)**.

> **Status: implementado.** As fases F0 a F3 estão concluídas (núcleo, API,
> interface, bateria de 12 casos e relatório). F4 tem o conteúdo teórico pronto em
> [`teoria.md`](teoria.md) — falta montar os slides e ensaiar. F5 (congelamento e
> entrega) depende da data da banca. Ver [`validacao.md`](validacao.md) para o
> registro dos 12 casos conferidos.

---

## 1. Objetivo e critério de sucesso

Entregar um software que, para uma treliça plana definida pelo usuário, calcule e
apresente **reações de apoio** e **esforços normais em todas as barras**
(tração/compressão/força zero), com a mesma cobertura funcional do módulo *Trusses*
do MdSolids, acompanhado do material de apresentação da teoria.

| # | Critério de sucesso | Como é verificado |
| --- | --- | --- |
| S1 | Paridade funcional com o MdSolids/Trusses | Matriz de paridade (§5) 100% marcada |
| S2 | Acerto nos 8 exercícios da banca | Bateria própria de 8+ casos com gabarito (§7) |
| S3 | Teoria defensável em banca | Roteiro de 12 blocos + deduções escritas (§8) |
| S4 | Não quebra com entrada inválida | Casos de erro tratados com mensagem, sem crash (§6.4) |
| S5 | Demonstração ao vivo sem depender de internet | App roda local (`localhost`), plano B em PDF/prints |

**Fora de escopo** (decidido, para não inflar): treliças 3D, treliças espaciais,
barras com momento (pórticos), análise não linear, dimensionamento de seções.

---

## 2. Decisões travadas

| Decisão | Escolha | Justificativa |
| --- | --- | --- |
| Stack | **Python 3.11+ (numpy) + FastAPI + front-end HTML/CSS/JS com SVG** | Solver testável isoladamente (pytest), UI no navegador = zero instalação na banca, SVG dá diagrama vetorial limpo para projetar |
| Prazo | **~3 semanas** | Cronograma de 5 fases (§9) |
| Método numérico | **Método matricial da rigidez (direto)** | Cobre isostáticas e hiperestáticas; deslocamentos saem de graça; é o que a banca espera ver explicado |
| Conferência independente | Método dos nós + método das seções (Ritter) | Prova que o resultado não vem "de dentro do mesmo código" |
| Entrada de dados | JSON versionado + edição visual na UI | JSON = testável e reproduzível; UI = usável na apresentação |
| Unidades | Interno sempre kN e m; exibição configurável | Evita a classe de bug clássica de unidades |

---

## 3. Arquitetura

Três camadas com dependência em uma única direção (`web → api → core`). O `core`
não importa nada de web e é onde mora toda a nota técnica.

```
projeto-marcio-n2/
├── app/
│   ├── core/                 # domínio puro, sem I/O
│   │   ├── model.py          # Node, Member, Support, Load, Truss (dataclasses + validação)
│   │   ├── topology.py       # duplicidade, barra de comprimento zero, nós isolados, colinearidade
│   │   ├── determinacy.py    # b + r vs 2n, grau de indeterminação, detecção de mecanismo
│   │   ├── stiffness.py      # montagem de K, condições de contorno, solve, reações, N nas barras
│   │   ├── equilibrium.py    # resíduo ΣFx, ΣFy, ΣM e verificação de equilíbrio nodal
│   │   ├── zero_force.py     # barras de força zero: regras geométricas + confirmação numérica
│   │   └── units.py          # conversão e formatação (3 decimais, sinal)
│   ├── api/
│   │   ├── app.py            # POST /solve, GET /presets, POST /report
│   │   └── schemas.py        # pydantic: entrada e saída (contrato estável)
│   └── web/
│       ├── index.html        # layout: canvas | painel de propriedades | tabela de resultados
│       ├── js/editor.js      # grid, snap, criar/mover nó, criar barra, apoios, cargas
│       ├── js/render.js      # SVG: barras coloridas por T/C, rótulos, reações, cargas
│       ├── js/checks.js      # painel de verificações (estaticidade, resíduo, avisos)
│       └── css/
├── tests/
│   ├── cases/*.json          # casos com entrada + gabarito (unitário e de integração)
│   └── test_*.py
├── docs/
│   ├── plano.md              # este documento
│   ├── escopo-tecnico.md
│   ├── teoria.md             # deduções para a apresentação (Fase 4)
│   └── apresentacao/         # roteiro + slides
└── README.md
```

**Regra de ouro:** nenhuma conta de engenharia em JavaScript. O front só desenha e
edita; quem calcula é o `core`. Isso mantém um único lugar para auditar e testar.

---

## 4. Contrato de dados (entrada/saída)

Entrada — é o que a UI produz e o que os testes consomem:

```json
{
  "units": { "force": "kN", "length": "m" },
  "nodes": [
    { "id": "A", "x": 0.0, "y": 0.0, "support": "pin" },
    { "id": "B", "x": 4.0, "y": 0.0, "support": "roller" },
    { "id": "C", "x": 2.0, "y": 3.0, "support": "none" }
  ],
  "members": [ { "id": "AB", "a": "A", "b": "B", "EA": 1.0 } ],
  "loads":   [ { "node": "C", "Fx": 0.0, "Fy": -10.0 } ]
}
```

Saída — contrato estável, usado pela UI, pelo relatório e pelos testes:

```json
{
  "status": "ok",
  "determinacy": { "b": 3, "r": 3, "n": 3, "degree": 0, "class": "isostática" },
  "reactions":  [ { "node": "A", "Rx": 0.0, "Ry": 5.0 }, { "node": "B", "Ry": 5.0 } ],
  "members":    [ { "id": "AB", "N": 3.333, "state": "tração" },
                  { "id": "AC", "N": -6.009, "state": "compressão" } ],
  "displacements": [ { "node": "C", "ux": 0.0, "uy": -0.001 } ],
  "checks": { "sumFx": 0.0, "sumFy": 0.0, "sumM": 0.0, "maxNodalResidual": 0.0 },
  "warnings": [ "barra AC: força zero" ],
  "errors": []
}
```

Convenção fixada e escrita na UI: **N positivo = tração**, **negativo = compressão**.

---

## 5. Paridade com o MdSolids/Trusses (checklist da nota de 4,0)

A evidência do binário oficial (formulários, controles, mensagens, cores) e a
**matriz de paridade item a item** estão em [`docs/mdsolids-truss.md`](mdsolids-truss.md).
Resumo do checklist:

- [x] Definir geometria: nós com coordenadas (x, y) e barras por par de nós
- [x] **Grade por espaçamento e nº de intervalos** (como `frmDefGrid`)
- [x] **Barras criadas por arraste** de um ponto de grade a outro
- [x] Apoios: articulação fixa (2 restrições) e apoio móvel/roleto (1 restrição)
- [x] Cargas nodais (Fx, Fy), com sentido e magnitude explícitos no desenho
- [x] Classificação de estaticidade: `b + r` vs `2n` (iso / hipo / hiperestática)
- [x] Reações de apoio por equilíbrio global, exibidas junto ao nó
- [x] Esforços normais em **todas** as barras, com sinal e classificação T/C
- [x] Identificação de barras de força zero
- [x] Diagrama da treliça com valores e cores por estado
- [x] **Paleta do MdSolids opcional** (tração ciano, compressão ouro, força zero magenta)
- [x] **Tensão normal σ = N/A** por barra, com área informada no inspetor
- [x] **Área requerida** a partir de uma tensão admissível (`A = |N|/σ_adm`)
- [x] Unidades de área (mm², cm², m², in²) e de tensão (MPa, kPa, GPa, ksi, psi)
- [x] Tabela de resultados exportável (relatório imprimível, com a tabela de σ)
- [x] Mensagens de erro para hipostática/mecanismo (em vez de resultado absurdo)
- [x] *Extra (não exigido, mas defensável na banca):* deslocamentos nodais e
      treliças hiperestáticas pelo método da rigidez

---

## 6. Núcleo de cálculo — especificação

### 6.1 Validação de entrada (antes de qualquer conta)
Nós com id único; coordenadas numéricas finitas; barras referenciando nós
existentes; sem barra de comprimento zero; sem barra duplicada/sobreposta; sem nó
isolado (aviso); carga apenas em nó (hipótese da treliça); `EA > 0`.

### 6.2 Estaticidade
`n` nós, `b` barras, `r` reações → grau `g = b + r - 2n`.
`g < 0` hipostática (mecanismo) → erro com a explicação; `g = 0` isostática;
`g > 0` hiperestática (resolvível, mas `N` depende de `EA` → aviso explícito).

### 6.3 Método matricial da rigidez
1. Por barra `(a,b)`: `L`, `c = (xb-xa)/L`, `s = (yb-ya)/L`.
2. Rigidez local expandida 4×4: `(EA/L)·[[c²,cs,-c²,-cs],[cs,s²,-cs,-s²],[-c²,-cs,c²,cs],[-cs,-s²,cs,s²]]`.
3. Montagem da `K` global `(2n × 2n)` por soma de contribuições.
4. Condições de contorno: eliminar as linhas/colunas dos GDL restringidos.
5. Resolver `K_ff · u_f = F_f` (`numpy.linalg.solve`; `lstsq`/posto como detector de singularidade).
6. Reações: `R = K·u − F` nas linhas dos GDL restringidos.
7. Esforço normal: `N = (EA/L)·[−c, −s, c, s]·[ua, ub]`, positivo = tração.
8. Deslocamentos: `u` completo (livre + zeros nos apoios).

**Robustez numérica:** posto/condicionamento da `K_ff` antes do solve; se singular,
identificar os GDL sem rigidez e reportar "mecanismo" em vez de número gigante.

### 6.4 Casos de erro tratados (todos com teste)
Treliça hipostática · mecanismo interno (rank deficiente) · nó desconectado ·
barra de comprimento zero · barra duplicada · id inexistente · `EA ≤ 0` ·
carga aplicada fora de nó · nenhum apoio · zero nós.

### 6.5 Verificações de consistência (o "como sei que está certo")
- `ΣFx = ΣFy = ΣM = 0` global com todas as forças + reações.
- Equilíbrio nodal: em cada nó, a soma vetorial dos esforços das barras + carga = 0.
- Caso isostático: `N` independente de `EA` (rodar com `EA=1` e `EA=1000` → mesmo `N`).
- Método dos nós / seções calculado à mão para os casos da bateria.

---

## 7. Bateria de validação (8 exercícios + reservas)

Cada caso vira um `tests/cases/*.json` com gabarito calculado à mão **e** conferido
no MdSolids. A banca vai usar 8 exercícios; a bateria própria tem 12 para cobrir o
espaço de problemas.

| # | Caso | O que exercita |
| --- | --- | --- |
| 1 | Treliça triangular, pino em A, roleto em B, carga vertical em C | Caso canônico (gabarito exato já levantado: `Ay=By=5`, `AB=10/3`, `AC=BC=−5√13/3`) |
| 2 | Treliça de telhado tipo Fink com carga distribuída convertida em cargas nodais | Conversão de carregamento, múltiplos nós |
| 3 | Treliça Pratt com carga lateral (vento) | Apoio móvel com reação horizontal nula, barras em tração/compressão alternadas |
| 4 | Treliça Warren com vários painéis | Simetria e padrão de sinais |
| 5 | Treliça com nós em T/L gerando barras de força zero | Detecção de força zero |
| 6 | Treliça com duas cargas inclinadas em nós distintos | Decomposição de forças |
| 7 | Treliça com apoio em altura diferente (geometria não retangular) | Cossenos diretores, ângulos não triviais |
| 8 | Treliça hiperestática de 1 grau (`g = 1`) | Método da rigidez + sensibilidade a `EA` |
| 9 | Treliça hipostática | Deve **falhar com mensagem**, não travar |
| 10 | Treliça com mecanismo interno (`g = 0` mas `K` singular) | Detecção de mecanismo |
| 11 | Caso com carga zero e só peso próprio desprezado | Estado trivial (todas as barras em zero) |
| 12 | Treliça de maior porte (~12 nós) para checar desempenho e legibilidade | Escala |

**Critério de aceite da bateria:** 100% de acerto numérico contra gabarito
(tolerância 1e-6 em `N` e reações) e 100% de casos de erro com mensagem correta.

---

## 8. Entregável da apresentação teórica (4,0 pts)

Roteiro de 12 blocos, cada um com demo no software. Documento de apoio em
`docs/teoria.md` com as deduções escritas (não só slides).

1. **Contexto** — o que o MdSolids/Trusses faz e o que vamos replicar.
2. **Idealização da treliça** — barras biarticuladas, cargas só nos nós, sem flexão,
   pequenas deformações, material elástico linear. *Por que as hipóteses importam.*
3. **De onde vêm os dados** — modelo de dados (nós, barras, apoios, cargas), unidades,
   validação de entrada; mostrar o JSON e a UI lado a lado.
4. **Estaticidade** — `b + r` vs `2n`, exemplos de iso/hipo/hiperestática; demo do
   app classificando os três.
5. **Equilíbrio externo** — ΣFx, ΣFy, ΣM → reações; convenção de sinais; demo.
6. **Método dos nós** — resolução manual de uma treliça simples, nó a nó, com a
   convenção "tração saindo do nó"; comparar com a saída do app.
7. **Método das seções (Ritter)** — corte estratégico para uma barra específica;
   por que serve como conferência independente.
8. **Método matricial da rigidez** — dedução da matriz de barra a partir de
   `N = (EA/L)·Δ`, matriz de transformação por `c, s`, montagem da `K` global,
   condições de contorno, solução de `K u = F`, recuperação de `N = (EA/L)·[−c,−s,c,s]·u`.
   Mostrar a `K` montada numericamente para o exemplo do bloco 6.
9. **Casos especiais** — barras de força zero (regras), simetria, nós com 3 barras.
10. **Interpretação dos resultados** — sinal e significado físico de T/C, ordem de
    grandeza, checagem de equilíbrio global, deslocamentos.
11. **Limitações e validação** — hipóteses, hiperestática depende de `EA`, o que o
    software não faz; bateria de casos e conferência contra o MdSolids.
12. **Demo final + contingência** — fluxo completo ao vivo (montar, calcular, ler);
    plano B com prints/PDF se a máquina falhar.

---

## 9. Cronograma (~3 semanas)

| Fase | Dias | Entregável | Critério de aceite |
| --- | --- | --- | --- |
| **F0 — Fundação** | 1–2 | Repo estruturado, `model.py` + validação, contrato JSON, CI de testes rodando | `pytest` verde com testes de validação de entrada |
| **F1 — Núcleo** | 3–6 | `determinacy`, `stiffness`, `equilibrium`, `zero_force` | Casos 1, 4, 5, 9, 10, 11 da bateria passando |
| **F2 — API + UI** | 7–11 | `POST /solve`, editor com grid/snap, render SVG, tabela de resultados | Montar a treliça do caso 1 pela UI e obter o mesmo resultado do teste |
| **F3 — Robustez + bateria** | 12–15 | Presets, import/export JSON, relatório imprimível, bateria completa, conferência no MdSolids | 12/12 casos verdes; paridade §5 100% |
| **F4 — Teoria** | 16–19 | `docs/teoria.md`, slides, roteiro cronometrado, ensaio | Apresentação de 12 blocos roda no tempo, sem consultar código |
| **F5 — Congelamento** | 20–21 | Tag de entrega, build local documentado, ensaio final, aviso de entrega ao professor | App roda em máquina limpa seguindo o README |

**Marcos de decisão:** fim da F1 (núcleo correto?) · fim da F2 (usável?) · fim da F3
(congelar escopo — nada novo entra depois) · fim da F4 (ensaio aprovado).

---

## 10. Riscos e mitigações

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| A banca usa treliça hiperestática e `N` depende de `EA` | Resultado "certo" com dado que não foi fornecido | Aviso explícito na UI + `EA=1` documentado + explicar a dependência na apresentação |
| Caso de mecanismo devolve números gigantes em vez de erro | Perda de credibilidade | Checagem de posto/condicionamento antes do solve (F1) |
| UI quebra ao vivo | Perde a demo | Plano B: relatório PDF/prints; demo ensaiada; app local sem internet |
| Escopo crescer (3D, pórticos, animação) | Não fecha em 3 semanas | Fora de escopo declarado (§1); congelamento na F5 |
| Teoria rasa (4,0 pts é o maior peso) | Perde a maior fatia da nota | F4 reserva 4 dias e tem deduções escritas, não só slides |
| Erro de convenção de sinal T/C | Todo resultado parece errado | Convenção única fixada no core, testada nos casos 1 e 4 |
| Unidades misturadas | Erro silencioso | Interno sempre kN/m; conversão só na borda |

---

## 11. Definição de pronto

- [x] `pytest` verde, bateria de 12 casos + casos de erro
- [x] App local sobe com um comando documentado no README
- [x] Paridade §5 com todos os itens marcados
- [ ] Conferência dos 8 exercícios contra o MdSolids registrada em `docs/validacao.md`
      — **feito contra gabarito analítico e método dos nós** (12/12 casos, ver
      `docs/validacao.md`); falta a conferência direta no MdSolids original, que
      exige a máquina com o software instalado
- [ ] `docs/teoria.md` + slides + roteiro cronometrado
- [x] Relatório imprimível por caso (entrada, resultados, verificações)
- [ ] Entrega agendada com o professor (quarta ou quinta da semana N2)
