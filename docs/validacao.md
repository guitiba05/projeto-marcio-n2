# Registro de validação

Documento gerado por `python tools/build_validation.py` a partir de `data/cases/`. Não editar à mão: rode o script.

## Como cada caso é verificado

Cada caso válido passa por seis verificações independentes:

1. **estaticidade** — `g = b + r − 2n` coerente com o esperado;
2. **esforços normais** — comparados com o gabarito gravado;
3. **reações de apoio** — comparadas com o gabarito gravado;
4. **equilíbrio global** — `ΣFx`, `ΣFy`, `ΣM` nulos;
5. **equilíbrio nodal** — resíduo em cada nó nulo;
6. **conferência cruzada** — método dos nós (equações de equilíbrio apenas, sem `EA` e sem deslocamentos) reproduz os mesmos esforços.

Os casos de erro verificam que o programa **recusa** com o código esperado, em vez de devolver número absurdo.

## Resumo da bateria

| caso | descrição | classificação | situação |
| --- | --- | --- | --- |
| `01-triangulo` | Triângulo isostático (caso canônico) | isostática (g = 0) | ✅ |
| `02-telhado-pratt` | Treliça de telhado (Pratt) com carga distribuída convertida em nodal | isostática (g = 0) | ✅ |
| `03-warren` | Treliça Warren com 3 painéis | isostática (g = 0) | ✅ |
| `04-pratt-vento` | Treliça Pratt com carga lateral (vento) | isostática (g = 0) | ✅ |
| `05-forca-zero-T` | Treliça com barras de força zero (regra R2) | isostática (g = 0) | ✅ |
| `06-forca-zero-R3` | Treliça com barras de força zero (regra R3) | isostática (g = 0) | ✅ |
| `07-geometria-irregular` | Geometria irregular (ângulos não triviais) | isostática (g = 0) | ✅ |
| `08-hiperestatica` | Treliça hiperestática de grau 1 | hiperestática (g = 1) | ✅ |
| `09-hipostatica` | Treliça hipostática (deve falhar com mensagem) | erro esperado: `hypostatic` | ✅ |
| `10-mecanismo` | Mecanismo interno com g = 0 (deve falhar com mensagem) | erro esperado: `mechanism` | ✅ |
| `11-sem-carga` | Estado trivial: treliça válida sem carregamento | isostática (g = 0) | ✅ |
| `12-pratt-grande` | Treliça de maior porte: Pratt com 6 painéis (14 nós, 25 barras) | isostática (g = 0) | ✅ |

## Detalhe por caso

### `01-triangulo` — Triângulo isostático (caso canônico)

Treliça triangular com pino em A, roleto em B e carga vertical em C. É o caso de referência com solução analítica exata: Ay = By = 5 kN, N_AB = 10/3 kN (tração) e N_AC = N_BC = -5√13/3 kN (compressão).

Estaticidade: `b + r = 3 + 3 = 6` versus `2n = 6` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `AB` | 4.000 | 3.333 | tração |
| `AC` | 3.606 | −6.009 | compressão |
| `BC` | 3.606 | −6.009 | compressão |

| apoio | Rx | Ry |
| --- | --- | --- |
| `A` | 0.000 | 5.000 |
| `B` | — | 5.000 |

Verificações: `ΣFx = 4.44e-16`, `ΣFy = 8.88e-16`, `ΣM = 3.55e-15`, resíduo nodal máximo `8.88e-16` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `0.00e+00`.

### `02-telhado-pratt` — Treliça de telhado (Pratt) com carga distribuída convertida em nodal

Telhado de duas águas com 4 painéis e carga vertical aplicada nos nós do banzo superior (equivalente a uma carga distribuída sobre a cobertura). Exercita conversão de carregamento e múltiplos nós carregados.

Estaticidade: `b + r = 13 + 3 = 16` versus `2n = 16` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `AC1` | 2.000 | 6.400 | tração |
| `C1C2` | 2.000 | 6.400 | tração |
| `C2C3` | 2.000 | 6.400 | tração |
| `C3E` | 2.000 | 6.400 | tração |
| `AT1` | 3.202 | −10.245 | compressão |
| `T1T2` | 2.062 | −8.246 | compressão |
| `T2T3` | 2.062 | −8.246 | compressão |
| `T3E` | 3.202 | −10.245 | compressão |
| `C1T1` | 2.500 | 0.000 | força zero |
| `C2T2` | 3.000 | −4.000 | compressão |
| `C3T3` | 2.500 | 0.000 | força zero |
| `T1C2` | 3.202 | 2.561 | tração |
| `T3C2` | 3.202 | 2.561 | tração |

