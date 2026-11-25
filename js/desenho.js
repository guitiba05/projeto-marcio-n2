// Desenho da treliça em SVG: barras, apoios, cargas, reações, rótulos e grade opcional.
const LARGURA_DESENHO = 760;
const ALTURA_DESENHO = 560;
// Folga para os textos de reação e de carga não encostarem na borda do SVG.
const MARGEM_DESENHO = 110;

const CORES = {
  'Tração': '#2563eb',
  'Compressão': '#dc2626',
  'Força zero': '#a1a1aa',
  semResultado: '#475569',
  carga: '#111827',
  reacao: '#059669'
};

// Distância, na unidade da treliça, entre duas linhas da grade.
const PASSO_DA_GRADE = { mm: 100, m: 1, ft: 1, in: 10 };

// Opções do desenho (todas ligadas/desligadas na tela; o padrão é o desenho simples).
const OPCOES_DESENHO_PADRAO = {
  rotulos: 'nome-valor', // 'nome-valor' | 'valor' | 'nome' | 'ocultar'
  grade: false,
  espessura: false
};

function criarConversorDeCoordenadas(nos) {
  const xs = nos.map(no => no.x);
  const ys = nos.map(no => no.y);
  const menorX = Math.min(...xs);
  const menorY = Math.min(...ys);
  const largura = Math.max(...xs) - menorX || 1;
  const altura = Math.max(...ys) - menorY || 1;
  const escala = Math.min(
    (LARGURA_DESENHO - 2 * MARGEM_DESENHO) / largura,
    (ALTURA_DESENHO - 2 * MARGEM_DESENHO) / altura
  );
  const sobraX = (LARGURA_DESENHO - largura * escala) / 2;
  const sobraY = (ALTURA_DESENHO - altura * escala) / 2;
  return no => ({
    x: sobraX + (no.x - menorX) * escala,
    y: ALTURA_DESENHO - sobraY - (no.y - menorY) * escala
  });
}

function desenharPontasDeSeta() {
  return `<defs>
    <marker id="ponta-carga" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="${CORES.carga}"></path>
    </marker>
    <marker id="ponta-reacao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="${CORES.reacao}"></path>
    </marker>
  </defs>`;
}

function desenharSeta(inicio, fim, cor, idDaPonta, texto) {
  const vertical = Math.abs(inicio.x - fim.x) < 1e-6;
  const meioX = (inicio.x + fim.x) / 2;
  const meioY = (inicio.y + fim.y) / 2;
  return `<line x1="${inicio.x}" y1="${inicio.y}" x2="${fim.x}" y2="${fim.y}" stroke="${cor}" stroke-width="2.5" marker-end="url(#${idDaPonta})"></line>
    <text x="${vertical ? meioX + 10 : meioX}" y="${vertical ? meioY + 4 : meioY + 18}"
      text-anchor="${vertical ? 'start' : 'middle'}" class="texto-seta" fill="${cor}">${texto}</text>`;
}

function desenharGrade(trelica, posicao, unidades) {
  const passo = PASSO_DA_GRADE[unidades.comprimento] || 100;
  const xs = trelica.nos.map(no => no.x);
  const ys = trelica.nos.map(no => no.y);
  const menorX = Math.floor(Math.min(...xs) / passo) * passo;
  const maiorX = Math.ceil(Math.max(...xs) / passo) * passo;
  const menorY = Math.floor(Math.min(...ys) / passo) * passo;
  const maiorY = Math.ceil(Math.max(...ys) / passo) * passo;
  const partes = [];

  for (let i = 0; i <= Math.round((maiorX - menorX) / passo); i++) {
    const valor = menorX + i * passo;
    const de = posicao({ x: valor, y: maiorY });
    const ate = posicao({ x: valor, y: menorY });
    partes.push(`<line x1="${de.x}" y1="${de.y}" x2="${ate.x}" y2="${ate.y}" class="linha-grade"></line>`);
    partes.push(`<text x="${de.x}" y="${ALTURA_DESENHO - 6}" text-anchor="middle" class="texto-grade">${formatarNumero(valor, 0)}</text>`);
  }

  for (let i = 0; i <= Math.round((maiorY - menorY) / passo); i++) {
    const valor = menorY + i * passo;
    const de = posicao({ x: menorX, y: valor });
    const ate = posicao({ x: maiorX, y: valor });
    partes.push(`<line x1="${de.x}" y1="${de.y}" x2="${ate.x}" y2="${ate.y}" class="linha-grade"></line>`);
    partes.push(`<text x="6" y="${de.y + 4}" text-anchor="start" class="texto-grade">${formatarNumero(valor, 0)}</text>`);
  }

  return partes.join('');
}

