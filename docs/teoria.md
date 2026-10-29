# Base teórica — módulo Trusses

Documento de apoio à apresentação (4,0 pontos). Aqui estão as deduções escritas,
não só os resultados: o objetivo é que qualquer integrante consiga defender cada
fórmula e cada número da tela.

Treliça de referência usada em todos os exemplos (a mesma do caso `01-triangulo`):

```
        C (2, 3)
        /\
       /  \
      /    \        carga Fy = −10 kN em C
     /      \
   A(0,0)---B(4,0)
    pino     roleto
```

`EA = 1 kN` para todas as barras (irrelevante neste caso, porque a treliça é
isostática — isso é demonstrado em §9).

---

## 1. O que o módulo faz

Dada uma treliça plana (nós, barras, apoios e cargas nodais), o programa devolve:

1. classificação de estaticidade;
2. reações de apoio;
3. esforço normal em **todas** as barras, com sinal e classificação
   tração/compressão;
4. barras de força zero;
5. deslocamentos nodais;
6. verificações de equilíbrio e uma conferência por método independente.

---

## 2. Idealização: por que a treliça é um modelo simples

Uma treliça real é uma estrutura soldada ou parafusada. O modelo que resolve o
problema em segundos se apoia em cinco hipóteses, e **cada uma delas pode ser
questionada na banca**:

| # | Hipótese | O que ela elimina | Quando falha na prática |
| --- | --- | --- | --- |
| H1 | Barras biarticuladas (rótulas sem atrito nas extremidades) | momento fletor na barra → só existe esforço normal `N` | ligações soldadas rígidas geram momento secundário |
| H2 | Cargas aplicadas apenas nos nós | força cortante distribuída ao longo da barra | peso próprio e carga de vento distribuída |
| H3 | Material elástico linear (`σ = E·ε`) | não linearidade do material | escoamento, flambagem |
| H4 | Pequenas deformações (geometria indeformada) | não linearidade geométrica | grandes deslocamentos (cabos, treliças muito esbeltas) |
| H5 | Treliça plana, cargas no plano | componente fora do plano | treliça espacial, excentricidade |

A consequência de H1 + H2 é a mais importante: **cada barra é um elemento de dois
forços**, solicitado apenas axialmente. É isso que permite escrever uma única
relação constitutiva por barra (§7.1) e resolver o problema com um sistema linear.

Como H2 é uma hipótese, o programa **recusa** carga fora de nó: o formato de
entrada só aceita cargas em nós. Carga distribuída precisa ser convertida antes
(ver caso `02-telhado-pratt`, onde a carga de cobertura é aplicada nos nós do
banzo superior).

---

## 3. De onde vêm os dados

### 3.1 Modelo de dados

```
nós      → id, (x, y), tipo de apoio
barras   → id, nó inicial, nó final, EA
cargas   → nó, Fx, Fy
```

Tudo em **kN e metros internamente**. A unidade de entrada é convertida na borda
(`N`, `kgf`, `tf`, `kip`, `lbf`; `cm`, `mm`, `ft`, `in`) e o resultado é
convertido de volta para a unidade pedida. Isso evita a classe de erro mais comum
em software de engenharia: misturar unidades no meio da conta.

### 3.2 Apoios e número de reações

| Apoio | Restringe | Reações |
| --- | --- | --- |
| livre (`none`) | nada | 0 |
| articulação fixa (`pin`) | `ux` e `uy` | 2 (Rx, Ry) |
| apoio móvel / roleto (`roller`) | `uy` | 1 (Ry) |
| roleto horizontal (`roller_x`) | `ux` | 1 (Rx) |

### 3.3 Validação antes de calcular

O programa recusa, com mensagem explícita, antes de qualquer conta:
nó repetido, barra com nó inexistente, barra duplicada, barra de comprimento
nulo, `EA ≤ 0`, carga em nó inexistente, coordenada não numérica ou infinita,
treliça sem nenhum apoio, e unidade desconhecida. Nó sem barras e treliça
desconexa geram **aviso**, não erro.

---

## 4. Estaticidade: `b + r` versus `2n`

Uma treliça plana tem `n` nós e portanto `2n` equações de equilíbrio (duas por
nó: `ΣFx = 0` e `ΣFy = 0`). As incógnitas são `b` esforços normais mais `r`
reações de apoio.

