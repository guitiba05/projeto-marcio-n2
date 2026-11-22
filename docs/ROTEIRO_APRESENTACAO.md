# Roteiro da apresentação — Treliças (módulo Trusses do MDSolids)

Este roteiro cobre os 4 pontos da avaliação teórica:

1. **como obter os dados** (do enunciado para o programa);
2. **como os dados são tratados no software**;
3. **os conceitos dos cálculos** (equilíbrio de nós, sistema de equações, Gauss, tensão);
4. **apresentação e interpretação dos resultados**.

Todos os números deste roteiro foram conferidos à mão **e** no programa
(exemplos 1, 2 e 3 do seletor "Exemplo").

---

## 0. Sequência sugerida (≈ 15 minutos)

| Tempo | O que mostrar | Quem fala (sugestão para a dupla) |
|---|---|---|
| 2 min | O que é treliça, hipóteses, apoios e convenção de sinais (seção 1) | Pessoa 1 |
| 2 min | Como transformar um exercício em dados (seção 2) | Pessoa 1 |
| 5 min | Exemplo 1 à mão e depois no programa, aba "Cálculo passo a passo" (seção 3) | Pessoa 1 (à mão) e Pessoa 2 (programa) |
| 2 min | Exemplo 2: barras de força zero e reação negativa (seção 4) | Pessoa 2 |
| 1 min | Exemplo 3: treliça maior, 12 equações (seção 5) | Pessoa 2 |
| 2 min | Casos de erro: hipostática, hiperestática e instável (seção 6) | Pessoa 1 |
| 1 min | Como o código está organizado (ver `COMO_O_CODIGO_FUNCIONA.md`) | Pessoa 2 |

---

## 1. Teoria em 8 ideias

### 1.1 O que é uma treliça

Uma estrutura feita de **barras retas** ligadas nas pontas por **nós**. Hipóteses do modelo
(as mesmas do MDSolids):

- os nós são **pinos** (rótulas): não transmitem momento;
- as cargas são aplicadas **só nos nós**;
- o peso próprio das barras é desprezado (ou convertido em cargas nos nós).

**Consequência:** cada barra só recebe duas forças, uma em cada ponta. Para a barra ficar em
equilíbrio, essas duas forças precisam estar **na direção da própria barra**. Então cada barra
tem **uma única incógnita**: a força normal **N**.

### 1.2 Convenção de sinais (usada no programa inteiro)

| Grandeza | Positivo | Negativo |
|---|---|---|
| Força na barra N | **tração** (a barra é puxada e tende a alongar) | **compressão** (a barra é empurrada e tende a encurtar) |
| Fx (carga ou reação) | para a direita → | para a esquerda ← |
| Fy (carga ou reação) | para cima ↑ | para baixo ↓ |

> **Truque do método:** supomos **todas as barras tracionadas**. Se a conta der N negativo, a
> barra está comprimida. Não precisa adivinhar o sentido antes.

### 1.3 Apoios

| Apoio no programa | Desenho | Reações | Nº |
|---|---|---|---|
| Fixo / pino | triângulo | Rx e Ry | 2 |
| Rolete (só Ry) | triângulo com rodinhas | Ry | 1 |
| Rolete (só Rx) | triângulo de lado | Rx | 1 |
| Livre | — | nenhuma | 0 |

### 1.4 Equilíbrio de um nó

Cada nó está parado, então a soma das forças nele é zero:

```
ΣFx = 0      ΣFy = 0
```

São **2 equações por nó**. Não existe equação de momento no nó, porque todas as forças passam
pelo mesmo ponto.

### 1.5 Decompondo a força de uma barra

Se a barra vai do nó i ao nó j:

```
Δx = xj − xi        Δy = yj − yi        L = √(Δx² + Δy²)
cos θ = Δx / L      sen θ = Δy / L
```

Como a barra está tracionada, ela **puxa o nó i na direção de j**. A força que ela faz no nó i é:

```
componente x = N · cos θ        componente y = N · sen θ
```

No nó j o vetor é o contrário (−cos θ, −sen θ), porque a barra puxa j na direção de i.
**É exatamente isso que o programa calcula**: a direção "do nó para o outro nó".

### 1.6 Estaticidade: contar equações e incógnitas

- **n** = número de nós → **2n equações**
- **b** = número de barras → b incógnitas (os N)
- **r** = número de reações → r incógnitas

