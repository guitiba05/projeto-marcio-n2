function escreverTermos(termos) {
  const termosUteis = termos.filter(termo => termo.valor !== 0);
  if (termosUteis.length === 0) return '0';
  return termosUteis.map((termo, i) => {
    const absoluto = Math.abs(termo.valor);
    let texto = formatarNumero(absoluto, termo.casas);
    if (termo.nome) texto = absoluto === 1 ? termo.nome : texto + '·' + termo.nome;
    if (i === 0) return (termo.valor < 0 ? '−' : '') + texto;
    return (termo.valor < 0 ? ' − ' : ' + ') + texto;
  }).join('');
}

function rotuloDaEquacao(equacao) {
  return equacao.no + ': ΣF' + equacao.direcao;
}

function tabelaDeMatriz(cabecalhos, rotulos, matriz, vetor) {
  const cabecalho = cabecalhos.map(nome => `<th>${nome}</th>`).join('');
  const linhas = matriz.map((linha, i) => {
    const celulas = linha.map(valor => {
      const zero = Math.abs(valor) < 1e-12;
      return `<td class="${zero ? 'zero' : ''}">${zero ? '0' : formatarNumero(valor, 4)}</td>`;
    }).join('');
    return `<tr><th>${rotulos[i]}</th>${celulas}<td class="vetor">${formatarNumero(vetor[i], 3)}</td></tr>`;
  }).join('');
  return `<div class="rolagem"><table class="matriz"><thead><tr><th></th>${cabecalho}<th class="vetor">c</th></tr></thead><tbody>${linhas}</tbody></table></div>`;
}

function passoDados(resultado, unidades) {
  const { trelica } = resultado;
  const linhasNos = trelica.nos.map(no => {
    const reacoes = TIPOS_DE_APOIO[no.apoio].reacoes.map(direcao => no.nome + direcao).join(', ') || '—';
    return `<tr><td>${no.nome}</td><td>${formatarNumero(no.x, 2)}</td><td>${formatarNumero(no.y, 2)}</td>
      <td>${TIPOS_DE_APOIO[no.apoio].descricao}</td><td>${reacoes}</td>
      <td>${formatarNumero(no.fx, 2)}</td><td>${formatarNumero(no.fy, 2)}</td></tr>`;
  }).join('');
  const linhasBarras = trelica.barras.map(barra =>
    `<tr><td>${nomeDaBarra(barra)}</td><td>${barra.no1}</td><td>${barra.no2}</td></tr>`).join('');
  return `<section class="passo">
    <h3>Passo 1 — O que o programa leu</h3>
    <p>Cada nó tem coordenadas (x, y), um tipo de apoio e uma carga (Fx, Fy).
      O tipo de apoio diz quantas <strong>reações</strong> existem naquele nó. Cada barra só liga dois nós.</p>
    <div class="rolagem"><table class="dados">
      <thead><tr><th>Nó</th><th>x (${unidades.comprimento})</th><th>y (${unidades.comprimento})</th><th>Apoio</th><th>Reações criadas</th>
      <th>Fx (${unidades.forca})</th><th>Fy (${unidades.forca})</th></tr></thead>
      <tbody>${linhasNos}</tbody></table></div>
    <div class="rolagem"><table class="dados">
      <thead><tr><th>Barra</th><th>Nó inicial</th><th>Nó final</th></tr></thead>
      <tbody>${linhasBarras}</tbody></table></div>
  </section>`;
}