function desenharApoio(ponto, apoio) {
  const { x, y } = ponto;
  if (apoio === 'fixo') {
    return `<polygon points="${x},${y + 6} ${x - 13},${y + 26} ${x + 13},${y + 26}" class="apoio"></polygon>
      <line x1="${x - 20}" y1="${y + 28}" x2="${x + 20}" y2="${y + 28}" class="chao"></line>`;
  }
  if (apoio === 'rolete_y') {
    return `<polygon points="${x},${y + 6} ${x - 13},${y + 24} ${x + 13},${y + 24}" class="apoio"></polygon>
      <circle cx="${x - 7}" cy="${y + 29}" r="4" class="apoio"></circle>
      <circle cx="${x + 7}" cy="${y + 29}" r="4" class="apoio"></circle>
      <line x1="${x - 20}" y1="${y + 34}" x2="${x + 20}" y2="${y + 34}" class="chao"></line>`;
  }
  if (apoio === 'rolete_x') {
    return `<polygon points="${x - 6},${y} ${x - 24},${y - 13} ${x - 24},${y + 13}" class="apoio"></polygon>
      <circle cx="${x - 29}" cy="${y - 7}" r="4" class="apoio"></circle>
      <circle cx="${x - 29}" cy="${y + 7}" r="4" class="apoio"></circle>
      <line x1="${x - 34}" y1="${y - 20}" x2="${x - 34}" y2="${y + 20}" class="chao"></line>`;
  }
  return '';
}

// Ângulo (em graus, 0 a 180) entre uma direção e a direção mais próxima de uma barra.
// Quanto maior, mais livre está aquele lado do nó para desenhar a seta de carga.
function folgaAngular(direcao, direcoes) {
  if (!direcoes || direcoes.length === 0) return 180;
  let menor = 180;
  direcoes.forEach(barra => {
    const produto = direcao.x * barra.x + direcao.y * barra.y;
    const angulo = Math.acos(Math.max(-1, Math.min(1, produto))) * 180 / Math.PI;
    if (angulo < menor) menor = angulo;
  });
  return menor;
}

function direcoesDasBarras(trelica, no, posicao) {
  const origem = posicao(no);
  return trelica.barras
    .filter(barra => barra.no1 === no.nome || barra.no2 === no.nome)
    .map(barra => {
      const outro = buscarNo(trelica, barra.no1 === no.nome ? barra.no2 : barra.no1);
      const alvo = posicao(outro);
      const dx = alvo.x - origem.x;
      const dy = alvo.y - origem.y;
      const comprimento = Math.hypot(dx, dy) || 1;
      return { x: dx / comprimento, y: dy / comprimento };
    });
}

// Desenha uma componente de carga (fx ou fy).
// A seta ocupa um dos dois lados do nó ao longo da linha de ação da força:
// atrás do nó (ponta chegando no nó, como antes) ou à frente (saindo do nó).
// Se o lado de trás colidir com uma barra (ângulo < 25°), usa o lado da frente.
function desenharComponenteDeCarga(ponto, valor, eixo, unidades, direcoes) {
  const sentido = Math.sign(valor);
  // No desenho o eixo y cresce para baixo.
  const vetor = eixo === 'x' ? { x: sentido, y: 0 } : { x: 0, y: -sentido };
  const tras = folgaAngular({ x: -vetor.x, y: -vetor.y }, direcoes);
  const frente = folgaAngular(vetor, direcoes);
  const usarFrente = tras < 25 && frente > tras;

  const inicio = usarFrente
    ? { x: ponto.x + vetor.x * 9, y: ponto.y + vetor.y * 9 }
    : { x: ponto.x - vetor.x * 60, y: ponto.y - vetor.y * 60 };
  const fim = usarFrente
    ? { x: ponto.x + vetor.x * 60, y: ponto.y + vetor.y * 60 }
    : { x: ponto.x - vetor.x * 9, y: ponto.y - vetor.y * 9 };

  const texto = formatarNumero(Math.abs(valor), 2) + ' ' + unidades.forca;
  return desenharSeta(inicio, fim, CORES.carga, 'ponta-carga', texto);
}