```
grau de indeterminação:   g = b + r − 2n
```

| `g` | Classificação | O que significa |
| --- | --- | --- |
| `g < 0` | **hipostática** | faltam vínculos: é um mecanismo, não há solução de equilíbrio |
| `g = 0` | **isostática** | equilíbrio basta; `N` independe de `EA` |
| `g > 0` | **hiperestática** | sobram vínculos; `N` depende da rigidez relativa `EA` |

**Ponto que a banca costuma cobrar:** a contagem é **condição necessária, não
suficiente**. O caso `10-mecanismo` tem `b + r = 2 + 4 = 6 = 2n`, ou seja `g = 0`,
e mesmo assim é um mecanismo: o nó B, entre dois pinos, com duas barras
colineares, pode se deslocar verticalmente. O programa detecta isso pela
singularidade da matriz de rigidez (§7.5), não pela contagem.

---

## 5. Equilíbrio externo: reações de apoio

O corpo inteiro é um corpo rígido sujeito a cargas e reações:

```
ΣFx = 0:     Σ Fx,aplicadas + Σ Rx = 0
ΣFy = 0:     Σ Fy,aplicadas + Σ Ry = 0
ΣM_A = 0:    Σ (x·Fy − y·Fx) = 0   (momento em relação à origem)
```

Na treliça de referência: `Ax = 0`; `ΣM_A: By·4 − 10·2 = 0 → By = 5 kN`;
`ΣFy: Ay + By = 10 → Ay = 5 kN`. Simetria confirma: carga centrada, apoios
simétricos, reações iguais.

---

## 6. Método dos nós

### 6.1 Convenção de sinal — a decisão que mais causa erro

Adotamos **tração positiva** e desenhamos a força de cada barra **saindo do nó**:

* se o resultado der `N > 0`, a barra está sendo **tracionada**;
* se der `N < 0`, a barra está sendo **comprimida** (a força real aponta para
  dentro do nó, ao contrário do que foi desenhado).

A convenção é fixada **uma vez** no núcleo do programa e testada; a interface, o
diagrama e o relatório usam exatamente a mesma.

### 6.2 Resolução completa da treliça de referência

**Nó C** (carga `Fy = −10 kN`). Direções saindo de C:
AC → `A − C = (−2, −3)/√13 = (−0,5547; −0,8321)`
BC → `B − C = (2, −3)/√13 = (0,5547; −0,8321)`

```
ΣFx: −0,5547·N_AC + 0,5547·N_BC = 0        → N_AC = N_BC
ΣFy: −0,8321·N_AC − 0,8321·N_BC − 10 = 0   → −1,6641·N_AC = 10
                                            → N_AC = N_BC = −6,0093 kN
```

Ambas em **compressão** (sinal negativo). Coerente: a carga empurra o vértice
para baixo e as diagonais seguram o nó, trabalhando comprimidas.

**Nó A** (reações `Ax = 0`, `Ay = 5`). Direções saindo de A:
AB → `(1; 0)`; AC → `(0,5547; 0,8321)`

```
ΣFx: N_AB + 0,5547·N_AC + Ax = 0   → N_AB = −0,5547·(−6,0093) = +3,3333 kN
ΣFy: 0,8321·N_AC + Ay = 0          → 0,8321·(−6,0093) + 5 = −5 + 5 = 0 ✓
```

`N_AB = +10/3 kN` (**tração**) — o banzo inferior trabalha tracionado, o que é o
comportamento esperado de um banzo inferior sob carga vertical descendente.

**Verificação no nó B** (reação `By = 5`): `ΣFx: −N_AB = −3,333 ≠ 0`?
Atenção: em B chegam AB (direção `(−1; 0)`) e BC (direção `(−0,5547; 0,8321)`),
além de `By`. `ΣFx: −3,3333 + (−0,5547)·(−6,0093) = −3,3333 + 3,3333 = 0 ✓`.

### 6.3 Limite do método dos nós

Funciona bem para treliças isostáticas e pequenas. Para uma treliça com 14 nós
(caso `12-pratt-grande`) são 28 equações acopladas — resolvível, mas não à mão
em tempo de prova. E para treliça hiperestática o sistema não fecha (mais
incógnitas que equações). Daí os dois métodos seguintes.

---

