# Como o código funciona

O programa é uma página web comum: **HTML + CSS + JavaScript**, sem servidor, sem biblioteca e
sem instalação. Abrir o `index.html` no navegador já basta.

## 1. Mapa dos arquivos

```
index.html            a página: tabelas de entrada, desenho e abas de resultado
css/estilo.css        aparência (cores, tabelas, layout)
js/calculo.js         ★ O CÁLCULO. Não sabe nada de tela: recebe a treliça e devolve números
js/exemplos.js        treliças prontas do seletor "Exemplo"
js/formatar.js        escreve números no formato brasileiro (vírgula, sinal de menos)
js/desenho.js         desenha a treliça em SVG (barras, apoios, cargas, reações)
js/passo-a-passo.js   transforma o resultado do cálculo no texto da aba "Cálculo passo a passo"
js/tela.js            liga tudo: lê as tabelas, chama o cálculo e mostra o resultado
```

Os arquivos são carregados nessa ordem no final do `index.html`. A regra principal é
**só o `calculo.js` faz conta de engenharia**. Os outros só leem, desenham ou escrevem texto.

## 2. Fluxo de um clique em "Calcular"

```
  tabelas da tela ──► objeto trelica ──► resolverTrelica(trelica) ──► resultado
                                              (calculo.js)               │
                         ┌────────────────────────────────────────────────┤
                         ▼                        ▼                       ▼
                desenharTrelica()         mostrarResultados()     gerarPassoAPasso()
                  (desenho.js)               (tela.js)            (passo-a-passo.js)
```

## 3. Como a treliça fica guardada na memória

Tudo o que o usuário digita vira **um único objeto** chamado `trelica`. É também o formato do
arquivo salvo pelo botão "Salvar". Para o Exemplo 1:

```js
{
  unidades: 'si_kn',
  tensaoAdmTracao: 50,
  tensaoAdmCompressao: 50,
  nos: [
    { nome: 'A', x: 0, y: 0, apoio: 'fixo',     fx: 0, fy: 0 },
    { nome: 'B', x: 4, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
    { nome: 'C', x: 2, y: 3, apoio: 'livre',    fx: 0, fy: -10 }
  ],
  barras: [
    { no1: 'A', no2: 'B', area: 100 },
    { no1: 'A', no2: 'C', area: 100 },
    { no1: 'B', no2: 'C', area: 100 }
  ]
}
```

- A carga fica **dentro do nó** (`fx`, `fy`).
- O apoio é uma palavra (`fixo`, `rolete_y`, `rolete_x`, `livre`).
- A barra só guarda os **nomes** dos dois nós. O nome da barra é a junção deles em ordem alfabética (de A para B ou de B para A, o nome é sempre `AB`, igual aos formulários de resposta).

## 4. `calculo.js` — função por função

A função principal é `resolverTrelica` (linha 227). Ela chama as outras nesta ordem:

```
resolverTrelica
 ├─ validarTrelica          os dados fazem sentido?
 ├─ listarIncognitas        quem são as incógnitas (N de cada barra + reações)
 ├─ classificarEstaticidade b + r comparado com 2n
 ├─ medirBarra              Δx, Δy, L, cos, sen de cada barra
 ├─ montarSistema           escreve as 2n equações em forma de matriz
 │    └─ coeficiente        o número que multiplica cada incógnita em cada equação
 ├─ resolverPorGauss        resolve [A]·{x} = {c}
 ├─ situacaoDaBarra         tração / compressão / força zero
 ├─ conferirEquilibrio      prova real
 └─ calcularTensoes         σ = N/A e área necessária
```

### 4.1 Tabelas de configuração (linhas 1–17)

```js
const TIPOS_DE_APOIO = {
  livre:    { descricao: 'Livre (sem apoio)',     reacoes: [] },
  fixo:     { descricao: 'Fixo / pino (Rx e Ry)', reacoes: ['x', 'y'] },
  rolete_y: { descricao: 'Rolete (só Ry)',        reacoes: ['y'] },
  rolete_x: { descricao: 'Rolete (só Rx)',        reacoes: ['x'] }
};
```

Cada tipo de apoio diz **quais reações ele cria**. Um pino cria duas (x e y) e um rolete cria
uma. O resto do código só olha essa lista, então não existe nenhum `if (apoio === 'fixo')`
espalhado pelo programa.

`SISTEMAS_DE_UNIDADES` guarda os nomes das unidades e o `fatorTensao`: 1000 para kN com mm²
(1 kN/mm² = 1000 MPa) e 1 para os outros sistemas.

`TOLERANCIA_PIVO` (10⁻⁹) é o limite abaixo do qual o pivô é considerado zero. `LIMITE_FORCA_ZERO`
(10⁻⁶) é o limite abaixo do qual uma força vira 0 (força zero).