| apoio | Rx | Ry |
| --- | --- | --- |
| `A` | 0.000 | 8.000 |
| `E` | — | 8.000 |

Verificações: `ΣFx = -1.42e-14`, `ΣFy = -1.24e-14`, `ΣM = -1.42e-14`, resíduo nodal máximo `1.24e-14` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `1.42e−14`.

Barras de força zero: `C1T1`, `C3T3`.

### `03-warren` — Treliça Warren com 3 painéis

Banzo inferior reto, banzo superior com montantes inclinados em zigue-zague. Carregamento simétrico nos nós superiores; os resultados devem sair simétricos.

Estaticidade: `b + r = 11 + 3 = 14` versus `2n = 14` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `B0B1` | 2.000 | 7.500 | tração |
| `B1B2` | 2.000 | 12.500 | tração |
| `B2B3` | 2.000 | 7.500 | tração |
| `T0T1` | 2.000 | −10.000 | compressão |
| `T1T2` | 2.000 | −10.000 | compressão |
| `B0T0` | 2.236 | −16.771 | compressão |
| `T0B1` | 2.236 | 5.590 | tração |
| `B1T1` | 2.236 | −5.590 | compressão |
| `T1B2` | 2.236 | −5.590 | compressão |
| `B2T2` | 2.236 | 5.590 | tração |
| `T2B3` | 2.236 | −16.771 | compressão |

| apoio | Rx | Ry |
| --- | --- | --- |
| `B0` | 0.000 | 15.000 |
| `B3` | — | 15.000 |

Verificações: `ΣFx = 7.11e-15`, `ΣFy = -5.33e-15`, `ΣM = -2.84e-14`, resíduo nodal máximo `1.26e-14` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `1.07e−14`.

### `04-pratt-vento` — Treliça Pratt com carga lateral (vento)

Banzo superior reto, montantes verticais e diagonais. Carga vertical nos nós internos mais uma força horizontal no nó superior da extremidade. O roleto em B3 não resiste a esforço horizontal, então toda a componente horizontal vai para o pino em B0.

Estaticidade: `b + r = 13 + 3 = 16` versus `2n = 16` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `B0B1` | 2.000 | 8.000 | tração |
| `B1B2` | 2.000 | 15.333 | tração |
| `B2B3` | 2.000 | 12.667 | tração |
| `T0T1` | 2.000 | −7.333 | compressão |
| `T1T2` | 2.000 | −4.667 | compressão |
| `T2T3` | 2.000 | 8.000 | tração |
| `B0T0` | 2.000 | −7.333 | compressão |
| `B1T1` | 2.000 | −7.333 | compressão |
| `B2T2` | 2.000 | 2.667 | tração |
| `B3T3` | 2.000 | 0.000 | força zero |
| `T0B1` | 2.828 | 10.371 | tração |
| `T1B2` | 2.828 | −3.771 | compressão |
| `T2B3` | 2.828 | −17.913 | compressão |

| apoio | Rx | Ry |
| --- | --- | --- |
| `B0` | −8.000 | 7.333 |
| `B3` | — | 12.667 |

Verificações: `ΣFx = -7.11e-15`, `ΣFy = -1.42e-14`, `ΣM = -1.42e-14`, resíduo nodal máximo `1.00e-14` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `1.42e−14`.

Barras de força zero: `B3T3`.

### `05-forca-zero-T` — Treliça com barras de força zero (regra R2)

Painel quadrado com uma diagonal e um nó superior sem carga e sem vínculo (nó D). Pela regra R2, as duas barras que chegam em D (CD e DA) têm força zero. Serve para mostrar que a regra é geométrica e não depende da carga.

Estaticidade: `b + r = 5 + 3 = 8` versus `2n = 8` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `AB` | 4.000 | 0.000 | força zero |
| `BC` | 3.000 | −14.500 | compressão |
| `CD` | 4.000 | 0.000 | força zero |
| `DA` | 3.000 | 0.000 | força zero |
| `AC` | 5.000 | 7.500 | tração |