## 7. Método matricial da rigidez

É o motor do programa: resolve isostática **e** hiperestática, e de graça fornece
os deslocamentos.

### 7.1 Relação constitutiva da barra

Barra de rigidez axial `EA` e comprimento `L`, com versor `n̂ = (c, s)`. O
alongamento é a projeção relativa dos deslocamentos no eixo da barra:

```
ΔL = (u_b − u_a) · n̂ = c·(u_bx − u_ax) + s·(u_by − u_ay)
```

Material elástico linear (H3) → lei de Hooke para esforço axial:

```
N = (EA / L) · ΔL          N > 0 → tração
```

### 7.2 Matriz de rigidez da barra (4×4)

Escrevendo `ΔL` em função dos quatro deslocamentos nodais e aplicando o princípio
dos trabalhos virtuais, as forças nodais equivalentes são `f = k · u` com

```
        EA/L · ⎡  c²    cs   −c²   −cs ⎤   ⎧ u_ax ⎫
               ⎢  cs    s²   −cs   −s² ⎥   ⎪ u_ay ⎪
               ⎢ −c²   −cs    c²    cs ⎥ · ⎨ u_bx ⎬
               ⎣ −cs   −s²    cs    s² ⎦   ⎩ u_by ⎭
```

Propriedades que conferem a matriz (e que o programa testa):

* **simétrica** — consequência da reciprocidade de Maxwell–Betti;
* **posto 1** — a barra só resiste a um modo de deformação (o axial); os outros
  três modos são de corpo rígido (duas translações e uma rotação);
* `k · [1, 0, 1, 0] = 0` — translação pura não gera força.

Para a barra AB (`L = 4`, `c = 1`, `s = 0`, `EA = 1` → `EA/L = 0,25`):

```
k_AB = 0,25 · ⎡ 1  0 −1  0 ⎤
              ⎢ 0  0  0  0 ⎥
              ⎢−1  0  1  0 ⎥
              ⎣ 0  0  0  0 ⎦
```

### 7.3 Montagem da matriz global

Cada nó `i` ocupa dois graus de liberdade: `2i` (`ux`) e `2i+1` (`uy`). A matriz
global `K` é `2n × 2n` e recebe a soma das contribuições de cada barra nos GDL
correspondentes aos seus dois nós:

```
K = Σ_barras  K_barra  (espalhada nos GDL dos nós da barra)
```

Ordem adotada: `[A.ux, A.uy, B.ux, B.uy, C.ux, C.uy]`.

```
        ⎡ 0,3353   0,1280  −0,2500   0        −0,0853  −0,1280 ⎤
        ⎢ 0,1280   0,1920   0        0        −0,1280  −0,1920 ⎥
K  =    ⎢−0,2500   0        0,3353  −0,1280  −0,0853   0,1280 ⎥
        ⎢ 0        0       −0,1280   0,1920   0,1280  −0,1920 ⎥
        ⎢−0,0853  −0,1280  −0,0853   0,1280   0,1707   0       ⎥
        ⎣−0,1280  −0,1920   0,1280  −0,1920   0        0,3840 ⎦
```

Leitura da matriz: a linha `A.ux` mostra que o nó A "sente" rigidez própria
(`0,3353`), acoplamento com `A.uy` (`0,1280`, da diagonal AC) e com B
(`−0,2500`, da barra AB).

### 7.4 Condições de contorno e solução

Deslocamentos nulos nos apoios: `A.ux`, `A.uy` e `B.uy` (GDL `0, 1, 3`). Os GDL
livres são `B.ux`, `C.ux`, `C.uy` (`2, 4, 5`). Eliminando as linhas e colunas
restringidas:

```
        ⎡ 0,3353  −0,0853   0,1280 ⎤ ⎧u_Bx⎫   ⎧  0 ⎫
K_ff =  ⎢−0,0853   0,1707   0      ⎥ ⎨u_Cx⎬ = ⎨  0 ⎬   = F_f
        ⎣ 0,1280   0        0,3840 ⎦ ⎩u_Cy⎭   ⎩ −10⎭
```

Resolvendo `K_ff · u_f = F_f`:

```
u_Bx = +13,3333      u_Cx = +6,6667      u_Cy = −30,4845   (em m, com EA = 1 kN)
```