### 4.2 `medirBarra` (linha 27)

Calcula `Δx = x_final − x_inicial`, `Δy`, `L = √(Δx² + Δy²)`, `cos = Δx/L` e `sen = Δy/L`.
Serve para mostrar a geometria no passo a passo e o comprimento na tabela.

### 4.3 `validarTrelica` (linha 43)

Antes de qualquer conta, procura erros de digitação: menos de 2 nós, nenhuma barra, nome
repetido, barra ligando o nó a ele mesmo, barra de comprimento zero, barra repetida e nó solto
(sem barra). Devolve uma lista de mensagens. Lista vazia quer dizer que está tudo certo.

### 4.4 `listarIncognitas` (linha 80)

Monta o vetor de incógnitas **x**:

1. primeiro, **uma incógnita por barra** (`NAB`, `NAC`, `NBC`);
2. depois, **uma por reação**, lendo `TIPOS_DE_APOIO` de cada nó (`Ax`, `Ay`, `By`).

Para o triângulo: `x = [NAB, NAC, NBC, Ax, Ay, By]`. A **posição** de cada incógnita nessa lista
será a **coluna** dela na matriz.

### 4.5 `classificarEstaticidade` (linha 99)

```js
const n = trelica.nos.length;
const b = trelica.barras.length;
const r = incognitas.length - b;
let tipo = 'isostática';
if (b + r < 2 * n) tipo = 'hipostática';
if (b + r > 2 * n) tipo = 'hiperestática';
```

É a fórmula b + r = 2n escrita em código.

### 4.6 `coeficiente` (linha 109) — o coração do método dos nós

Responde: **"na equação ΣF(direção) do nó X, qual número multiplica esta incógnita?"**

```js
function coeficiente(trelica, no, direcao, incognita) {
  if (incognita.tipo === 'reacao') {
    return incognita.no === no.nome && incognita.direcao === direcao ? 1 : 0;
  }
  const barra = incognita.barra;
  if (barra.no1 !== no.nome && barra.no2 !== no.nome) return 0;
  const outroNo = buscarNo(trelica, barra.no1 === no.nome ? barra.no2 : barra.no1);
  const dx = outroNo.x - no.x;
  const dy = outroNo.y - no.y;
  const comprimento = Math.sqrt(dx * dx + dy * dy);
  return direcao === 'x' ? dx / comprimento : dy / comprimento;
}
```

São três situações:

| Incógnita | Coeficiente |
|---|---|
| uma reação **deste** nó, **nesta** direção | 1 |
| uma reação de outro nó, ou na outra direção | 0 |
| uma barra que **não toca** este nó | 0 |
| uma barra que **toca** este nó | cos ou sen da direção **deste nó → outro nó** |

Por que "deste nó para o outro"? Porque supomos tração: a barra **puxa** o nó em direção ao outro
nó. Exemplo: no nó C do triângulo, a barra AC aponta de C (2; 3) para A (0; 0):
`(−2; −3) ÷ 3,6056 = (−0,5547; −0,8321)`. Esses são os coeficientes de NAC nas equações ΣFx e
ΣFy do nó C.

### 4.7 `montarSistema` (linha 122)

```js
trelica.nos.forEach(no => {
  ['x', 'y'].forEach(direcao => {
    const carga = direcao === 'x' ? no.fx : no.fy;
    equacoes.push({ no: no.nome, direcao: direcao, carga: carga });
    matriz.push(incognitas.map(incognita => coeficiente(trelica, no, direcao, incognita)));
    vetor.push(-carga);
  });
});
```

Para cada nó e para cada direção (x e y), cria **uma linha** da matriz: a lista de coeficientes de
todas as incógnitas. A equação real é `soma(coef × incógnita) + carga = 0`. Passando a carga para o
outro lado fica `soma(coef × incógnita) = −carga`, por isso o vetor recebe `-carga`.

Resultado: `matriz` com 2n linhas × (b + r) colunas e `vetor` com 2n valores.

### 4.8 `resolverPorGauss` (linha 137)

Resolve `[A]·{x} = {c}` em duas fases.

**Ida (escalonamento):**

```js
for (let coluna = 0; coluna < tamanho; coluna++) {
  // 1. procura a linha com o maior valor (em módulo) nesta coluna → pivô
  // 2. se o maior for ~0 → sistema sem solução única → treliça instável
  // 3. se o pivô não estiver na diagonal → troca as linhas
  // 4. para cada linha abaixo: linha = linha − fator × linhaDoPivo,
  //    com fator = a[linha][coluna] / a[coluna][coluna]  → zera a coluna
}
```

**Volta (substituição):** da última linha para a primeira,

```js
solucao[linha] = (c[linha] − Σ a[linha][k]·solucao[k]) / a[linha][linha]
```

