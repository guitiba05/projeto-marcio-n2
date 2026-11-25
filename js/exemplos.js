function criarBarras(pares, area) {
  return pares.map(par => ({ no1: par[0], no2: par[1], area: area }));
}

const EXEMPLOS = [
  {
    titulo: '1. Triângulo simples (apresentação)',
    unidades: 'si_kn',
    tensaoAdmTracao: 50,
    tensaoAdmCompressao: 50,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 4, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'C', x: 2, y: 3, apoio: 'livre', fx: 0, fy: -10 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'C'], ['B', 'C']], 100)
  },
  {
    titulo: '2. Quadro com diagonal: força zero (apresentação)',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 4, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'C', x: 4, y: 3, apoio: 'livre', fx: 0, fy: -12 },
      { nome: 'D', x: 0, y: 3, apoio: 'livre', fx: 8, fy: 0 }
    ],
    barras: criarBarras([['A', 'B'], ['B', 'C'], ['C', 'D'], ['A', 'D'], ['A', 'C']], 0)
  },
  {
    titulo: '3. Ponte Pratt com 3 painéis (apresentação)',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 3, y: 0, apoio: 'livre', fx: 0, fy: -30 },
      { nome: 'C', x: 6, y: 0, apoio: 'livre', fx: 0, fy: -15 },
      { nome: 'D', x: 9, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'E', x: 3, y: 4, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'F', x: 6, y: 4, apoio: 'livre', fx: 0, fy: 0 }
    ],
    barras: criarBarras([['A', 'B'], ['B', 'C'], ['C', 'D'], ['A', 'E'], ['E', 'F'], ['D', 'F'], ['B', 'E'], ['C', 'F'], ['B', 'F']], 0)
  },
  {
    titulo: 'Lista — Exercício 1',
    unidades: 'kn_mm',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 100, y: 200, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 400, y: 800, apoio: 'livre', fx: 22, fy: -15 },
      { nome: 'C', x: 1000, y: 200, apoio: 'rolete_y', fx: 0, fy: 0 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'C'], ['B', 'C']], 0)
  },
  {
    titulo: 'Lista — Exercício 2',
    unidades: 'kn_mm',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 200, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 1000, y: 200, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'C', x: 100, y: 800, apoio: 'livre', fx: 0, fy: 42 },
      { nome: 'D', x: 600, y: 800, apoio: 'livre', fx: 11, fy: 7.5 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'C'], ['B', 'C'], ['B', 'D'], ['C', 'D']], 0)
  },
  {
    titulo: 'Lista — Exercício 3',
    unidades: 'kn_mm',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 200, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'B', x: 300, y: 200, apoio: 'livre', fx: 0, fy: -15 },
      { nome: 'C', x: 1000, y: 200, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'D', x: 100, y: 800, apoio: 'livre', fx: 22, fy: 0 },
      { nome: 'E', x: 400, y: 800, apoio: 'livre', fx: 30, fy: 8.5 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'D'], ['B', 'C'], ['B', 'D'], ['B', 'E'], ['C', 'E'], ['D', 'E']], 0)
  },
  {
    titulo: 'Lista — Exercício 4',
    unidades: 'kn_mm',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 200, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 300, y: 200, apoio: 'livre', fx: 0, fy: -13 },
      { nome: 'C', x: 600, y: 200, apoio: 'livre', fx: 21.5, fy: 0 },
      { nome: 'D', x: 1000, y: 200, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'E', x: 100, y: 800, apoio: 'livre', fx: -14, fy: 0 },
      { nome: 'F', x: 400, y: 800, apoio: 'livre', fx: 0, fy: -8 },
      { nome: 'G', x: 600, y: 800, apoio: 'livre', fx: 12.25, fy: 6 }
    ],
    barras: criarBarras([
      ['A', 'B'], ['A', 'E'], ['B', 'C'], ['B', 'E'], ['B', 'F'], ['C', 'D'],
      ['C', 'F'], ['C', 'G'], ['D', 'G'], ['E', 'F'], ['F', 'G']
    ], 0)
  },
  {
    titulo: 'Lista — Exercício 5',
    unidades: 'kn_mm',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 300, y: 100, apoio: 'livre', fx: 0, fy: -44.5 },
      { nome: 'C', x: 500, y: 200, apoio: 'livre', fx: 0, fy: -32.5 },
      { nome: 'D', x: 1000, y: 300, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'E', x: 800, y: 500, apoio: 'livre', fx: 12, fy: -11.6 },
      { nome: 'F', x: 500, y: 800, apoio: 'livre', fx: 12.5, fy: 8.7 },
      { nome: 'G', x: 100, y: 900, apoio: 'livre', fx: 0, fy: -4 },
      { nome: 'H', x: 300, y: 900, apoio: 'livre', fx: 8.5, fy: 2.5 }
    ],
    barras: criarBarras([
      ['A', 'B'], ['A', 'G'], ['B', 'C'], ['B', 'F'], ['B', 'H'], ['B', 'G'], ['C', 'D'],
      ['C', 'E'], ['C', 'F'], ['D', 'E'], ['E', 'F'], ['F', 'H'], ['G', 'H']
    ], 0)
  },
  {
    titulo: 'Extra: Treliça Warren',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 2, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'C', x: 4, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'D', x: 6, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'E', x: 1, y: 2, apoio: 'livre', fx: 0, fy: -10 },
      { nome: 'F', x: 3, y: 2, apoio: 'livre', fx: 0, fy: -10 },
      { nome: 'G', x: 5, y: 2, apoio: 'livre', fx: 0, fy: -10 }
    ],
    barras: criarBarras([['A', 'B'], ['B', 'C'], ['C', 'D'], ['E', 'F'], ['F', 'G'], ['A', 'E'], ['E', 'B'], ['B', 'F'], ['F', 'C'], ['C', 'G'], ['G', 'D']], 0)
  },
  {
    titulo: 'Extra: Pratt com carga de vento',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 2, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'C', x: 4, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'D', x: 6, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'E', x: 0, y: 2, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'F', x: 2, y: 2, apoio: 'livre', fx: 0, fy: -10 },
      { nome: 'G', x: 4, y: 2, apoio: 'livre', fx: 0, fy: -10 },
      { nome: 'H', x: 6, y: 2, apoio: 'livre', fx: 8, fy: 0 }
    ],
    barras: criarBarras([['A', 'B'], ['B', 'C'], ['C', 'D'], ['E', 'F'], ['F', 'G'], ['G', 'H'], ['A', 'E'], ['B', 'F'], ['C', 'G'], ['D', 'H'], ['E', 'B'], ['F', 'C'], ['G', 'D']], 0)
  },
  {
    titulo: 'Extra: Telhado de duas águas',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 2, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'C', x: 4, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'D', x: 6, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'E', x: 8, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'F', x: 2, y: 2.5, apoio: 'livre', fx: 0, fy: -4 },
      { nome: 'G', x: 4, y: 3, apoio: 'livre', fx: 0, fy: -8 },
      { nome: 'H', x: 6, y: 2.5, apoio: 'livre', fx: 0, fy: -4 }
    ],
    barras: criarBarras([['A', 'B'], ['B', 'C'], ['C', 'D'], ['D', 'E'], ['A', 'F'], ['F', 'G'], ['G', 'H'], ['H', 'E'], ['B', 'F'], ['C', 'G'], ['D', 'H'], ['F', 'C'], ['H', 'C']], 0)
  },
  {
    titulo: 'Extra: Geometria irregular com cargas inclinadas',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 5, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'C', x: 1, y: 3, apoio: 'livre', fx: -4, fy: -10 },
      { nome: 'D', x: 4, y: 2, apoio: 'livre', fx: 3, fy: -6 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'C'], ['C', 'D'], ['D', 'B'], ['A', 'D']], 0)
  },
  {
    titulo: 'Extra: Ponte Pratt grande (14 nós)',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 2, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'C', x: 4, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'D', x: 6, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'E', x: 8, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'F', x: 10, y: 0, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'G', x: 12, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'H', x: 0, y: 3, apoio: 'livre', fx: 0, fy: 0 },
      { nome: 'I', x: 2, y: 3, apoio: 'livre', fx: 0, fy: -8 },
      { nome: 'J', x: 4, y: 3, apoio: 'livre', fx: 0, fy: -8 },
      { nome: 'K', x: 6, y: 3, apoio: 'livre', fx: 0, fy: -8 },
      { nome: 'L', x: 8, y: 3, apoio: 'livre', fx: 0, fy: -8 },
      { nome: 'M', x: 10, y: 3, apoio: 'livre', fx: 0, fy: -8 },
      { nome: 'N', x: 12, y: 3, apoio: 'livre', fx: 0, fy: 0 }
    ],
    barras: criarBarras([
      ['A', 'B'], ['B', 'C'], ['C', 'D'], ['D', 'E'], ['E', 'F'], ['F', 'G'],
      ['H', 'I'], ['I', 'J'], ['J', 'K'], ['K', 'L'], ['L', 'M'], ['M', 'N'],
      ['A', 'H'], ['B', 'I'], ['C', 'J'], ['D', 'K'], ['E', 'L'], ['F', 'M'], ['G', 'N'],
      ['H', 'B'], ['I', 'C'], ['J', 'D'], ['L', 'D'], ['M', 'E'], ['N', 'F']
    ], 0)
  },
  {
    titulo: 'Extra: Rolete em plano inclinado (30°)',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 4, y: 0, apoio: 'rolete_inclinado', anguloApoio: 30, fx: 0, fy: 0 },
      { nome: 'C', x: 2, y: 3, apoio: 'livre', fx: 0, fy: -10 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'C'], ['B', 'C']], 0)
  },
  {
    titulo: 'Erro 1: hipostática (falta apoio)',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'B', x: 4, y: 0, apoio: 'rolete_y', fx: 0, fy: 0 },
      { nome: 'C', x: 2, y: 3, apoio: 'livre', fx: 0, fy: -10 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'C'], ['B', 'C']], 0)
  },
  {
    titulo: 'Erro 2: hiperestática (sobra apoio)',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 4, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'C', x: 2, y: 3, apoio: 'livre', fx: 0, fy: -10 }
    ],
    barras: criarBarras([['A', 'B'], ['A', 'C'], ['B', 'C']], 0)
  },
  {
    titulo: 'Erro 3: instável (quadrado sem diagonal)',
    unidades: 'si_kn',
    tensaoAdmTracao: 0,
    tensaoAdmCompressao: 0,
    nos: [
      { nome: 'A', x: 0, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'B', x: 4, y: 0, apoio: 'fixo', fx: 0, fy: 0 },
      { nome: 'C', x: 4, y: 3, apoio: 'livre', fx: 5, fy: 0 },
      { nome: 'D', x: 0, y: 3, apoio: 'livre', fx: 0, fy: 0 }
    ],
    barras: criarBarras([['A', 'B'], ['B', 'C'], ['C', 'D'], ['A', 'D']], 0)
  }
];