function passoIncognitas(resultado) {
  const { estaticidade: e, incognitas } = resultado;
  const nomes = incognitas.map(incognita => incognita.nome).join(', ');
  const comparacao = e.incognitas === e.equacoes ? '=' : (e.incognitas < e.equacoes ? '<' : '>');
  const explicacao = {
    'isostática': 'Número de incógnitas igual ao de equações: o sistema é quadrado e pode ter solução única.',
    'hipostática': 'Menos incógnitas que equações: faltam barras ou apoios, a treliça se move (mecanismo).',
    'hiperestática': 'Mais incógnitas que equações: só o equilíbrio não basta para achar todas as forças.'
  };
  return `<section class="passo">
    <h3>Passo 2 — Incógnitas, equações e estaticidade</h3>
    <p>Cada barra tem 1 força desconhecida (N) e cada reação de apoio é 1 incógnita.
      Cada nó fornece 2 equações de equilíbrio: ΣFx = 0 e ΣFy = 0.</p>
    <ul>
      <li>n = ${e.n} nós → 2n = <strong>${e.equacoes} equações</strong></li>
      <li>b = ${e.b} barras e r = ${e.r} reações → b + r = <strong>${e.incognitas} incógnitas</strong></li>
      <li>Vetor de incógnitas: <code>x = [ ${nomes} ]</code></li>
    </ul>
    <p class="destaque">b + r = ${e.incognitas} ${comparacao} 2n = ${e.equacoes} → treliça <strong>${e.tipo}</strong>.
      ${explicacao[e.tipo]}</p>
  </section>`;
}

function passoGeometria(resultado, unidades) {
  const linhas = resultado.geometria.map(g => `<tr><td>${g.nome}</td><td>${formatarNumero(g.dx, 3)}</td><td>${formatarNumero(g.dy, 3)}</td>
    <td>${formatarNumero(g.comprimento, 4)}</td><td>${formatarNumero(g.cos, 4)}</td><td>${formatarNumero(g.sen, 4)}</td></tr>`).join('');
  return `<section class="passo">
    <h3>Passo 3 — Geometria de cada barra</h3>
    <p>Δx = x<sub>final</sub> − x<sub>inicial</sub>, Δy = y<sub>final</sub> − y<sub>inicial</sub>,
      L = √(Δx² + Δy²), cos θ = Δx / L e sen θ = Δy / L. O cos e o sen dizem quanto da força da barra vai para x e quanto vai para y.</p>
    <div class="rolagem"><table class="dados">
      <thead><tr><th>Barra</th><th>Δx (${unidades.comprimento})</th><th>Δy (${unidades.comprimento})</th><th>L (${unidades.comprimento})</th><th>cos θ</th><th>sen θ</th></tr></thead>
      <tbody>${linhas}</tbody></table></div>
  </section>`;
}

function passoEquacoes(resultado) {
  const { trelica, incognitas, sistema } = resultado;
  const blocos = trelica.nos.map((no, indiceDoNo) => {
    const direcoes = trelica.barras
      .filter(barra => barra.no1 === no.nome || barra.no2 === no.nome)
      .map(barra => {
        const outro = buscarNo(trelica, barra.no1 === no.nome ? barra.no2 : barra.no1);
        const dx = outro.x - no.x;
        const dy = outro.y - no.y;
        const comprimento = Math.sqrt(dx * dx + dy * dy);
        return `<li>N${nomeDaBarra(barra)}: de ${no.nome} para ${outro.nome} →
          (${formatarNumero(dx, 2)}; ${formatarNumero(dy, 2)}) ÷ ${formatarNumero(comprimento, 4)} =
          (<strong>${formatarNumero(dx / comprimento, 4)}</strong>; <strong>${formatarNumero(dy / comprimento, 4)}</strong>)</li>`;
      }).join('');

    const equacoes = ['x', 'y'].map((direcao, d) => {
      const linha = sistema.matriz[2 * indiceDoNo + d];
      const carga = direcao === 'x' ? no.fx : no.fy;
      const termos = linha.map((coef, j) => ({ valor: coef, nome: incognitas[j].nome, casas: 4 }));
      termos.push({ valor: carga, nome: '', casas: 3 });
      return `ΣF${direcao} = 0:  ${escreverTermos(termos)} = 0`;
    }).join('\n');

    const reacoes = TIPOS_DE_APOIO[no.apoio].reacoes.map(direcao => no.nome + direcao).join(' e ');
    return `<div class="bloco-no">
      <h4>Nó ${no.nome}</h4>
      <p>Direção de cada barra saindo do nó (vetor unitário):</p>
      <ul>${direcoes}</ul>
      <p>Reações neste nó: ${reacoes || 'nenhuma'} · Carga: Fx = ${formatarNumero(no.fx, 2)}, Fy = ${formatarNumero(no.fy, 2)}</p>
      <pre>${equacoes}</pre>
    </div>`;
  }).join('');

  return `<section class="passo">
    <h3>Passo 4 — Equações de equilíbrio de cada nó (método dos nós)</h3>
    <p>Supomos todas as barras em <strong>tração</strong>: a barra puxa o nó na direção do outro nó.
      Por isso o coeficiente de cada N é a direção "do nó para o outro nó". Se a resposta der negativa, a barra está em compressão.
      Reações entram com coeficiente 1 (positivas para a direita e para cima), e as cargas entram com o seu próprio valor.</p>
    <div class="grade-nos">${blocos}</div>
  </section>`;
}