| Comparação | Classificação | O que acontece |
|---|---|---|
| b + r = 2n | **isostática** | sistema quadrado, solução única (se a geometria for estável) |
| b + r < 2n | **hipostática** | faltam barras ou apoios, a estrutura se move |
| b + r > 2n | **hiperestática** | sobram incógnitas, só o equilíbrio não resolve (o MDSolids recusa) |

> **Cuidado:** b + r = 2n é condição **necessária, mas não suficiente**. Um quadrado sem diagonal
> pode fechar a conta e mesmo assim ser instável (ver o Erro 3 na seção 6).

### 1.7 Por que o computador monta um sistema em vez de ir nó a nó

À mão, procuramos um nó com no máximo 2 incógnitas, resolvemos, e passamos ao próximo.
Isso nem sempre é possível em treliças mais complicadas. O programa faz o caminho geral:

1. escreve **todas** as 2n equações de uma vez;
2. organiza em forma de matriz: **[A]·{x} = {c}**;
3. resolve tudo junto pela **eliminação de Gauss**.

O resultado é idêntico ao método dos nós feito à mão, porque as equações são as mesmas.

### 1.8 Eliminação de Gauss (a ideia)

- **Ida (escalonamento):** para cada coluna, escolhemos um **pivô** (o maior valor da coluna,
  em valor absoluto) e zeramos tudo abaixo dele com operações do tipo
  `Linha ← Linha − fator × LinhaDoPivô`. Se o maior candidato for zero em alguma coluna, as
  equações são dependentes e **a treliça é instável**.
- **Volta (substituição):** a última linha fica com 1 incógnita só. Resolvemos e vamos subindo.

A **troca de linhas** (pivotamento) existe para nunca dividir por zero e para diminuir o erro de
arredondamento.

### 1.9 Tensão normal e dimensionamento (comando "Stresses" do MDSolids)

```
σ = N / A                       (tensão normal na barra)
A necessária = |N| / σadm       (menor área que não ultrapassa a tensão admissível)
```

Em kN e mm²: 1 kN/mm² = 1000 MPa, por isso o programa multiplica por 1000.
A tração usa o σadm de tração e a compressão usa o σadm de compressão.

### 1.10 Barras de força zero (dá para ver sem conta)

- Nó **sem carga** com **2 barras não alinhadas** → as duas são zero.
- Nó **sem carga** com **3 barras, duas alinhadas** → a terceira é zero.
- Regra geral: num nó, se só **uma** barra tem componente numa direção e não há carga nem reação
  nessa direção, essa barra é zero.

Uma barra de força zero não é inútil: ela trava a estrutura, segura outros carregamentos e
diminui o comprimento de flambagem das barras comprimidas.

---

## 2. Como obter os dados (do enunciado para a tela)

1. **Escolha uma origem** (normalmente o apoio da esquerda em (0; 0)).
2. **Dê nome aos nós** na ordem em que aparecem. O programa usa letras automáticas A, B, C…,
   então cadastre os nós na mesma ordem das letras do enunciado.
3. **Calcule as coordenadas** de cada nó a partir das cotas da figura (vãos e alturas).
4. **Apoios:** pino → "Fixo"; rolete sobre o chão → "Rolete (só Ry)"; rolete numa parede →
   "Rolete (só Rx)".
5. **Cargas:** escreva as componentes. Para baixo é Fy negativo. Para uma carga inclinada F com
   ângulo θ medido a partir da horizontal: `Fx = F·cos θ`, `Fy = F·sen θ` (com o sinal do sentido).
6. **Barras:** uma linha para cada barra, escolhendo os dois nós.
7. **Unidades:** escolha o sistema (kN–mm–mm²–MPa, que é o padrão e o dos exercícios da lista,
   kN–m–mm²–MPa, N–mm–mm²–MPa, kip–ft–in²–ksi ou lb–in–in²–psi). As forças saem **na mesma
   unidade da carga**.
8. (Opcional) **Área** das barras e **σadm** para o cálculo de tensões.
9. **Calcular.**

> A unidade de comprimento **não muda as forças**: as coordenadas só entram como razões
> (cos θ e sen θ). Ela só aparece no comprimento das barras.

---

## 3. Exemplo 1 — Triângulo (o exemplo principal)

### 3.1 Enunciado

```
            10 kN
              ↓
              C (2; 3)
             / \
            /   \
           /     \
    (0;0) A───────B (4; 0)
         pino    rolete
```