| apoio | Rx | Ry |
| --- | --- | --- |
| `A` | −6.000 | −4.500 |
| `B` | — | 14.500 |

Verificações: `ΣFx = -2.66e-15`, `ΣFy = 0.00e+00`, `ΣM = 7.11e-15`, resíduo nodal máximo `3.55e-15` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `3.55e−15`.

Barras de força zero: `AB`, `CD`, `DA`.

### `06-forca-zero-R3` — Treliça com barras de força zero (regra R3)

Nó C no meio do banzo inferior recebe três barras, sendo duas colineares (AC e CB). Pela regra R3, a terceira barra (CT, o montante central) tem força zero — mas continua com rigidez, o que é uma distinção importante.

Estaticidade: `b + r = 5 + 3 = 8` versus `2n = 8` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `AC` | 2.000 | 3.333 | tração |
| `CB` | 2.000 | 3.333 | tração |
| `CT` | 3.000 | 0.000 | força zero |
| `AT` | 3.606 | −6.009 | compressão |
| `BT` | 3.606 | −6.009 | compressão |

| apoio | Rx | Ry |
| --- | --- | --- |
| `A` | 0.000 | 5.000 |
| `B` | — | 5.000 |

Verificações: `ΣFx = -4.44e-16`, `ΣFy = 1.78e-15`, `ΣM = 3.55e-15`, resíduo nodal máximo `3.55e-15` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `1.78e−15`.

Barras de força zero: `CT`.

### `07-geometria-irregular` — Geometria irregular (ângulos não triviais)

Treliça com nós fora de alinhamento ortogonal: ângulos não triviais nos cossenos diretores e duas cargas inclinadas em nós distintos.

Estaticidade: `b + r = 5 + 3 = 8` versus `2n = 8` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `AB` | 5.000 | 2.800 | tração |
| `AC` | 3.162 | −10.752 | compressão |
| `CD` | 3.162 | 0.632 | tração |
| `DB` | 2.236 | −6.261 | compressão |
| `AD` | 4.472 | −0.447 | compressão |

| apoio | Rx | Ry |
| --- | --- | --- |
| `A` | 1.000 | 10.400 |
| `B` | — | 5.600 |

Verificações: `ΣFx = 0.00e+00`, `ΣFy = 8.88e-16`, `ΣM = 3.55e-15`, resíduo nodal máximo `2.81e-15` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `2.66e−15`.

### `08-hiperestatica` — Treliça hiperestática de grau 1

Quadrado com as duas diagonais: b + r = 6 + 3 = 9 > 2n = 8, grau 1. O método dos nós não resolve (sistema não quadrado); o método da rigidez resolve, mas os esforços passam a depender de EA.

Estaticidade: `b + r = 6 + 3 = 9` versus `2n = 8` → **hiperestática**, grau `1`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `AB` | 4.000 | 1.036 | tração |
| `BC` | 4.000 | −8.964 | compressão |
| `CD` | 4.000 | 1.036 | tração |
| `DA` | 4.000 | 1.036 | tração |
| `AC` | 5.657 | −1.464 | compressão |
| `BD` | 5.657 | −1.464 | compressão |

| apoio | Rx | Ry |
| --- | --- | --- |
| `A` | 0.000 | 0.000 |
| `B` | — | 10.000 |

Verificações: `ΣFx = 8.88e-16`, `ΣFy = 1.78e-15`, `ΣM = 0.00e+00`, resíduo nodal máximo `1.55e-15` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `n/a (hiperestática)`.

### `09-hipostatica` — Treliça hipostática (deve falhar com mensagem)

Triângulo com pino em A e nenhum vínculo em B: b + r = 3 + 2 = 5 < 2n = 6. Falta um vínculo — é um mecanismo. O programa deve recusar o cálculo com mensagem clara, não devolver números absurdos.

**Resultado:** recusado com código `hypostatic` — A treliça é hipostática (grau -1). b + r = 3 + 2 = 5 < 2n = 6. Faltam 1 vínculo(s): a estrutura é um mecanismo e não pode ser resolvida apenas pelo equilíbrio.