Os deslocamentos são grandes porque `EA = 1 kN` é um valor artificial, escolhido
para deixar os números redondos; o que importa é a coerência. Conferindo:
`N_AB = (EA/L)·u_Bx = (1/4)·13,3333 = 3,3333 kN` ✓ — exatamente o esforço normal
obtido. O sinal de `u_Cy` é negativo porque o eixo `y` aponta para cima e a carga
empurra para baixo; `u_Cx > 0` mostra que o nó C se desloca para a direita,
porque o apoio móvel em B libera o deslocamento horizontal do conjunto.

### 7.5 Reações e esforços normais

Reações: `R = K · u − F` nas linhas restringidas.

```
R_Ax = 0        R_Ay = +5,0000        R_By = +5,0000     (kN)
```

Esforço normal por barra: `N = (EA/L)·[−c, −s, c, s]·[u_ax, u_ay, u_bx, u_by]`

```
N_AB = +3,3333   (tração)      N_AC = N_BC = −6,0093   (compressão)
```

**Os mesmos valores do método dos nós** — e isso é verificado automaticamente em
todos os casos do programa.

### 7.6 Detecção de mecanismo (por que não sai número gigante)

Se a treliça for um mecanismo, `K_ff` é **singular** e um `solve` ingênuo devolve
deslocamentos astronômicos com forças sem sentido. O programa faz a
**decomposição em valores singulares** de `K_ff` **antes** de resolver e verifica
duas coisas distintas:

1. **Posto (gate de mecanismo).** Se o menor valor singular `s_min` cai abaixo da
   tolerância de máquina (`s_max · max(shape) · eps`), a matriz é
   **deficiente em posto**: existe direção de deslocamento com rigidez nula. É
   mecanismo, e o cálculo é recusado. Os vetores singulares direitos associados
   aos valores singulares nulos indicam os GDL do modo — por exemplo `[B.uy]` no
   caso `10-mecanismo`.
2. **Condicionamento (aviso).** Se o posto é cheio mas `cond(K_ff) = s_max/s_min`
   é alto (acima de `10^10`), a solução perde dígitos significativos. O resultado
   é entregue com **aviso explícito**, não recusado.

**Por que o gate é o posto e não o autovalor nem o condicionamento.** Três
critérios foram testados neste projeto:

| critério | o que mede | veredito |
|---|---|---|
| `λ_min < 10^-10 · λ_max` | razão de autovalores | **errado**: recusa treliça estável com rigidez contrastada |
| `cond(K_ff) > 10^14` | razão de valores singulares | **errado**: mesma falha, só num regime mais extremo |
| **deficiência de posto** | existe direção de rigidez nula? | **correto**: é exatamente a definição de mecanismo |

Estabilidade cinemática é uma propriedade de *posto*; `cond` mede apenas
qualidade numérica. Medido nos 12 casos do projeto: todos os estáveis têm `cond`
entre 4 e 273 e posto cheio; os instáveis têm posto deficiente (`3/4` e `1/2`).
Uma treliça estável com `EA` de `10^-8` kN num banzo e `10^6` kN nas diagonais
(contraste `10^14`) tem posto cheio e resolve — com aviso de mal condicionada.
Acima de `10^16` de contraste o valor singular cai abaixo da precisão de máquina
e o caso se torna **indistinguível de mecanismo** — limite da aritmética, não do
método.

#### Calibração medida nos 12 casos

Valores obtidos com `python -c` sobre `data/cases/` (reprodutível; a coluna
"posto" é `posto(K_ff)/nº de GDL livres`):

| caso | `cond(K_ff)` | posto | veredito |
|---|---|---|---|
| `01-triangulo` | 4,1 | 3/3 | resolve |
| `02-telhado-pratt` | 78,5 | 13/13 | resolve |
| `03-warren` | 46,3 | 11/11 | resolve |
| `04-pratt-vento` | 64,6 | 13/13 | resolve |
| `05-forca-zero-T` | 13,1 | 5/5 | resolve |
| `06-forca-zero-R3` | 13,8 | 5/5 | resolve |
| `07-geometria-irregular` | 9,4 | 5/5 | resolve |
| `08-hiperestatica` | 11,9 | 5/5 | resolve |
| `09-hipostatica` | 7,9·10¹⁸ | **3/4** | recusa (`hypostatic`) |
| `10-mecanismo` | ∞ | **1/2** | recusa (`mechanism`) |
| `11-sem-carga` | 4,1 | 3/3 | resolve |
| `12-pratt-grande` | 273,4 | 25/25 | resolve |