### 3.2 Entrada no programa (seletor "1. Triângulo simples")

| Nó | x | y | Apoio | Fx | Fy |
|---|---|---|---|---|---|
| A | 0 | 0 | Fixo (Ax, Ay) | 0 | 0 |
| B | 4 | 0 | Rolete (By) | 0 | 0 |
| C | 2 | 3 | Livre | 0 | −10 |

Barras: AB, AC, BC. Área 100 mm² em todas e σadm = 50 MPa (tração e compressão).

### 3.3 Resolução à mão (como no caderno)

**Geometria**

| Barra | Δx | Δy | L | cos θ | sen θ |
|---|---|---|---|---|---|
| AB | 4 | 0 | 4 | 1 | 0 |
| AC | 2 | 3 | √13 = 3,6056 | 0,5547 | 0,8321 |
| BC | −2 | 3 | 3,6056 | −0,5547 | 0,8321 |

**Reações (equilíbrio da treliça inteira)**

```
ΣMA = 0:  By·4 − 10·2 = 0      →  By = 5 kN  ↑
ΣFy = 0:  Ay + By − 10 = 0     →  Ay = 5 kN  ↑
ΣFx = 0:  Ax = 0
```

**Nó C** (só 2 incógnitas: NAC e NBC). Vistas de C, as barras apontam para A (−0,5547; −0,8321)
e para B (0,5547; −0,8321):

```
ΣFx = 0:  −0,5547·NAC + 0,5547·NBC = 0              →  NAC = NBC
ΣFy = 0:  −0,8321·NAC − 0,8321·NBC − 10 = 0          →  −1,6641·NAC = 10
                                                      →  NAC = NBC = −6,009 kN  (compressão)
```

**Nó A.** Vistas de A, as barras apontam para B (1; 0) e para C (0,5547; 0,8321):

```
ΣFx = 0:  NAB + 0,5547·NAC + Ax = 0   →  NAB = −0,5547·(−6,009) = +3,333 kN  (tração)
ΣFy = 0:  0,8321·NAC + Ay = 0          →  0,8321·(−6,009) + 5 = 0  ✓ (confere)
```

Valores exatos: NAB = 10/3 kN e NAC = NBC = −5√13/3 kN.

### 3.4 Como o programa entende este exemplo (aba "Cálculo passo a passo")

**Passo 2 — incógnitas e equações**

```
n = 3  →  2n = 6 equações
b = 3, r = 3 (Ax, Ay, By)  →  b + r = 6 incógnitas   →  isostática
x = [ NAB, NAC, NBC, Ax, Ay, By ]
```

**Passo 4 — equações que o programa escreve (iguais às feitas à mão)**

```
Nó A:  ΣFx:  NAB + 0,5547·NAC + Ax = 0
       ΣFy:  0,8321·NAC + Ay = 0
Nó B:  ΣFx:  −NAB − 0,5547·NBC = 0
       ΣFy:  0,8321·NBC + By = 0
Nó C:  ΣFx:  −0,5547·NAC + 0,5547·NBC = 0
       ΣFy:  −0,8321·NAC − 0,8321·NBC − 10 = 0
```

**Passo 5 — a matriz [A]·{x} = {c}** (a carga muda de lado, por isso c = −carga)

```
           NAB      NAC      NBC      Ax       Ay       By    |   c
A: ΣFx   1,0000   0,5547   0        1,0000   0        0      |   0
A: ΣFy   0        0,8321   0        0        1,0000   0      |   0
B: ΣFx  −1,0000   0       −0,5547   0        0        0      |   0
B: ΣFy   0        0        0,8321   0        0        1,0000 |   0
C: ΣFx   0       −0,5547   0,5547   0        0        0      |   0
C: ΣFy   0       −0,8321  −0,8321   0        0        0      |  10
```

**Passo 6 — eliminação de Gauss (10 operações)**

```
 1. L3 ← L3 − (−1,0000) × L1
 2. L3 ← L3 − (0,6667) × L2
 3. L5 ← L5 − (−0,6667) × L2
 4. L6 ← L6 − (−1,0000) × L2
 5. L3 ↔ L4            (troca: o maior pivô da coluna NBC está na linha 4)
 6. L4 ← L4 − (−0,6667) × L3
 7. L5 ← L5 − (0,6667) × L3
 8. L6 ← L6 − (−1,0000) × L3
 9. L5 ↔ L6            (troca de novo)
10. L6 ← L6 − (0,6667) × L5
```