### `10-mecanismo` — Mecanismo interno com g = 0 (deve falhar com mensagem)

Nó B no meio de dois pinos A e C, com apenas as barras AB e CB, ambas colineares. A contagem dá b + r = 2 + 4 = 6 = 2n, ou seja g = 0, mas B pode se deslocar verticalmente sem resistência de primeira ordem: a matriz de rigidez é singular. Prova que a contagem não garante estabilidade.

**Resultado:** recusado com código `mechanism` — A treliça tem mecanismo interno: a matriz de rigidez é singular, ou seja, existe deslocamento sem resistência nos GDL [B.uy]. A contagem b + r - 2n não garante estabilidade; adicione barras ou vínculos.

### `11-sem-carga` — Estado trivial: treliça válida sem carregamento

Mesma geometria do caso 1, sem nenhuma carga aplicada. Todas as barras devem ficar com força zero e todas as reações nulas.

Estaticidade: `b + r = 3 + 3 = 6` versus `2n = 6` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `AB` | 4.000 | 0.000 | força zero |
| `AC` | 3.606 | 0.000 | força zero |
| `BC` | 3.606 | 0.000 | força zero |

| apoio | Rx | Ry |
| --- | --- | --- |
| `A` | 0.000 | 0.000 |
| `B` | — | 0.000 |

Verificações: `ΣFx = 0.00e+00`, `ΣFy = 0.00e+00`, `ΣM = 0.00e+00`, resíduo nodal máximo `0.00e+00` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `0.00e+00`.

Barras de força zero: `AB`, `AC`, `BC`.

### `12-pratt-grande` — Treliça de maior porte: Pratt com 6 painéis (14 nós, 25 barras)

Treliça de ponte com 6 painéis, 14 nós e 25 barras, carga distribuída convertida em cargas nodais no banzo superior. Verifica escala, legibilidade do diagrama e desempenho.

Estaticidade: `b + r = 25 + 3 = 28` versus `2n = 28` → **isostática**, grau `0`.

| barra | L | N | estado |
| --- | --- | --- | --- |
| `B0B1` | 2.000 | 0.000 | força zero |
| `T0T1` | 2.000 | −13.333 | compressão |
| `B1B2` | 2.000 | 13.333 | tração |
| `T1T2` | 2.000 | −21.333 | compressão |
| `B2B3` | 2.000 | 21.333 | tração |
| `T2T3` | 2.000 | −24.000 | compressão |
| `B3B4` | 2.000 | 21.333 | tração |
| `T3T4` | 2.000 | −24.000 | compressão |
| `B4B5` | 2.000 | 13.333 | tração |
| `T4T5` | 2.000 | −21.333 | compressão |
| `B5B6` | 2.000 | 0.000 | força zero |
| `T5T6` | 2.000 | −13.333 | compressão |
| `B0T0` | 3.000 | −20.000 | compressão |
| `B1T1` | 3.000 | −20.000 | compressão |
| `B2T2` | 3.000 | −12.000 | compressão |
| `B3T3` | 3.000 | −8.000 | compressão |
| `B4T4` | 3.000 | −12.000 | compressão |
| `B5T5` | 3.000 | −20.000 | compressão |
| `B6T6` | 3.000 | −20.000 | compressão |
| `T0B1` | 3.606 | 24.037 | tração |
| `T6B5` | 3.606 | 24.037 | tração |
| `T1B2` | 3.606 | 14.422 | tração |
| `T5B4` | 3.606 | 14.422 | tração |
| `T2B3` | 3.606 | 4.807 | tração |
| `T4B3` | 3.606 | 4.807 | tração |

| apoio | Rx | Ry |
| --- | --- | --- |
| `B0` | 0.000 | 20.000 |
| `B6` | — | 20.000 |

Verificações: `ΣFx = 2.95e-14`, `ΣFy = 2.24e-13`, `ΣM = 1.42e-12`, resíduo nodal máximo `6.98e-14` → **equilíbrio verificado**.

Conferência pelo método dos nós: diferença máxima `1.63e−13`.

Barras de força zero: `B0B1`, `B5B6`.

## Como reproduzir

```powershell
python -m pytest -q                 # toda a suíte
python tools/build_cases.py         # regera os gabaritos e revalida
python tools/build_validation.py    # regera este documento
```
