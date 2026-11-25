const TOLERANCIA_PIVO = 1e-9;
const LIMITE_FORCA_ZERO = 1e-6;

const TIPOS_DE_APOIO = {
  livre: { descricao: 'Livre (sem apoio)', reacoes: [] },
  fixo: { descricao: 'Fixo / pino (Rx e Ry)', reacoes: ['x', 'y'] },
  rolete_y: { descricao: 'Rolete (só Ry)', reacoes: ['y'] },
  rolete_x: { descricao: 'Rolete (só Rx)', reacoes: ['x'] },
  rolete_inclinado: { descricao: 'Rolete inclinado (Rn ⟂ superfície)', reacoes: ['n'] }
};

const SISTEMAS_DE_UNIDADES = {
  kn_mm: { descricao: 'kN, mm, mm², MPa', forca: 'kN', comprimento: 'mm', area: 'mm²', tensao: 'MPa', fatorTensao: 1000 },
  si_kn: { descricao: 'kN, m, mm², MPa', forca: 'kN', comprimento: 'm', area: 'mm²', tensao: 'MPa', fatorTensao: 1000 },
  si_n: { descricao: 'N, mm, mm², MPa', forca: 'N', comprimento: 'mm', area: 'mm²', tensao: 'MPa', fatorTensao: 1 },
  us_kip: { descricao: 'kip, ft, in², ksi', forca: 'kip', comprimento: 'ft', area: 'in²', tensao: 'ksi', fatorTensao: 1 },
  us_lb: { descricao: 'lb, in, in², psi', forca: 'lb', comprimento: 'in', area: 'in²', tensao: 'psi', fatorTensao: 1 }
};

function nomeDaBarra(barra) {
  return [barra.no1, barra.no2].sort().join('');
}

function buscarNo(trelica, nome) {
  return trelica.nos.find(no => no.nome === nome);
}

function direcaoDaReacao(no, direcao) {
  if (direcao === 'x') return { x: 1, y: 0 };
  if (direcao === 'y') return { x: 0, y: 1 };
  const radianos = (no.anguloApoio || 0) * Math.PI / 180;
  return { x: -Math.sin(radianos), y: Math.cos(radianos) };
}

function medirBarra(trelica, barra) {
  const inicio = buscarNo(trelica, barra.no1);
  const fim = buscarNo(trelica, barra.no2);
  const dx = fim.x - inicio.x;
  const dy = fim.y - inicio.y;
  const comprimento = Math.sqrt(dx * dx + dy * dy);
  return {
    nome: nomeDaBarra(barra),
    dx: dx,
    dy: dy,
    comprimento: comprimento,
    cos: dx / comprimento,
    sen: dy / comprimento,
    angulo: Math.atan2(Math.abs(dy), Math.abs(dx)) * 180 / Math.PI
  };
}

