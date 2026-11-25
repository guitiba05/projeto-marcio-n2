# Treliças Planas — versão do módulo Trusses do MDSolids

Trabalho da avaliação N2 (CEFSA): uma versão própria do módulo **Trusses (Treliças)** do
[MDSolids](https://static-archives.git-pages.mst.edu/mdsolids/).

O programa recebe uma treliça plana (nós, apoios, cargas e barras) e calcula:

- a classificação **isostática / hipostática / hiperestática** (b + r comparado com 2n);
- as **reações de apoio**;
- a **força em cada barra**, com **tração (+)**, **compressão (−)** ou **força zero**;
- a **tensão normal σ = N/A** e a **área necessária** para uma tensão admissível;
- o **cálculo passo a passo**, com as equações de cada nó, a matriz, a eliminação de Gauss e a
  prova real.

## Como abrir

Não precisa instalar nada. **Dê duplo clique em `index.html`** e ele abre no navegador.

1. Escolha um **Exemplo** pronto ou clique em **Nova**.
2. Preencha os **nós** (x, y, apoio e cargas) e as **barras**. O nome do nó pode ser editado.
   Para carga inclinada, use o quadro **Carga inclinada** (módulo e ângulo). Para posicionar um nó pelo
   ângulo da figura, use o quadro **Posicionar nó por ângulo**.
3. Clique em **Calcular**.
4. Veja a aba **Resultados** e a aba **Cálculo passo a passo**.

## Como o cálculo funciona (resumo)

1. Cada nó dá 2 equações: **ΣFx = 0** e **ΣFy = 0** (método dos nós).
2. Cada barra é 1 incógnita (N, suposta em tração) e cada reação é 1 incógnita.
3. Se **b + r = 2n**, o sistema é quadrado: **[A]·{x} = {c}**.
4. O sistema é resolvido por **eliminação de Gauss** com troca de linhas.
5. O resultado é conferido colocando os valores de volta em todas as equações.

## Arquivos

```
index.html               a página
css/estilo.css           aparência
js/calculo.js            ★ todo o cálculo (método dos nós + Gauss + tensões)
js/exemplos.js           exemplos prontos
js/formatar.js           formatação de números
js/desenho.js            desenho da treliça
js/passo-a-passo.js      texto da aba "Cálculo passo a passo"
js/posicionar-no.js      quadro "Posicionar nó por ângulo"
js/tela.js               liga a tela ao cálculo
docs/ROTEIRO_APRESENTACAO.md   ★ roteiro da apresentação com exemplos resolvidos à mão
docs/COMO_O_CODIGO_FUNCIONA.md explicação do código, função por função
docs/enunciado.md              texto da proposta do trabalho
```

## Convenções

- **N > 0 é tração, N < 0 é compressão** (igual ao MDSolids: *Tension (+)*, *Compression (−)*).
- Fx positivo aponta para a direita e Fy positivo aponta para cima. Carga para baixo é Fy negativo.
- Treliça hiperestática e treliça instável são **recusadas com mensagem**, como no MDSolids.

## Requisitos do trabalho

| Item | Peso / observação |
| --- | --- |
| Apresentação da parte teórica do modelo | 4,0 pontos (a parte mais importante) |
| Bateria de 8 exercícios | 2,0 pontos (só se a parte teórica for aprovada) |
| Trabalho em duplas (no máximo) | — |
| Entrega na semana da N2 (quarta ou quinta, horário alternativo) | avisar antes |
| Presença na prova N2 + assinatura da lista | condição para a nota |
