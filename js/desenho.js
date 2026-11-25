const LARGURA_DESENHO = 720;
const ALTURA_DESENHO = 460;
const MARGEM_DESENHO = 95;

const CORES = {
  'Tração': '#2563eb',
  'Compressão': '#dc2626',
  'Força zero': '#a1a1aa',
  semResultado: '#475569',
  carga: '#111827',
  reacao: '#059669'
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
  const vertical = inicio.x === fim.x;
  const meioX = (inicio.x + fim.x) / 2;
  const meioY = (inicio.y + fim.y) / 2;
  return `<line x1="${inicio.x}" y1="${inicio.y}" x2="${fim.x}" y2="${fim.y}" stroke="${cor}" stroke-width="2.5" marker-end="url(#${idDaPonta})"></line>
    <text x="${vertical ? meioX + 9 : meioX}" y="${vertical ? meioY + 4 : meioY + 18}"
      text-anchor="${vertical ? 'start' : 'middle'}" class="texto-seta" fill="${cor}">${texto}</text>`;
}

function desenharApoio(ponto, apoio, anguloApoio) {
  const { x, y } = ponto;
  if (apoio === 'rolete_inclinado') {
    return `<g transform="rotate(${-(anguloApoio || 0)} ${x} ${y})">${desenharApoio(ponto, 'rolete_y')}</g>`;
  }
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

function desenharCargas(ponto, no, unidades) {
  const partes = [];
  if (no.fx !== 0) {
    const sentido = Math.sign(no.fx);
    const inicio = { x: ponto.x - sentido * 60, y: ponto.y };
    const fim = { x: ponto.x - sentido * 9, y: ponto.y };
    partes.push(desenharSeta(inicio, fim, CORES.carga, 'ponta-carga', formatarNumero(Math.abs(no.fx), 2) + ' ' + unidades.forca));
  }
  if (no.fy !== 0) {
    const sentido = Math.sign(no.fy);
    const inicio = { x: ponto.x, y: ponto.y + sentido * 60 };
    const fim = { x: ponto.x, y: ponto.y + sentido * 9 };
    partes.push(desenharSeta(inicio, fim, CORES.carga, 'ponta-carga', formatarNumero(Math.abs(no.fy), 2) + ' ' + unidades.forca));
  }
  return partes.join('');
}

function desenharReacao(ponto, reacao, unidades) {
  if (reacao.valor === 0) return '';
  const sentido = Math.sign(reacao.valor);
  const texto = reacao.nome + ' = ' + formatarNumero(Math.abs(reacao.valor), 2) + ' ' + unidades.forca;
  if (reacao.direcao === 'n') {
    const modulo = Math.hypot(reacao.fx, reacao.fy) || 1;
    const telaX = reacao.fx / modulo;
    const telaY = -reacao.fy / modulo;
    const inicio = { x: ponto.x - telaX * 85, y: ponto.y - telaY * 85 };
    const fim = { x: ponto.x - telaX * 40, y: ponto.y - telaY * 40 };
    return desenharSeta(inicio, fim, CORES.reacao, 'ponta-reacao', texto);
  }
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

function desenharBarra(inicio, fim, nome, barraCalculada, mostrarNome) {
  const cor = barraCalculada ? CORES[barraCalculada.situacao] : CORES.semResultado;
  const tracejado = barraCalculada && barraCalculada.situacao === 'Força zero' ? 'stroke-dasharray="8 6"' : '';
  const comprimento = Math.hypot(fim.x - inicio.x, fim.y - inicio.y) || 1;
  let ladoX = (fim.y - inicio.y) / comprimento;
  let ladoY = -(fim.x - inicio.x) / comprimento;
  if (ladoY > 0 || (ladoY === 0 && ladoX > 0)) {
    ladoX = -ladoX;
    ladoY = -ladoY;
  }
  const textoX = (inicio.x + fim.x) / 2 + ladoX * 10;
  const textoY = (inicio.y + fim.y) / 2 + ladoY * 10 + 4;
  const ancora = ladoX < -0.3 ? 'end' : ladoX > 0.3 ? 'start' : 'middle';
  let rotulo = nome;
  if (barraCalculada) rotulo = (mostrarNome ? nome + ': ' : '') + formatarComSinal(barraCalculada.forca, 2);
  return `<line x1="${inicio.x}" y1="${inicio.y}" x2="${fim.x}" y2="${fim.y}" stroke="${cor}" stroke-width="5" stroke-linecap="round" ${tracejado}></line>
    <text x="${textoX}" y="${textoY}" text-anchor="${ancora}" class="texto-barra" fill="${cor}">${rotulo}</text>`;
}

function desenharTrelica(svg, trelica, resultado) {
  svg.setAttribute('viewBox', `0 0 ${LARGURA_DESENHO} ${ALTURA_DESENHO}`);
  if (trelica.nos.length === 0) {
    svg.innerHTML = `<text x="${LARGURA_DESENHO / 2}" y="${ALTURA_DESENHO / 2}" text-anchor="middle" class="texto-vazio">Adicione nós e barras para ver o desenho</text>`;
    return;
  }

  const unidades = SISTEMAS_DE_UNIDADES[trelica.unidades];
  const posicao = criarConversorDeCoordenadas(trelica.nos);
  const calculado = resultado && resultado.sucesso;
  const partes = [desenharPontasDeSeta()];

  trelica.barras.forEach((barra, i) => {
    const inicio = buscarNo(trelica, barra.no1);
    const fim = buscarNo(trelica, barra.no2);
    if (!inicio || !fim) return;
    const barraCalculada = calculado ? resultado.barras[i] : null;
    partes.push(desenharBarra(posicao(inicio), posicao(fim), nomeDaBarra(barra), barraCalculada, trelica.barras.length <= 12));
  });

  trelica.nos.forEach(no => partes.push(desenharApoio(posicao(no), no.apoio, no.anguloApoio)));
  trelica.nos.forEach(no => partes.push(desenharCargas(posicao(no), no, unidades)));

  if (calculado) {
    resultado.reacoes.forEach(reacao => partes.push(desenharReacao(posicao(buscarNo(trelica, reacao.no)), reacao, unidades)));
  }

  trelica.nos.forEach(no => {
    const ponto = posicao(no);
    partes.push(`<circle cx="${ponto.x}" cy="${ponto.y}" r="6" class="no"></circle>
      <text x="${ponto.x - 10}" y="${ponto.y - 10}" text-anchor="end" class="texto-no">${no.nome}</text>`);
  });

  svg.innerHTML = partes.join('');
}