function passoMatriz(resultado) {
  const { incognitas, sistema } = resultado;
  const rotulos = sistema.equacoes.map(rotuloDaEquacao);
  return `<section class="passo">
    <h3>Passo 5 — Sistema na forma de matriz: [A]·{x} = {c}</h3>
    <p>Cada equação vira uma linha. Cada incógnita vira uma coluna. As cargas passam para o outro lado do sinal de igual,
      por isso <strong>c = −carga</strong>. Tamanho: ${sistema.matriz.length} equações × ${incognitas.length} incógnitas.</p>
    ${tabelaDeMatriz(incognitas.map(incognita => incognita.nome), rotulos, sistema.matriz, sistema.vetor)}
  </section>`;
}

function passoGauss(resultado) {
  const { incognitas, gauss } = resultado;
  const operacoes = gauss.etapas.map(etapa => {
    if (etapa.tipo === 'troca') {
      return `<li>L${etapa.linhaA + 1} ↔ L${etapa.linhaB + 1} (troca de linhas para usar o maior pivô da coluna)</li>`;
    }
    return `<li>L${etapa.linha + 1} ← L${etapa.linha + 1} − (${formatarNumero(etapa.fator, 4)}) × L${etapa.linhaDoPivo + 1}</li>`;
  }).join('');

  const listaDeOperacoes = `<details ${gauss.etapas.length <= 25 ? 'open' : ''}>
    <summary>${gauss.etapas.length} operações de linha</summary><ol>${operacoes}</ol></details>`;

  if (!gauss.sucesso) {
    return `<section class="passo">
      <h3>Passo 6 — Eliminação de Gauss</h3>
      ${listaDeOperacoes}
      <p class="erro">Na coluna de <strong>${incognitas[gauss.colunaSemPivo].nome}</strong> todos os valores possíveis para pivô são zero.
        Isso quer dizer que as equações não são independentes: a treliça pode se mover sem deformar as barras (é instável),
        e não existe uma resposta única.</p>
    </section>`;
  }

  const a = gauss.matrizTriangular;
  const c = gauss.vetorTriangular;
  const x = gauss.solucao;
  const substituicoes = [];
  for (let linha = x.length - 1; linha >= 0; linha--) {
    let soma = 0;
    for (let k = linha + 1; k < x.length; k++) soma += a[linha][k] * x[k];
    substituicoes.push(`<li>${incognitas[linha].nome} = (${formatarNumero(c[linha], 4)} − ${formatarEntreParenteses(soma, 4)}) ÷ ${formatarEntreParenteses(a[linha][linha], 4)}
      = <strong>${formatarNumero(x[linha], 4)}</strong></li>`);
  }

  return `<section class="passo">
    <h3>Passo 6 — Resolução pela eliminação de Gauss</h3>
    <p><strong>Ida (escalonamento):</strong> para cada coluna, escolhemos o maior valor como pivô e zeramos tudo abaixo dele,
      subtraindo múltiplos da linha do pivô. Fazer a mesma operação dos dois lados não muda a solução.</p>
    ${listaDeOperacoes}
    <p>Matriz depois do escalonamento (tudo abaixo da diagonal é zero):</p>
    ${tabelaDeMatriz(incognitas.map(incognita => incognita.nome), a.map((linha, i) => 'L' + (i + 1)), a, c)}
    <p><strong>Volta (substituição):</strong> a última linha tem só uma incógnita. Achamos ela e subimos linha por linha:
      incógnita = (c − soma dos termos já conhecidos) ÷ pivô.</p>
    <ol class="substituicao">${substituicoes.join('')}</ol>
  </section>`;
}