function validarTrelica(trelica) {
  const erros = [];
  const nomes = trelica.nos.map(no => no.nome);

  if (trelica.nos.length < 2) erros.push('Cadastre pelo menos 2 nós.');
  if (trelica.barras.length < 1) erros.push('Cadastre pelo menos 1 barra.');

  trelica.nos.forEach(no => {
    if (no.nome === '') erros.push('Existe um nó sem nome.');
    if (nomes.filter(nome => nome === no.nome).length > 1) erros.push('O nome ' + no.nome + ' está repetido.');
    if (!Number.isFinite(no.x) || !Number.isFinite(no.y)) erros.push('O nó ' + no.nome + ' tem coordenada inválida.');
    if (!Number.isFinite(no.fx) || !Number.isFinite(no.fy)) erros.push('O nó ' + no.nome + ' tem carga inválida.');
    if (no.apoio === 'rolete_inclinado' && !Number.isFinite(no.anguloApoio)) erros.push('O nó ' + no.nome + ' tem ângulo de apoio inválido.');
  });

  const barrasJaVistas = [];
  trelica.barras.forEach(barra => {
    const inicio = buscarNo(trelica, barra.no1);
    const fim = buscarNo(trelica, barra.no2);
    if (!inicio || !fim) {
      erros.push('A barra ' + nomeDaBarra(barra) + ' usa um nó que não existe.');
      return;
    }
    if (barra.no1 === barra.no2) erros.push('A barra ' + nomeDaBarra(barra) + ' liga o nó a ele mesmo.');
    else if (inicio.x === fim.x && inicio.y === fim.y) erros.push('A barra ' + nomeDaBarra(barra) + ' tem comprimento zero.');
    const chave = [barra.no1, barra.no2].sort().join('-');
    if (barrasJaVistas.includes(chave)) erros.push('A barra ' + nomeDaBarra(barra) + ' está repetida.');
    barrasJaVistas.push(chave);
  });

  trelica.nos.forEach(no => {
    const ligado = trelica.barras.some(barra => barra.no1 === no.nome || barra.no2 === no.nome);
    if (!ligado) erros.push('O nó ' + no.nome + ' não está ligado a nenhuma barra.');
  });

  return [...new Set(erros)];
}

function listarIncognitas(trelica) {
  const incognitas = trelica.barras.map(barra => ({
    tipo: 'barra',
    nome: 'N' + nomeDaBarra(barra),
    barra: barra
  }));
  trelica.nos.forEach(no => {
    TIPOS_DE_APOIO[no.apoio].reacoes.forEach(direcao => {
      incognitas.push({
        tipo: 'reacao',
        nome: no.nome + direcao,
        no: no.nome,
        direcao: direcao
      });
    });
  });
  return incognitas;
}

function classificarEstaticidade(trelica, incognitas) {
  const n = trelica.nos.length;
  const b = trelica.barras.length;
  const r = incognitas.length - b;
  let tipo = 'isostática';
  if (b + r < 2 * n) tipo = 'hipostática';
  if (b + r > 2 * n) tipo = 'hiperestática';
  return { n: n, b: b, r: r, equacoes: 2 * n, incognitas: b + r, tipo: tipo };
}

function coeficiente(trelica, no, direcao, incognita) {
  if (incognita.tipo === 'reacao') {
    if (incognita.no !== no.nome) return 0;
    const sentido = direcaoDaReacao(no, incognita.direcao);
    return direcao === 'x' ? sentido.x : sentido.y;
  }
  const barra = incognita.barra;
  if (barra.no1 !== no.nome && barra.no2 !== no.nome) return 0;
  const outroNo = buscarNo(trelica, barra.no1 === no.nome ? barra.no2 : barra.no1);
  const dx = outroNo.x - no.x;
  const dy = outroNo.y - no.y;
  const comprimento = Math.sqrt(dx * dx + dy * dy);
  return direcao === 'x' ? dx / comprimento : dy / comprimento;
}

function montarSistema(trelica, incognitas) {
  const equacoes = [];
  const matriz = [];
  const vetor = [];
  trelica.nos.forEach(no => {
    ['x', 'y'].forEach(direcao => {
      const carga = direcao === 'x' ? no.fx : no.fy;
      equacoes.push({ no: no.nome, direcao: direcao, carga: carga });
      matriz.push(incognitas.map(incognita => coeficiente(trelica, no, direcao, incognita)));
      vetor.push(-carga);
    });
  });
  return { equacoes: equacoes, matriz: matriz, vetor: vetor };
}