function desenharCargas(ponto, no, unidades, direcoes) {
  const partes = [];
  if (no.fx !== 0) partes.push(desenharComponenteDeCarga(ponto, no.fx, 'x', unidades, direcoes));
  if (no.fy !== 0) partes.push(desenharComponenteDeCarga(ponto, no.fy, 'y', unidades, direcoes));
  return partes.join('');
}

function desenharReacao(ponto, reacao, unidades) {
  if (reacao.valor === 0) return '';
  const sentido = Math.sign(reacao.valor);
  const texto = reacao.nome + ' = ' + formatarNumero(Math.abs(reacao.valor), 2) + ' ' + unidades.forca;
  if (reacao.direcao === 'y') {
    const perto = ponto.y + 40;
    const longe = ponto.y + 85;
    const inicio = { x: ponto.x, y: sentido > 0 ? longe : perto };
    const fim = { x: ponto.x, y: sentido > 0 ? perto : longe };
    return desenharSeta(inicio, fim, CORES.reacao, 'ponta-reacao', texto);
  }
  const perto = ponto.x - 40;
  const longe = ponto.x - 85;
  const inicio = { x: sentido > 0 ? longe : perto, y: ponto.y + 18 };
  const fim = { x: sentido > 0 ? perto : longe, y: ponto.y + 18 };
  return desenharSeta(inicio, fim, CORES.reacao, 'ponta-reacao', texto);
}

function textoDoRotulo(nome, barraCalculada, modo) {
  if (modo === 'ocultar') return '';
  if (!barraCalculada) return modo === 'valor' ? '' : nome;
  if (modo === 'nome') return nome;
  if (modo === 'valor') return formatarComSinal(barraCalculada.forca);
  return nome + ': ' + formatarComSinal(barraCalculada.forca);
}

// Caixa aproximada que o texto ocuparia, já considerando a rotação da barra.
function caixaDoRotulo(centro, texto, anguloGraus) {
  const largura = texto.length * 7;
  const altura = 15;
  const radianos = anguloGraus * Math.PI / 180;
  const larguraNaTela = Math.abs(Math.cos(radianos)) * largura + Math.abs(Math.sin(radianos)) * altura;
  const alturaNaTela = Math.abs(Math.sin(radianos)) * largura + Math.abs(Math.cos(radianos)) * altura;
  return {
    x1: centro.x - larguraNaTela / 2, x2: centro.x + larguraNaTela / 2,
    y1: centro.y - alturaNaTela / 2, y2: centro.y + alturaNaTela / 2
  };
}

function caixasSeCruzam(a, b) {
  return a.x1 < b.x2 && b.x1 < a.x2 && a.y1 < b.y2 && b.y1 < a.y2;
}

// Escolhe o primeiro ponto da barra (t = 0,5 depois 0,36 / 0,64 / 0,28 / 0,72)
// cujo rótulo não encoste nos rótulos já desenhados.
function posicionarRotulo(inicio, fim, texto, ocupados) {
  const dx = fim.x - inicio.x;
  const dy = fim.y - inicio.y;
  const comprimento = Math.hypot(dx, dy) || 1;
  const ux = dx / comprimento;
  const uy = dy / comprimento;

  // Perpendicular voltada para cima (ou para a esquerda, quando a barra é horizontal).
  let px = uy;
  let py = -ux;
  if (py > 0 || (Math.abs(py) < 1e-6 && px > 0)) { px = -px; py = -py; }

  let angulo = Math.atan2(dy, dx) * 180 / Math.PI;
  if (angulo > 90) angulo -= 180;
  if (angulo < -90) angulo += 180;

  const tentativas = [0.5, 0.36, 0.64, 0.28, 0.72];
  let escolhido = null;

  tentativas.forEach(t => {
    const centro = {
      x: inicio.x + ux * comprimento * t + px * 11,
      y: inicio.y + uy * comprimento * t + py * 11
    };
    const caixa = caixaDoRotulo(centro, texto, angulo);
    if (escolhido) return;
    if (!ocupados.some(outra => caixasSeCruzam(caixa, outra))) escolhido = { centro: centro, caixa: caixa };
  });

  if (!escolhido) {
    const centro = { x: inicio.x + ux * comprimento * 0.5 + px * 11, y: inicio.y + uy * comprimento * 0.5 + py * 11 };
    escolhido = { centro: centro, caixa: caixaDoRotulo(centro, texto, angulo) };
  }

  ocupados.push(escolhido.caixa);
  return { centro: escolhido.centro, angulo: angulo };
}

