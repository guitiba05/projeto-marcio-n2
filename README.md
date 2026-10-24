# Projeto Márcio — N2

Versão própria do módulo **Trusses (Treliças)** do software
[MdSolids](https://static-archives.git-pages.mst.edu/mdsolids/), desenvolvida como
trabalho da avaliação N2 (CEFSA).

O objetivo é entregar, no mínimo, as mesmas funcionalidades do módulo *Trusses*
original: entrada de geometria e carregamentos, cálculo de reações de apoio, esforços
normais nas barras (tração/compressão), determinação de barras de força zero e
apresentação/interpretação dos resultados.

## Status

Repositório inicializado. Escopo e enunciado documentados; implementação a iniciar.

## Estrutura do repositório

```
docs/
  enunciado.md          Texto original da proposta do trabalho
  escopo-tecnico.md     Escopo funcional e base teórica prevista
```

A estrutura de código será definida quando a linguagem/plataforma for escolhida
(sem restrição pelo enunciado).

## Requisitos do trabalho (resumo)

| Item | Peso / observação |
| --- | --- |
| Apresentação da parte teórica do modelo | 4,0 pontos — parte mais importante da nota |
| Bateria de 8 exercícios (funcionalidade e taxa de acerto) | 2,0 pontos — só ocorre se a parte teórica for aprovada |
| Trabalho em duplas (no máximo) | — |
| Entrega na semana das avaliações N2 (quarta ou quinta, horário alternativo) | Avisar antecipadamente |
| Presença na prova N2 + assinatura da lista | Condição para a nota |

Detalhes completos em [`docs/enunciado.md`](docs/enunciado.md).

## Base teórica a apresentar

- Idealização da treliça: barras biarticuladas, cargas nos nós, hipóteses de
  linearidade e pequenas deformações.
- Equilíbrio global: equações de equilíbrio externo, apoios e reações, treliças
  isostáticas, hipostáticas e hiperestáticas (grau de indeterminação).
- **Método dos nós**: equilíbrio nó a nó, ordem de resolução, convenção de
  tração/compressão.
- **Método das seções**: corte de Ritter para esforços em barras específicas.
- **Método matricial da rigidez**: matriz de rigidez da barra, matriz de
  transformação (rotação), montagem da matriz global, condições de contorno,
  resolução do sistema e recuperação dos esforços normais.
- Casos particulares: barras de força zero, simetria, cargas em nós.

## Referência

- MdSolids — módulo *Trusses*: <https://static-archives.git-pages.mst.edu/mdsolids/>