Matriz escalonada (tudo abaixo da diagonal é zero):

```
       NAB      NAC      NBC      Ax       Ay       By     |   c
L1   1,0000   0,5547   0        1,0000   0        0       |   0
L2   0        0,8321   0        0        1,0000   0       |   0
L3   0        0        0,8321   0        0        1,0000  |   0
L4   0        0        0        1,0000  −0,6667   0,6667  |   0
L5   0        0        0        0        1,0000   1,0000  |  10
L6   0        0        0        0        0       −1,3333  |  −6,667
```

> Repare: a linha L5 virou **Ay + By = 10**, que é o equilíbrio vertical da treliça inteira. A
> eliminação "redescobre" sozinha as equações que usamos à mão.

Volta (substituição), de baixo para cima:

```
By  = (−6,6667 − 0)        ÷ (−1,3333) = 5,0000
Ay  = (10,0000 − 5,0000)   ÷ 1,0000    = 5,0000
Ax  = (0 − 0)              ÷ 1,0000    = 0,0000
NBC = (0 − 5,0000)         ÷ 0,8321    = −6,0093
NAC = (0 − 5,0000)         ÷ 0,8321    = −6,0093
NAB = (0 − (−3,3333))      ÷ 1,0000    = 3,3333
```

**Passo 8 — prova real:** o programa coloca os valores de volta nas 6 equações (todas dão 0) e
confere ΣFx = ΣFy = ΣM = 0 da treliça inteira.

**Passo 9 — tensões** (A = 100 mm², σadm = 50 MPa)

```
σAB = 3,333 × 1000 ÷ 100 = +33,33 MPa   ≤ 50  → OK
σAC = −6,009 × 1000 ÷ 100 = −60,09 MPa  > 50  → excede
A necessária (AC) = 6,009 × 1000 ÷ 50 = 120,19 mm²
```

### 3.5 Interpretação

- As **duas diagonais estão comprimidas** (−6,009 kN): a carga em C "empurra" as barras para baixo.
- A **barra de baixo está tracionada** (+3,333 kN): ela impede que A e B se afastem.
- Cada apoio leva **metade da carga** (5 kN), porque a treliça e a carga são simétricas.
- Com 100 mm², as diagonais **não passam** em 50 MPa: precisariam de pelo menos 120,2 mm².
  Barra comprimida ainda teria que ser verificada à flambagem (fora do escopo do MDSolids Trusses).

**Teste ao vivo:** mude Fy de C para −20 e clique em Calcular. Todas as forças dobram, porque o
problema é **linear**.

---

## 4. Exemplo 2 — Quadro com diagonal (força zero e reação negativa)

### 4.1 Enunciado e entrada (seletor "2. Quadro com diagonal")

```
   8 kN →  D (0;3) ─────── C (4;3)   ↓ 12 kN
           │            ╱  │
           │         ╱     │
           │      ╱        │
           │   ╱           │
          A (0;0) ─────── B (4;0)
           pino           rolete (By)
```

| Nó | x | y | Apoio | Fx | Fy |
|---|---|---|---|---|---|
| A | 0 | 0 | Fixo | 0 | 0 |
| B | 4 | 0 | Rolete (By) | 0 | 0 |
| C | 4 | 3 | Livre | 0 | −12 |
| D | 0 | 3 | Livre | 8 | 0 |

Barras: AB, BC, CD, AD, AC (a diagonal mede 5 m: cos = 0,8 e sen = 0,6).
Contagem: b + r = 5 + 3 = 8 = 2·4 → isostática.

### 4.2 À mão

**Reações**

```
ΣFx = 0:  Ax + 8 = 0                            →  Ax = −8 kN  (aponta para a ESQUERDA)
ΣMA = 0:  4·By + 4·(−12) − 3·8 = 0             →  By = 18 kN ↑
ΣFy = 0:  Ay + 18 − 12 = 0                      →  Ay = −6 kN  (aponta para BAIXO)
```

**Nó B** (barras AB e BC, reação By):

```
ΣFx:  −NAB = 0           →  NAB = 0          (força zero!)
ΣFy:  NBC + By = 0       →  NBC = −18 kN     (compressão)
```

**Nó D** (barras CD e AD, carga 8 kN →):

```
ΣFx:  NCD + 8 = 0        →  NCD = −8 kN      (compressão)
ΣFy:  −NAD = 0           →  NAD = 0          (força zero!)
```