function desenharBarra(inicio, fim, nome, barraCalculada, ajustes, dica, ocupados, forcaMaxima) {
  const cor = barraCalculada ? CORES[barraCalculada.situacao] : CORES.semResultado;
  const tracejado = barraCalculada && barraCalculada.situacao === 'Força zero' ? 'stroke-dasharray="8 6"' : '';
  const espessura = ajustes.espessura && barraCalculada && forcaMaxima > 0
    ? 3 + 6 * Math.abs(barraCalculada.forca) / forcaMaxima
    : 5;

  const texto = textoDoRotulo(nome, barraCalculada, ajustes.rotulos);
  let rotulo = '';
  if (texto) {
    const lugar = posicionarRotulo(inicio, fim, texto, ocupados);
    rotulo = `<text x="${lugar.centro.x}" y="${lugar.centro.y + 4}" text-anchor="middle"
      transform="rotate(${lugar.angulo.toFixed(2)} ${lugar.centro.x} ${lugar.centro.y + 4})"
      class="texto-barra" fill="${cor}">${texto}</text>`;
  }

  return `<g class="grupo-barra" data-barra="${nome}">
    <title>${dica}</title>
    <line x1="${inicio.x}" y1="${inicio.y}" x2="${fim.x}" y2="${fim.y}" stroke="${cor}" stroke-width="${espessura}" stroke-linecap="round" ${tracejado}></line>
    ${rotulo}
  </g>`;
}

function desenharTrelica(svg, trelica, resultado, opcoes) {
  const ajustes = Object.assign({}, OPCOES_DESENHO_PADRAO, opcoes || {});
  svg.setAttribute('viewBox', `0 0 ${LARGURA_DESENHO} ${ALTURA_DESENHO}`);
  if (trelica.nos.length === 0) {
    svg.innerHTML = `<text x="${LARGURA_DESENHO / 2}" y="${ALTURA_DESENHO / 2}" text-anchor="middle" class="texto-vazio">Adicione nós e barras para ver o desenho</text>`;
    return;
  }

  const unidades = SISTEMAS_DE_UNIDADES[trelica.unidades];
  const posicao = criarConversorDeCoordenadas(trelica.nos);
  const calculado = resultado && resultado.sucesso;
  const ocupados = [];
  const forcaMaxima = calculado ? Math.max(...resultado.barras.map(barra => Math.abs(barra.forca)), 0) : 0;
  const partes = [desenharPontasDeSeta()];

  if (ajustes.grade) partes.push(desenharGrade(trelica, posicao, unidades));

  trelica.barras.forEach((barra, i) => {
    const inicio = buscarNo(trelica, barra.no1);
    const fim = buscarNo(trelica, barra.no2);
    if (!inicio || !fim) return;
    const calculada = calculado ? resultado.barras[i] : null;
    const dica = calculada
      ? 'Barra ' + nomeDaBarra(barra) + ' · L ' + formatarNumero(calculada.comprimento) + ' ' + unidades.comprimento +
        ' · θ ' + formatarNumero(calculada.anguloGraus) + '° · N ' + formatarComSinal(calculada.forca) + ' ' +
        unidades.forca + ' (' + calculada.situacao + ')'
      : 'Barra ' + nomeDaBarra(barra);
    partes.push(desenharBarra(posicao(inicio), posicao(fim), nomeDaBarra(barra), calculada, ajustes, dica, ocupados, forcaMaxima));
  });

  const direcoes = {};
  trelica.nos.forEach(no => { direcoes[no.nome] = direcoesDasBarras(trelica, no, posicao); });

  trelica.nos.forEach(no => partes.push(desenharApoio(posicao(no), no.apoio)));
  trelica.nos.forEach(no => partes.push(desenharCargas(posicao(no), no, unidades, direcoes[no.nome])));

  if (calculado) {
    resultado.reacoes.forEach(reacao => partes.push(desenharReacao(posicao(buscarNo(trelica, reacao.no)), reacao, unidades)));
  }

  trelica.nos.forEach(no => {
    const ponto = posicao(no);
    partes.push(`<g class="grupo-no" data-no="${no.nome}">
      <circle cx="${ponto.x}" cy="${ponto.y}" r="6" class="no"></circle>
      <text x="${ponto.x - 10}" y="${ponto.y - 10}" text-anchor="end" class="texto-no">${no.nome}</text>
    </g>`);
  });

  svg.innerHTML = partes.join('');
}