function resolverPorGauss(matrizOriginal, vetorOriginal) {
  const a = matrizOriginal.map(linha => linha.slice());
  const c = vetorOriginal.slice();
  const tamanho = c.length;
  const etapas = [];

  for (let coluna = 0; coluna < tamanho; coluna++) {
    let linhaDoPivo = coluna;
    for (let linha = coluna + 1; linha < tamanho; linha++) {
      if (Math.abs(a[linha][coluna]) > Math.abs(a[linhaDoPivo][coluna])) linhaDoPivo = linha;
    }

    if (Math.abs(a[linhaDoPivo][coluna]) < TOLERANCIA_PIVO) {
      return { sucesso: false, colunaSemPivo: coluna, etapas: etapas };
    }

    if (linhaDoPivo !== coluna) {
      [a[coluna], a[linhaDoPivo]] = [a[linhaDoPivo], a[coluna]];
      [c[coluna], c[linhaDoPivo]] = [c[linhaDoPivo], c[coluna]];
      etapas.push({ tipo: 'troca', linhaA: coluna, linhaB: linhaDoPivo });
    }

    for (let linha = coluna + 1; linha < tamanho; linha++) {
      const fator = a[linha][coluna] / a[coluna][coluna];
      if (fator === 0) continue;
      for (let k = coluna; k < tamanho; k++) {
        a[linha][k] = a[linha][k] - fator * a[coluna][k];
      }
      a[linha][coluna] = 0;
      c[linha] = c[linha] - fator * c[coluna];
      etapas.push({ tipo: 'eliminacao', linha: linha, linhaDoPivo: coluna, fator: fator });
    }
  }

  const solucao = new Array(tamanho).fill(0);
  for (let linha = tamanho - 1; linha >= 0; linha--) {
    let soma = c[linha];
    for (let k = linha + 1; k < tamanho; k++) {
      soma = soma - a[linha][k] * solucao[k];
    }
    solucao[linha] = soma / a[linha][linha];
  }

  return { sucesso: true, solucao: solucao, matrizTriangular: a, vetorTriangular: c, etapas: etapas };
}

function arredondarZero(valor) {
  return Math.abs(valor) < LIMITE_FORCA_ZERO ? 0 : valor;
}

function situacaoDaBarra(forca) {
  if (forca > 0) return 'Tração';
  if (forca < 0) return 'Compressão';
  return 'Força zero';
}

function conferirEquilibrio(trelica, sistema, valores, reacoes) {
  const residuos = sistema.matriz.map((linha, i) => {
    const soma = linha.reduce((total, coef, j) => total + coef * valores[j], 0);
    return soma - sistema.vetor[i];
  });

  let somaFx = 0;
  let somaFy = 0;
  let somaMomentos = 0;
  trelica.nos.forEach(no => {
    somaFx += no.fx;
    somaFy += no.fy;
    somaMomentos += no.x * no.fy - no.y * no.fx;
  });
  reacoes.forEach(reacao => {
    const no = buscarNo(trelica, reacao.no);
    somaFx += reacao.fx;
    somaFy += reacao.fy;
    somaMomentos += no.x * reacao.fy - no.y * reacao.fx;
  });

  return {
    residuos: residuos,
    maiorResiduo: Math.max(...residuos.map(Math.abs)),
    somaFx: arredondarZero(somaFx),
    somaFy: arredondarZero(somaFy),
    somaMomentos: arredondarZero(somaMomentos)
  };
}