function passoResultados(resultado, unidades) {
  const linhasBarras = resultado.barras.map(barra => `<tr><td>${barra.nome}</td>
    <td class="numero">${formatarComSinal(barra.forca)}</td><td class="${barra.situacao === 'Tração' ? 'tracao' : barra.situacao === 'Compressão' ? 'compressao' : 'nula'}">${barra.situacao}</td></tr>`).join('');
  const linhasReacoes = resultado.reacoes.map(reacao => {
    const sentido = reacao.valor === 0 ? 'nula' :
      reacao.direcao === 'x' ? (reacao.valor > 0 ? 'para a direita →' : 'para a esquerda ←') :
      (reacao.valor > 0 ? 'para cima ↑' : 'para baixo ↓');
    return `<tr><td>${reacao.nome}</td><td class="numero">${formatarComSinal(reacao.valor)}</td><td>${sentido}</td></tr>`;
  }).join('');
  return `<section class="passo">
    <h3>Passo 7 — Interpretação dos resultados</h3>
    <p><strong>N &gt; 0 → tração</strong> (a barra é puxada, tende a alongar). <strong>N &lt; 0 → compressão</strong>
      (a barra é empurrada, tende a encurtar). N = 0 → barra de força zero.
      Reação negativa quer dizer que ela age no sentido contrário ao que supusemos.</p>
    <div class="lado-a-lado">
      <table class="dados"><thead><tr><th>Barra</th><th>N (${unidades.forca})</th><th>Situação</th></tr></thead><tbody>${linhasBarras}</tbody></table>
      <table class="dados"><thead><tr><th>Reação</th><th>Valor (${unidades.forca})</th><th>Sentido</th></tr></thead><tbody>${linhasReacoes}</tbody></table>
    </div>
  </section>`;
}

function passoConferencia(resultado, unidades) {
  const { sistema, incognitas, valores, conferencia, trelica, reacoes } = resultado;
  const linhas = sistema.matriz.map((linha, i) => {
    const termos = linha.map((coef, j) => coef === 0 ? null :
      formatarEntreParenteses(coef, 4) + '×' + formatarEntreParenteses(valores[j], 3)).filter(Boolean);
    const carga = sistema.equacoes[i].carga;
    const soma = conferencia.residuos[i];
    return `<tr><td>${rotuloDaEquacao(sistema.equacoes[i])}</td><td class="esquerda">${termos.join(' + ')} + ${formatarEntreParenteses(carga, 3)}</td>
      <td class="numero">${formatarNumero(soma, 6)}</td><td>${Math.abs(soma) < 1e-6 ? '✓' : '✗'}</td></tr>`;
  }).join('');

  const termosMomento = [];
  const adicionarMomento = (no, forcaX, forcaY) => {
    if (forcaY !== 0 && no.x !== 0) termosMomento.push(`${formatarEntreParenteses(no.x, 2)}×${formatarEntreParenteses(forcaY, 2)}`);
    if (forcaX !== 0 && no.y !== 0) termosMomento.push(`${formatarEntreParenteses(-no.y, 2)}×${formatarEntreParenteses(forcaX, 2)}`);
  };
  trelica.nos.forEach(no => adicionarMomento(no, no.fx, no.fy));
  reacoes.forEach(reacao => {
    const no = buscarNo(trelica, reacao.no);
    if (reacao.direcao === 'x') adicionarMomento(no, reacao.valor, 0);
    else adicionarMomento(no, 0, reacao.valor);
  });

  return `<section class="passo">
    <h3>Passo 8 — Conferência (prova real)</h3>
    <p>Substituímos as respostas de volta em cada equação. Todas precisam dar zero.</p>
    <div class="rolagem"><table class="dados conferencia">
      <thead><tr><th>Equação</th><th>Coeficiente × valor encontrado + carga</th><th>Soma</th><th></th></tr></thead>
      <tbody>${linhas}</tbody></table></div>
    <p>Equilíbrio da treliça inteira (cargas + reações), com momentos em relação à origem (0; 0), M = x·Fy − y·Fx:</p>
    <ul>
      <li>ΣFx = ${formatarNumero(conferencia.somaFx, 6)} ${unidades.forca} ${conferencia.somaFx === 0 ? '✓' : '✗'}</li>
      <li>ΣFy = ${formatarNumero(conferencia.somaFy, 6)} ${unidades.forca} ${conferencia.somaFy === 0 ? '✓' : '✗'}</li>
      <li>ΣM = ${termosMomento.join(' + ') || '0'} = ${formatarNumero(conferencia.somaMomentos, 6)} ${conferencia.somaMomentos === 0 ? '✓' : '✗'}</li>
    </ul>
  </section>`;
}