**Nó C** (diagonal vista de C aponta para A: (−0,8; −0,6)):

```
ΣFy:  −NBC − 0,6·NAC − 12 = 0   →  18 − 0,6·NAC − 12 = 0  →  NAC = +10 kN  (tração)
ΣFx:  −NCD − 0,8·NAC = 0        →  8 − 8 = 0  ✓
```

**Nó A** (prova real): ΣFx = 0 + 0,8·10 − 8 = 0 ✓ e ΣFy = 0 + 0,6·10 − 6 = 0 ✓

### 4.3 Equações que o programa escreve

```
Nó A:  NAB + 0,8·NAC + Ax = 0        |  NAD + 0,6·NAC + Ay = 0
Nó B:  −NAB = 0                       |  NBC + By = 0
Nó C:  −NCD − 0,8·NAC = 0             |  −NBC − 0,6·NAC − 12 = 0
Nó D:  NCD + 8 = 0                    |  −NAD = 0
```

### 4.4 Interpretação

- **AB e AD são barras de força zero** (cinza tracejado no desenho). Em B, AB é a única barra
  horizontal e o rolete não segura na horizontal, então AB = 0. Em D, AD é a única vertical e
  não há carga vertical, então AD = 0.
- **Reação negativa não é erro:** Ay = −6 kN quer dizer que o pino **segura a treliça para baixo**.
  O vento de 8 kN tenta tombar a treliça para a direita, e o apoio A impede que ela levante.
  No desenho, a seta verde de Ay aponta para baixo.

---

## 5. Exemplo 3 — Ponte Pratt com 3 painéis (sistema 12 × 12)

### 5.1 Enunciado e entrada (seletor "3. Ponte Pratt")

```
              E (3;4) ───── F (6;4)
             ╱ │          ╱ │ ╲
            ╱  │       ╱    │  ╲
           ╱   │    ╱       │   ╲
   A (0;0) ─── B (3;0) ───── C (6;0) ─── D (9;0)
   pino        ↓ 30 kN       ↓ 15 kN     rolete
```

Barras: AB, BC, CD, AE, EF, DF, BE, CF, BF. Inclinadas 3-4-5: cos = 0,6 e sen = 0,8.
b + r = 9 + 3 = 12 = 2·6 → isostática, **12 equações e 12 incógnitas**.

### 5.2 À mão (ordem dos nós: A → D → E → C → B, e F confere)

```
Reações:  ΣMA: 9·Dy − 3·30 − 6·15 = 0  → Dy = 20 kN ;  Ay = 45 − 20 = 25 kN ;  Ax = 0

Nó A:  0,8·NAE + 25 = 0              → NAE = −31,25 kN (C)
       NAB + 0,6·(−31,25) = 0        → NAB = +18,75 kN (T)
Nó D:  0,8·NDF + 20 = 0              → NDF = −25,00 kN (C)
       −NCD − 0,6·(−25) = 0          → NCD = +15,00 kN (T)
Nó E:  −0,6·(−31,25) + NEF = 0       → NEF = −18,75 kN (C)
       −0,8·(−31,25) − NBE = 0       → NBE = +25,00 kN (T)
Nó C:  NCF − 15 = 0                  → NCF = +15,00 kN (T)
       −NBC + NCD = 0                → NBC = +15,00 kN (T)
Nó B:  NBE + 0,8·NBF − 30 = 0        → NBF = +6,25 kN  (T)
       −18,75 + 15 + 0,6·6,25 = 0    ✓
Nó F:  18,75 − 15 − 3,75 = 0 ✓   e   20 − 15 − 5 = 0 ✓
```

### 5.3 O que dizer na banca

- À mão foi preciso **escolher a ordem dos nós** com cuidado. O programa não escolhe nada: monta as
  12 equações e o Gauss resolve em 23 operações de linha.
- **Banzo superior (AE, EF, DF) comprimido e banzo inferior (AB, BC, CD) tracionado**, como numa
  viga biapoiada: a parte de cima encurta e a de baixo alonga.
- A maior força é **AE = −31,25 kN**, a barra mais crítica (compressão, então também flambagem).

---

## 6. Casos de erro (o MDSolids recusa os três)