function resolverTrelica(trelica) {
  const erros = validarTrelica(trelica);
  if (erros.length > 0) {
    return { sucesso: false, etapa: 'validacao', mensagem: 'Dados de entrada com problema.', erros: erros, trelica: trelica };
  }

  const incognitas = listarIncognitas(trelica);
  const estaticidade = classificarEstaticidade(trelica, incognitas);
  const geometria = trelica.barras.map(barra => medirBarra(trelica, barra));
  const sistema = montarSistema(trelica, incognitas);
  const resultado = { trelica: trelica, incognitas: incognitas, estaticidade: estaticidade, geometria: geometria, sistema: sistema };

  if (estaticidade.tipo === 'hipostática') {
    resultado.sucesso = false;
    resultado.etapa = 'estaticidade';
    resultado.mensagem = 'Treliça hipostática (instável): b + r = ' + estaticidade.incognitas +
      ' é menor que 2n = ' + estaticidade.equacoes + '. Faltam barras ou apoios.';
    return resultado;
  }

  if (estaticidade.tipo === 'hiperestática') {
    resultado.sucesso = false;
    resultado.etapa = 'estaticidade';
    resultado.mensagem = 'Treliça hiperestática: b + r = ' + estaticidade.incognitas +
      ' é maior que 2n = ' + estaticidade.equacoes +
      '. Há mais incógnitas que equações e o equilíbrio sozinho não resolve (o MDSolids também recusa este caso).';
    return resultado;
  }

  const gauss = resolverPorGauss(sistema.matriz, sistema.vetor);
  resultado.gauss = gauss;

  if (!gauss.sucesso) {
    resultado.sucesso = false;
    resultado.etapa = 'gauss';
    resultado.mensagem = 'Treliça geometricamente instável: a conta b + r = 2n fecha, mas o sistema não tem solução única. ' +
      'Verifique nós alinhados, quadros sem diagonal ou apoios que não impedem o giro.';
    return resultado;
  }

  const valores = gauss.solucao.map(arredondarZero);

  const barras = trelica.barras.map((barra, i) => ({
    nome: nomeDaBarra(barra),
    no1: barra.no1,
    no2: barra.no2,
    comprimento: geometria[i].comprimento,
    angulo: geometria[i].angulo,
    forca: valores[i],
    situacao: situacaoDaBarra(valores[i]),
    area: barra.area
  }));

  const reacoes = incognitas
    .map((incognita, i) => ({ incognita: incognita, valor: valores[i] }))
    .filter(item => item.incognita.tipo === 'reacao')
    .map(item => {
      const sentido = direcaoDaReacao(buscarNo(trelica, item.incognita.no), item.incognita.direcao);
      return {
        nome: item.incognita.nome,
        no: item.incognita.no,
        direcao: item.incognita.direcao,
        valor: item.valor,
        fx: arredondarZero(item.valor * sentido.x),
        fy: arredondarZero(item.valor * sentido.y)
      };
    });

  resultado.sucesso = true;
  resultado.valores = valores;
  resultado.barras = barras;
  resultado.reacoes = reacoes;
  resultado.conferencia = conferirEquilibrio(trelica, sistema, valores, reacoes);
  resultado.tensoes = calcularTensoes(
    barras,
    SISTEMAS_DE_UNIDADES[trelica.unidades] || SISTEMAS_DE_UNIDADES.si_kn,
    trelica.tensaoAdmTracao,
    trelica.tensaoAdmCompressao
  );
  return resultado;
}

function calcularTensoes(barras, unidades, tensaoAdmTracao, tensaoAdmCompressao) {
  return barras.map(barra => {
    const temArea = barra.area > 0;
    const tensao = temArea ? barra.forca * unidades.fatorTensao / barra.area : null;
    const admissivel = barra.forca >= 0 ? tensaoAdmTracao : tensaoAdmCompressao;
    const temAdmissivel = admissivel > 0;
    const areaNecessaria = temAdmissivel ? Math.abs(barra.forca) * unidades.fatorTensao / admissivel : null;
    let verificacao = '';
    if (temArea && temAdmissivel) verificacao = Math.abs(tensao) <= admissivel ? 'OK' : 'Excede';
    return {
      nome: barra.nome,
      forca: barra.forca,
      area: temArea ? barra.area : null,
      tensao: tensao,
      admissivel: temAdmissivel ? admissivel : null,
      areaNecessaria: areaNecessaria,
      verificacao: verificacao
    };
  });
}

function decomporCarga(modulo, anguloGraus) {
  const radianos = anguloGraus * Math.PI / 180;
  const limpar = valor => Math.round(valor * 1e6) / 1e6 || 0;
  return {
    fx: limpar(modulo * Math.cos(radianos)),
    fy: limpar(modulo * Math.sin(radianos))
  };
}