A separação é limpa: os estáveis têm `cond` ≤ 274 e posto cheio; os instáveis
têm posto deficiente. Nenhum caso do projeto fica perto da fronteira — a
fronteira só aparece em rigidez artificialmente contrastada (ver abaixo).

#### Limite físico do contraste de `EA`

| `EA` do banzo (diagonais `10^6` kN) | contraste | `s_min/s_max` | veredito |
|---|---|---|---|
| `10^-2` | `10^8` | 4,2·10⁻⁹ | resolve |
| `10^-4` | `10^10` | 4,2·10⁻¹¹ | resolve |
| `10^-6` | `10^12` | 4,2·10⁻¹³ | resolve |
| `10^-8` | `10^14` | 4,2·10⁻¹⁵ | resolve **com aviso** |
| `10^-10` | `10^16` | 2,0·10⁻¹⁷ | recusa — abaixo da precisão de máquina |

O limite em `10^16` não é escolha arbitrária: `2·10^-17` é menor que
`n·eps ≈ 6,7·10^-16`, ou seja, o valor singular é **indistinguível de zero** em
precisão dupla. Nenhum material real tem contraste de rigidez dessa ordem.

**Semântica da conferência cruzada.** O método dos nós é exato por equilíbrio e
serve de oráculo. Em regimes de condicionamento extremo ele pode divergir da
rigidez em resíduos da ordem de `10^-6` kN; nesse caso o resultado continua sendo
entregue (`status = "ok"`), mas acompanhado de **aviso explícito** e da ressalva
impressa no relatório. Recusar o cálculo seria pior: o valor está correto dentro
da precisão disponível, e o usuário precisa saber disso — não ser privado do
resultado.

---

## 8. Método das seções (Ritter)

Serve para obter o esforço em **uma** barra sem resolver a treliça inteira, e é a
melhor conferência independente para a banca porque **não usa** nem `EA` nem
deslocamentos.

Procedimento: cortar a treliça em duas partes, escolher a parte mais simples e
aplicar as três equações de equilíbrio nela.

### 8.1 Exemplo resolvido (caso `05-forca-zero-T`)

```
   D(0,3)---------C(4,3)      carga em C: Fx = +6, Fy = −10 kN
     |           /
     |         /              diagonal AC
     |       /
   A(0,0)---B(4,0)            A: pino   B: roleto
```

Reações (equilíbrio global): `Ax = −6`; `ΣM_A: By·4 + 6·3 − 10·4 = 0 → By = 14,5`;
`ΣFy: Ay + 14,5 − 10 = 0 → Ay = −4,5 kN`.

Corte vertical entre `x = 0` e `x = 4`, atravessando as barras **CD, AC e AB**.
Tomamos a parte esquerda (nós D e A).

```
ΣM_A = 0:  −3·N_CD = 0                      → N_CD = 0
ΣFy  = 0:  0,6·N_AC + Ay = 0                → N_AC = 4,5 / 0,6 = +7,5 kN
ΣFx  = 0:  N_AB + 0,8·N_AC + N_CD + Ax = 0  → N_AB = −0,8·7,5 + 6 = 0
```

Resultado: `N_CD = 0`, `N_AC = +7,5 kN` (tração), `N_AB = 0`.

Conferência pelo método dos nós no nó D (sem carga, sem vínculo, duas barras não
colineares): `ΣFx: N_CD = 0` e `ΣFy: N_DA = 0` → **duas barras de força zero**,
exatamente o que a regra R2 prevê (§9). Os dois métodos concordam.

---

## 9. Casos especiais

### 9.1 Barras de força zero

Válidas **somente** quando o nó não tem carga aplicada e não tem vínculo:

| Regra | Situação no nó | Conclusão |
| --- | --- | --- |
| **R1** | 1 barra | essa barra tem `N = 0` |
| **R2** | 2 barras não colineares | ambas têm `N = 0` |
| **R3** | 3 barras, sendo 2 colineares | a terceira tem `N = 0` |

Se houver carga ou reação no nó, **nenhuma** das três regras vale — o programa
verifica essa condição antes de aplicar a regra (testado em
`tests/test_zero_force.py`).