| Exemplo no seletor | Contagem | O que o programa diz | Por quê |
|---|---|---|---|
| Erro 1 (dois roletes) | b + r = 3 + 2 = 5 < 6 | **hipostática** | nada segura a treliça na horizontal, ela escorrega |
| Erro 2 (dois pinos) | b + r = 3 + 4 = 7 > 6 | **hiperestática** | 7 incógnitas e 6 equações: precisaria das deformações (E·A), que o MDSolids não usa |
| Erro 3 (quadrado sem diagonal) | b + r = 4 + 4 = 8 = 8 | **geometricamente instável** | a conta fecha, mas o quadrado vira losango. No Gauss, a coluna **Bx** fica sem pivô diferente de zero: as equações são dependentes |

No Erro 3 o "Cálculo passo a passo" mostra até onde o Gauss chegou e em que coluna parou. É a
melhor prova de que **contar não basta**.

---

## 7. Demonstração ao vivo (cliques)

1. Abrir `index.html` (duplo clique, sem instalar nada).
2. Exemplo 1 → **Calcular** → mostrar cores (azul tração, vermelho compressão), setas verdes das
   reações e a tabela.
3. Aba **Cálculo passo a passo** → percorrer os Passos 1 a 9 (seção 3.4 deste roteiro).
4. Mudar Fy de C para −20 → Calcular → tudo dobra (linearidade).
5. Exemplo 2 → força zero tracejada e reações negativas.
6. Erros 1, 2 e 3 → mensagens.
7. **Montar do zero** (mostra a entrada de dados): Nova → 3× "+ Nó":
   A (0; 0) fixo, B (6; 0) rolete, C (3; 4) com Fx = 5 e Fy = −20 → 3× "+ Barra" (AB, AC, BC) → Calcular.
   Resposta: Ax = −5, Ay = 6,667, By = 13,333, AB = +10, AC = −8,333, BC = −16,667 kN.
   Prova rápida: ΣMA = 6·By − 3·20 − 4·5 = 0 → By = 80/6 = 13,333 ✓

---

## 8. Perguntas prováveis do professor

**Por que as barras só têm força axial?**
Os nós são pinos (sem momento) e as cargas estão só nos nós. Uma barra com duas forças só fica em
equilíbrio se elas forem iguais, opostas e na linha da barra.

**Por que vocês supõem tração?**
É uma convenção. Supondo tração, o sinal do resultado já diz o estado: positivo é tração,
negativo é compressão.

**b + r = 2n garante que dá para resolver?**
Não. É necessário, mas não suficiente. O Erro 3 fecha a conta e é instável. O programa percebe
isso porque o Gauss não encontra pivô diferente de zero.

**Por que Gauss e não resolver nó a nó como no caderno?**
Nó a nó depende de achar um nó com no máximo 2 incógnitas, e nem sempre existe. O sistema
completo funciona para qualquer treliça isostática e dá o mesmo resultado.

**Para que serve a troca de linhas?**
Para não dividir por zero (muitos coeficientes da matriz são zero) e para reduzir o erro de
arredondamento, usando sempre o maior pivô.

**As reações não deveriam ser calculadas antes?**
À mão costumamos calcular antes. No programa elas são incógnitas como as outras. As 3 equações de
equilíbrio global são a soma das equações dos nós, então já estão dentro do sistema. O Passo 8
mostra ΣFx = ΣFy = ΣM = 0 como prova.

**E a treliça hiperestática?**
Tem mais incógnitas que equações. Para resolver seria preciso considerar a deformação das barras
(módulo de elasticidade e área, método da rigidez). O MDSolids Trusses também recusa.

**O resultado depende da área ou do material?**
Na isostática, não: N vem só do equilíbrio. A área só entra depois, para a tensão σ = N/A.

**Como entram cargas inclinadas?**
Pelas componentes: Fx = F·cos θ e Fy = F·sen θ.

**Qual a precisão?**
O programa coloca a resposta de volta em todas as equações (Passo 8). Os resíduos ficam na casa de
10⁻¹⁵, que é o arredondamento do computador.

**Limitações**
Não verifica flambagem das barras comprimidas, não resolve hiperestáticas, não calcula
deslocamentos e só aceita cargas nos nós. As mesmas limitações do módulo Trusses do MDSolids.

---

## 9. Paridade com o MDSolids (requisito "no mínimo as mesmas funcionalidades")