Cada troca e cada eliminação ficam gravadas em `etapas`, que é o que a aba "Cálculo passo a passo"
lista no Passo 6. A função devolve também a matriz já escalonada.

### 4.9 `resolverTrelica` (linha 227) — o roteiro completo

1. Valida. Se houver erro, para e devolve as mensagens.
2. Lista incógnitas, classifica, mede as barras e monta o sistema.
3. Se for **hipostática** ou **hiperestática**, para com a mensagem (como o MDSolids).
4. Resolve por Gauss. Se faltar pivô, para com "geometricamente instável".
5. Separa a solução: as primeiras `b` posições são as forças das barras e o resto são as reações.
6. Classifica cada barra (`situacaoDaBarra`: N > 0 tração, N < 0 compressão, N = 0 força zero).
7. Faz a prova real (`conferirEquilibrio`): coloca os valores de volta em todas as equações e calcula
   ΣFx, ΣFy e ΣM da treliça inteira.
8. Calcula as tensões (`calcularTensoes`).

O objeto `resultado` devolvido tem **tudo** (dados, incógnitas, matriz, etapas do Gauss, forças,
reações, conferência e tensões). Por isso o passo a passo consegue mostrar cada etapa.

### 4.10 `calcularTensoes` (linha 303)

```js
const tensao = barra.forca * unidades.fatorTensao / barra.area;                  // σ = N/A
const admissivel = barra.forca >= 0 ? tensaoAdmTracao : tensaoAdmCompressao;
const areaNecessaria = Math.abs(barra.forca) * unidades.fatorTensao / admissivel; // A = |N|/σadm
```

Se a área ou o σadm não foram informados, aquela coluna fica vazia ("—").

## 5. Os outros arquivos (resumo)

**`tela.js`**
- Guarda a treliça na variável `trelica` e o último resultado em `resultadoAtual`.
- `mostrarTabelaDeNos` / `mostrarTabelaDeBarras` desenham as tabelas a partir do objeto.
- `alterarNo` / `alterarBarra` fazem o caminho contrário: quando o usuário digita, atualizam o objeto.
- Qualquer mudança chama `aoMudarDados`, que redesenha e apaga o resultado antigo (para não
  mostrar resultado de dados velhos).
- `calcular` chama `resolverTrelica` e depois os três "mostradores".
- `mostrarResultados` lista as barras em ordem alfabética (`ordemAlfabetica`), como nos formulários
  de resposta, sem mudar a ordem das incógnitas na matriz.
- Os nomes dos nós são letras automáticas (`proximoNomeLivre`), como no MDSolids.
- Salvar/Abrir: transforma o objeto em JSON e vice-versa. `normalizarTrelica` limpa o arquivo
  aberto (aceita só números, nomes com letras/dígitos e tipos de apoio conhecidos).

**`desenho.js`**
- `criarConversorDeCoordenadas` transforma metros em pixels: calcula a escala para a treliça
  caber no quadro e **inverte o eixo y** (na tela, y cresce para baixo).
- Barras coloridas pelo resultado (azul tração, vermelho compressão, cinza tracejado força zero),
  apoios, cargas (preto) e reações (verde, no sentido real da força).

**`passo-a-passo.js`**
- Uma função por passo (`passoDados`, `passoIncognitas`, …, `passoTensoes`). Cada uma lê o
  `resultado` e devolve um pedaço de HTML. Não faz conta nova: só mostra o que o `calculo.js` fez.
  As únicas contas extras servem para escrever a substituição do Gauss e os momentos da prova real.

**`exemplos.js`**: lista `EXEMPLOS` no mesmo formato do objeto `trelica`.

**`formatar.js`**: números com vírgula e casas decimais fixas, e `−0,000` vira `0,000`.

## 6. Perguntas sobre o código que podem aparecer

**Onde está o método dos nós?**
Em `coeficiente` + `montarSistema` (`calculo.js`, linhas 109–135): uma linha da matriz para cada
ΣFx e ΣFy de cada nó.

**Onde ele descobre que a treliça é instável?**
Em dois lugares: `classificarEstaticidade` (contagem b + r × 2n) e `resolverPorGauss`, quando não
encontra pivô diferente de zero numa coluna.

**Por que JavaScript?**
Roda em qualquer navegador sem instalar nada, e a interface e o cálculo ficam na mesma linguagem.

**Usaram biblioteca para resolver o sistema?**
Não. A eliminação de Gauss está escrita à mão em `resolverPorGauss`, com cerca de 40 linhas.

**Como sabem que está certo?**
1. O Passo 8 coloca a resposta de volta em todas as equações, a cada cálculo.
2. Os exemplos 1, 2 e 3 foram resolvidos à mão (ver `ROTEIRO_APRESENTACAO.md`).
3. Os 12 casos com gabarito da versão anterior do projeto dão o mesmo resultado.