Detalhe que confunde: uma barra de força zero **continua tendo rigidez**. Ela não
contribui para o equilíbrio daquele carregamento, mas estabiliza o nó contra
outros carregamentos e evita mecanismo. Por isso o caso `06-forca-zero-R3` não é
um mecanismo: o montante CT tem `N = 0` mas rigidez axial.

### 9.2 Simetria

Treliça simétrica + carregamento simétrico → esforços simétricos. Serve para
detectar erro grosseiro: se `N` de barras espelhadas divergir, há bug ou erro de
digitação. O caso `03-warren` exercita isso.

### 9.3 Isostática não depende de `EA`

Em treliça isostática, os esforços são determinados apenas pelo equilíbrio: mudar
`EA` de todas as barras **não altera nenhum `N`** (só os deslocamentos). O
programa testa isso com `EA` variando de `1e-3` a `2,5e6`.

Em treliça hiperestática (`08-hiperestatica`, `g = 1`) o esforço **muda** com
`EA`, porque a compatibilidade de deslocamentos entra na solução. Isso é avisado
explicitamente na saída: se a banca der uma treliça hiperestática sem fornecer
`EA`, o resultado correto depende de um dado que não foi dado.

---

## 10. Tensão normal e dimensionamento

O MdSolids tem, depois do cálculo dos esforços, o comando **Stresses → Normal
Stresses in Truss Members** (`frmTrussStress`). É um segundo estágio: primeiro o
esforço normal de cada barra, depois a tensão.

### 10.1 Definição

Para uma barra de treliça (esforço axial puro, hipótese H1), a tensão normal é
uniforme na seção:

```
σ = N / A
```

* `N` — esforço normal da barra, positivo em tração (mesma convenção da seção 6.1);
* `A` — área da seção transversal;
* `σ` — tensão normal; **mesmo sinal de `N`**: tração positiva, compressão negativa.

Em unidades coerentes, `N` em N e `A` em mm² dão `σ` em **MPa**, porque
`1 MPa = 1 N/mm²`. O programa usa essa base internamente: o esforço entra em kN
(base do cálculo estrutural) e é multiplicado por 1000 na hora de dividir pela
área em mm².

### 10.2 Exemplo resolvido (caso `01-triangulo`)

Do método dos nós (seção 6.2): `N_AB = +10/3 = 3,3333 kN` (tração).
Adotando `A = 100 mm²` em todas as barras:

| Barra | `N` [kN] | `A` [mm²] | `σ = N·1000/A` [MPa] |
| --- | --- | --- | --- |
| AB | +3,3333 | 100 | **+33,333** (tração) |
| AC | −6,0093 | 100 | **−60,093** (compressão) |
| BC | −6,0093 | 100 | **−60,093** (compressão) |

A barra mais solicitada é a diagonal comprimida, não a barra mais curta nem a de
maior esforço em módulo por acaso: aqui coincidem porque a área é a mesma. Com
áreas diferentes, **a barra crítica é a de maior `|σ|`**, e é isso que o programa
destaca no resumo.

### 10.3 Dimensionamento inverso: área requerida

O problema inverso é o mais útil na prática: dado o material (tensão admissível
`σ_adm`), qual a área mínima?

```
A_req = |N| / σ_adm
```

O módulo é necessário porque a área não tem sinal: tanto tração quanto compressão
exigem seção positiva. Continuando o exemplo com `σ_adm = 50 MPa`:

| Barra | `N` [kN] | `A_req` [mm²] |
| --- | --- | --- |
| AB | +3,3333 | **66,667** |
| AC, BC | −6,0093 | **120,185** |

Logo, a seção que atende a treliça inteira é `A ≥ 120,185 mm²` — governada pela
diagonal comprimida. Se o material tiver limites diferentes para tração e
compressão (concreto, madeira, compósitos), o programa aceita
`{tension, compression}` separadamente; com `{50, 80}` a diagonal passa a exigir
`6009,252/80 = 75,116 mm²` e a barra AB (66,667 mm²) assume o comando.

### 10.4 Taxa de utilização

Quando a área real é informada **e** a tensão admissível também, o programa
calcula

```
u = |N| / (A · σ_adm) = σ / σ_adm
```