| Funcionalidade do MDSolids Trusses | Neste projeto |
|---|---|
| Definir nós (pontos da grade) | tabela de nós com x e y |
| Barras ligando nós | tabela de barras |
| Apoio pino e rolete (em x ou em y) | Fixo, Rolete (só Ry), Rolete (só Rx) |
| Cargas nodais em x e y | Fx e Fy em cada nó |
| Letras automáticas nos nós | A, B, C… |
| Verificação b + r = 2n | Passo 2 e mensagem |
| Recusa de treliça hiperestática | mensagem "hiperestática" |
| Recusa de treliça instável | mensagem "geometricamente instável" e coluna sem pivô |
| Reações de apoio | tabela e setas verdes no desenho |
| Forças nas barras, + tração / − compressão | tabela, cores e valores no desenho |
| Destaque de barras de força zero | cinza tracejado e lista |
| Tensão normal σ = N/A com área por barra | coluna σ |
| Área necessária para uma tensão admissível | coluna "A nec." (σadm de tração e de compressão) |
| Unidades SI e americanas | 4 sistemas de unidades |
| Imprimir resultados | botão Imprimir |
| Salvar e abrir | botões Salvar e Abrir (arquivo .json) |
| — (não existe no MDSolids) | **aba "Cálculo passo a passo"** |

Diferença assumida: no MDSolids a geometria é desenhada com o mouse sobre uma grade. Aqui as
coordenadas são digitadas numa tabela, e o resultado é o mesmo.

---

## 10. Exercícios da lista do professor (bateria de testes)

Os 5 exercícios da lista estão no seletor "Exemplo" como **Lista — Exercício 1** a **5**.
Todos são isostáticos e a prova real dá zero em todos.

### 10.1 Como ler a figura e digitar

1. **Unidades:** "kN, mm, mm², MPa" (já é o padrão do programa).
2. **Coordenadas:** cada linha da grade vale 100 mm. Leia x no eixo de cima e y no eixo da esquerda.
3. **Confira com o ângulo desenhado:** `tan(ângulo) = Δy / Δx`. Exemplo: 63,435° → 600/300 = 2 → tan 63,435° = 2 ✓.
   Ângulos comuns: 45° → 1:1 · 56,310° → 3:2 · 63,435° → 2:1 · 71,565° → 3:1 · 80,538° → 6:1 ·
   83,660° → 9:1 · 75,964° → 4:1 · 74,055° → 7:2 · 33,690° → 2:3 · 26,565° → 1:2 · 18,435° → 1:3 ·
   11,310° → 1:5 (sempre Δy : Δx).
4. **Apoios:** triângulo sobre hachura → **Fixo / pino**; bolinha (círculo) → **Rolete (só Ry)**.
5. **Cargas:** olhe para **onde a ponta da seta aponta**.
   - ponta para baixo → Fy **negativo**; ponta para cima → Fy **positivo**;
   - ponta para a direita → Fx **positivo**; ponta para a esquerda → Fx **negativo**.
6. **Cadastre os nós na ordem A, B, C…**, porque as letras são automáticas. Os nós não precisam
   estar em ordem de posição.
7. **Barras:** cadastre na ordem do formulário. O nome sai sempre em ordem alfabética
   (de C para B vira "BC"), e a tabela de resultados também sai em ordem alfabética.
8. **Para responder no formulário:** digite o **valor sem o sinal** e escolha o tipo no menu
   (o sinal + / − do programa já diz se é tração ou compressão). *(Confirme com o professor se o
   campo espera o valor com ou sem sinal.)*

### 10.2 Exercício 1 — conferido à mão

Dados: A (100; 200) fixo · B (400; 800) com 22 kN → e 15 kN ↓ · C (1000; 200) rolete.
Barras AB, AC, BC.

```
Reações:
ΣFx = 0:  Ax + 22 = 0                                 →  Ax = −22,000 kN
ΣMA = 0:  900·Cy + 300·(−15) − 600·22 = 0             →  Cy = 17700 / 900 = 19,667 kN
ΣFy = 0:  Ay + 19,667 − 15 = 0                        →  Ay = −4,667 kN

Nó C:  barra CB aponta para (−600; 600)/848,53 = (−0,7071; 0,7071)
       ΣFy:  0,7071·NBC + 19,667 = 0                  →  NBC = −27,813 kN  (compressão)
       ΣFx:  −NAC − 0,7071·(−27,813) = 0              →  NAC = +19,667 kN  (tração)
Nó A:  barra AB aponta para (300; 600)/670,82 = (0,4472; 0,8944)
       ΣFy:  0,8944·NAB − 4,667 = 0                   →  NAB = +5,217 kN   (tração)
       ΣFx:  0,4472·5,217 + 19,667 − 22 = 0  ✓
```