function passoTensoes(resultado, unidades) {
  const temDados = resultado.tensoes.some(t => t.area !== null || t.admissivel !== null);
  if (!temDados) {
    return `<section class="passo">
      <h3>Passo 9 — Tensão normal (opcional)</h3>
      <p>Informe a área das barras e/ou a tensão admissível para ver σ = N / A e a área necessária.</p>
    </section>`;
  }
  const fator = unidades.fatorTensao;
  const textoFator = fator === 1 ? '' : ` × ${formatarNumero(fator, 0)}`;
  const linhas = resultado.tensoes.map(t => {
    const sigma = t.area === null ? '—' :
      `${formatarNumero(t.forca, 3)}${textoFator} ÷ ${formatarNumero(t.area, 2)} = <strong>${formatarNumero(t.tensao, 3)}</strong>`;
    const areaNecessaria = t.admissivel === null ? '—' :
      `|${formatarNumero(t.forca, 3)}|${textoFator} ÷ ${formatarNumero(t.admissivel, 2)} = <strong>${formatarNumero(t.areaNecessaria, 3)}</strong>`;
    return `<tr><td>${t.nome}</td><td class="esquerda">${sigma}</td><td class="esquerda">${areaNecessaria}</td><td>${t.verificacao || '—'}</td></tr>`;
  }).join('');
  return `<section class="passo">
    <h3>Passo 9 — Tensão normal e área necessária</h3>
    <p>σ = N ÷ A (${unidades.tensao}). Área necessária: A = |N| ÷ σ<sub>adm</sub> (${unidades.area}).
      ${fator === 1 ? '' : `O fator ${formatarNumero(fator, 0)} converte ${unidades.forca}/${unidades.area} em ${unidades.tensao} (1 kN/mm² = 1000 MPa).`}
      Tração usa σ<sub>adm</sub> de tração e compressão usa σ<sub>adm</sub> de compressão.</p>
    <div class="rolagem"><table class="dados">
      <thead><tr><th>Barra</th><th>σ = N ÷ A (${unidades.tensao})</th><th>A necessária (${unidades.area})</th><th>|σ| ≤ σ<sub>adm</sub>?</th></tr></thead>
      <tbody>${linhas}</tbody></table></div>
  </section>`;
}

function gerarPassoAPasso(resultado) {
  if (!resultado) {
    return '<p class="aviso">Clique em <strong>Calcular</strong> para ver o cálculo passo a passo.</p>';
  }
  if (resultado.etapa === 'validacao') {
    return `<p class="erro">${resultado.mensagem}</p><ul>${resultado.erros.map(erro => `<li>${erro}</li>`).join('')}</ul>`;
  }

  const unidades = SISTEMAS_DE_UNIDADES[resultado.trelica.unidades];
  const partes = [
    passoDados(resultado, unidades),
    passoIncognitas(resultado),
    passoGeometria(resultado, unidades),
    passoEquacoes(resultado),
    passoMatriz(resultado)
  ];

  if (resultado.etapa === 'estaticidade') {
    partes.push(`<section class="passo"><h3>Parada</h3><p class="erro">${resultado.mensagem}</p>
      <p>Com ${resultado.sistema.matriz.length} equações e ${resultado.incognitas.length} incógnitas a matriz não é quadrada,
        então o programa para aqui, como o MDSolids.</p></section>`);
    return partes.join('');
  }

  partes.push(passoGauss(resultado));
  if (!resultado.sucesso) return partes.join('');

  partes.push(passoResultados(resultado, unidades));
  partes.push(passoConferencia(resultado, unidades));
  partes.push(passoTensoes(resultado, unidades));
  return partes.join('');
}