`u ≤ 1` significa seção suficiente; `u > 1`, insuficiente. É o mesmo critério de
`A ≥ A_req`, escrito de forma comparável entre barras de áreas diferentes.

### 10.5 O que a tensão **não** resolve

1. **Flambagem.** Compressão alta pode flambar a barra muito antes de escoar. `σ`
   não vê isso; a verificação de estabilidade é separada (Euler / norma).
2. **Área não altera `N` em treliça isostática** (seção 9.3). Informar área serve
   para obter `σ`, não para mudar os esforços. Em treliça hiperestática, `N`
   depende de `EA = E·A`, então mudar a área **muda** os esforços — o programa
   avisa.
3. **Concentração de tensão** em furos e ligações não é modelada: `σ = N/A` é a
   tensão média nominal na seção bruta.

---

## 11. Interpretação dos resultados

* **Tração (`N > 0`)**: a barra é alongada, puxa os nós para dentro de si.
* **Compressão (`N < 0`)**: a barra é encurtada, empurra os nós.
* **Força zero**: `|N| ≈ 0`, barra sem função naquele carregamento.
* **Ordem de grandeza**: em treliça de telhado com carga vertical, espera-se
  banzo superior comprimido, banzo inferior tracionado e diagonais alternando.
  Se o resultado contrariar isso, desconfie antes de aceitar.
* **Checagem de equilíbrio**: `ΣFx = ΣFy = ΣM = 0` e resíduo nodal nulo. Valores
  na casa de `1e−15` são ruído de ponto flutuante, não erro.
* **Conferência cruzada**: o programa compara o resultado com o método dos nós,
  que é um algoritmo independente. Concordância a `1e−13` significa que o
  resultado não é artefato de uma única formulação.

---

## 12. Limitações (dizer isso em voz alta ganha ponto)

1. Carga só em nó — carga distribuída precisa ser convertida.
2. Linear e elástico: não prevê flambagem nem escoamento. Compressão alta exige
   verificação separada de estabilidade da barra.
3. Treliça hiperestática depende de `EA`; sem esse dado o resultado é
   indeterminado fisicamente, embora o programa calcule com o `EA` informado.
4. Sem peso próprio automático.
5. Apoios só como pino, roleto (vertical ou horizontal) e livre — não há engaste
   (o que seria incoerente com a hipótese H1).
6. Plana: nada de treliça espacial.

---

## 13. Roteiro de apresentação (13 blocos)

| # | Bloco | Mensagem central | Demo no programa |
| --- | --- | --- | --- |
| 1 | Contexto | o que o MdSolids/Trusses faz e o que replicamos | abrir a interface, mostrar o seletor de casos |
| 2 | Idealização | as 5 hipóteses e o que cada uma elimina | mostrar que carga só entra em nó |
| 3 | Dados | nós, barras, apoios, cargas; unidades na borda | editar um nó e ver o JSON mudar |
| 4 | Estaticidade | `g = b + r − 2n` e os três casos | carregar casos 01, 08 e 09 |
| 5 | Equilíbrio externo | ΣFx, ΣFy, ΣM → reações | caso 01, ler as reações na tela |
| 6 | Método dos nós | resolução nó a nó, convenção de tração | caso 01, comparar com o cálculo do slide |
| 7 | Método das seções | corte de Ritter como conferência | caso 05, `N_CD = 0` e `N_AC = 7,5` |
| 8 | Rigidez | matriz da barra → K global → solução | painel de verificações e a matriz na saída |
| 9 | Casos especiais | R1/R2/R3 e simetria | casos 05, 06, 03 |
| 10 | **Tensão normal** | `σ = N/A`; área requerida `A = abs(N)/σ_adm` | caso 01 com A = 100 mm² → σ = 33,3 MPa; modo área requerida |
| 11 | Interpretação | sinal, ordem de grandeza, resíduos | caso 04 (vento) com T/C coloridos |
| 12 | Limitações e validação | hiperestática depende de EA; 12 casos conferidos | caso 08 e o relatório impresso |
| 13 | Demo final | fluxo completo: grade, arraste, calcular, σ, relatório | treliça nova montada ao vivo + imprimir PDF |

**Plano B:** cada caso tem um relatório HTML imprimível (`botão Relatório` →
salvar PDF). Se a máquina falhar, a apresentação continua com os PDFs.