### 10.3 Respostas

**Exercício 1** — reações Ax = −22,000 · Ay = −4,667 · Cy = +19,667 kN

| Barra | Valor (kN) | Tipo |
|---|---|---|
| AB | 5,217 | Tração |
| AC | 19,667 | Tração |
| BC | 27,813 | Compressão |

**Exercício 2** — A (0; 200) fixo · B (1000; 200) rolete · C (100; 800) 42 kN ↑ · D (600; 800) 11 kN → e 7,5 kN ↑
Reações Ax = −11,000 · Ay = −47,400 · By = −2,100 kN

| Barra | Valor (kN) | Tipo |
|---|---|---|
| AB | 3,100 | Tração |
| AC | 48,054 | Tração |
| BC | 9,735 | Compressão |
| BD | 9,014 | Tração |
| CD | 16,000 | Tração |

**Exercício 3** — A (0; 200) rolete · B (300; 200) 15 kN ↓ · C (1000; 200) fixo · D (100; 800) 22 kN → · E (400; 800) 30 kN → e 8,5 kN ↑
Reações Ay = −25,800 · Cx = −52,000 · Cy = +32,300 kN

| Barra | Valor (kN) | Tipo |
|---|---|---|
| AB | 4,300 | Compressão |
| AD | 26,156 | Tração |
| BC | 19,700 | Compressão |
| BD | 27,196 | Compressão |
| BE | 41,363 | Tração |
| CE | 45,679 | Compressão |
| DE | 9,100 | Compressão |

**Exercício 4** — A (0; 200) fixo · B (300; 200) 13 kN ↓ · C (600; 200) 21,5 kN → · D (1000; 200) rolete ·
E (100; 800) 14 kN ← · F (400; 800) 8 kN ↓ · G (600; 800) 12,25 kN → e 6 kN ↑
Reações Ax = −19,750 · Ay = +12,550 · Dy = +2,450 kN

| Barra | Valor (kN) | Tipo |
|---|---|---|
| AB | 21,842 | Tração |
| AE | 12,723 | Compressão |
| BC | 25,950 | Tração |
| BE | 13,229 | Tração |
| BF | 0,456 | Tração |
| CD | 1,633 | Tração |
| CF | 8,907 | Compressão |
| CG | 8,450 | Tração |
| DG | 2,945 | Compressão |
| EF | 7,725 | Tração |
| FG | 10,617 | Tração |

**Exercício 5** — A (0; 0) fixo · B (300; 100) 44,5 kN ↓ · C (500; 200) 32,5 kN ↓ · D (1000; 300) rolete ·
E (800; 500) 12 kN → e 11,6 kN ↓ · F (500; 800) 12,5 kN → e 8,7 kN ↑ · G (100; 900) 4 kN ↓ · H (300; 900) 8,5 kN → e 2,5 kN ↑
Reações Ax = −33,000 · Ay = +23,570 · Dy = +57,830 kN

| Barra | Valor (kN) | Tipo |
|---|---|---|
| AB | 38,990 | Tração |
| AG | 36,121 | Compressão |
| BC | 54,104 | Tração |
| BF | 12,478 | Compressão |
| BH | 12,732 | Tração |
| BG | 32,881 | Tração |
| CD | 49,146 | Tração |
| CE | 0,283 | Tração |
| CF | 46,858 | Tração |
| DE | 68,153 | Compressão |
| EF | 51,466 | Compressão |
| FH | 22,879 | Compressão |
| GH | 11,964 | Compressão |

> No formulário do Exercício 5, **BH vem antes de BG**. Na tela do programa a ordem é alfabética
> (BG antes de BH). Cuidado para não trocar as duas na hora de digitar.
>
> BF = 0,456 kN (Ex. 4) e CE = 0,283 kN (Ex. 5) são **pequenas, mas não são zero**: são tração.

---

## 11. Checklist do dia

- [ ] Avisar o professor **com antecedência** que vão entregar (quarta ou quinta da semana da N2).
- [ ] Estar **presente na prova N2** e **assinar a lista**: sem isso a nota não vale.
- [ ] Levar o projeto num pendrive também (é só a pasta; abre com duplo clique no `index.html`).
- [ ] Testar antes no computador da sala: abrir, escolher o Exemplo 1 e Calcular.
- [ ] Ter este roteiro aberto ou impresso, com as contas do Exemplo 1 feitas à mão no papel.
