let trelica = null;
let resultadoAtual = null;

function elemento(id) {
  return document.getElementById(id);
}

function limparNome(texto) {
  return String(texto).replace(/[^A-Za-z0-9]/g, '').slice(0, 4).toUpperCase();
}

function nomeDaPosicao(posicao) {
  const letra = String.fromCharCode(65 + (posicao % 26));
  return posicao < 26 ? letra : letra + Math.floor(posicao / 26);
}

function proximoNomeLivre() {
  const usados = trelica.nos.map(no => no.nome);
  let posicao = 0;
  while (usados.includes(nomeDaPosicao(posicao))) posicao++;
  return nomeDaPosicao(posicao);
}

function criarTrelicaVazia() {
  return { unidades: 'kn_mm', tensaoAdmTracao: 0, tensaoAdmCompressao: 0, nos: [], barras: [] };
}

function normalizarTrelica(dados) {
  const nova = criarTrelicaVazia();
  if (SISTEMAS_DE_UNIDADES[dados.unidades]) nova.unidades = dados.unidades;
  nova.tensaoAdmTracao = Number(dados.tensaoAdmTracao) || 0;
  nova.tensaoAdmCompressao = Number(dados.tensaoAdmCompressao) || 0;
  nova.nos = (dados.nos || []).map(no => ({
    nome: limparNome(no.nome),
    x: Number(no.x) || 0,
    y: Number(no.y) || 0,
    apoio: TIPOS_DE_APOIO[no.apoio] ? no.apoio : 'livre',
    fx: Number(no.fx) || 0,
    fy: Number(no.fy) || 0
  }));
  nova.barras = (dados.barras || []).map(barra => ({
    no1: limparNome(barra.no1),
    no2: limparNome(barra.no2),
    area: Number(barra.area) || 0
  }));
  return nova;
}

function opcoes(lista, selecionado) {
  return lista.map(item =>
    `<option value="${item.valor}" ${item.valor === selecionado ? 'selected' : ''}>${item.texto}</option>`).join('');
}

function mostrarTabelaDeNos() {
  const tiposDeApoio = Object.keys(TIPOS_DE_APOIO).map(chave => ({ valor: chave, texto: TIPOS_DE_APOIO[chave].descricao }));
  elemento('corpo-nos').innerHTML = trelica.nos.map((no, i) => `
    <tr>
      <td class="nome-no">${no.nome}</td>
      <td><input type="number" step="any" data-indice="${i}" data-campo="x" value="${no.x}"></td>
      <td><input type="number" step="any" data-indice="${i}" data-campo="y" value="${no.y}"></td>
      <td><select data-indice="${i}" data-campo="apoio">${opcoes(tiposDeApoio, no.apoio)}</select></td>
      <td><input type="number" step="any" data-indice="${i}" data-campo="fx" value="${no.fx}"></td>
      <td><input type="number" step="any" data-indice="${i}" data-campo="fy" value="${no.fy}"></td>
      <td><button class="remover" data-indice="${i}" title="Remover o nó ${no.nome}">×</button></td>
    </tr>`).join('');
}

function mostrarTabelaDeBarras() {
  const nomesDosNos = trelica.nos.map(no => ({ valor: no.nome, texto: no.nome }));
  elemento('corpo-barras').innerHTML = trelica.barras.map((barra, i) => `
    <tr>
      <td class="nome-no">${nomeDaBarra(barra)}</td>
      <td><select data-indice="${i}" data-campo="no1">${opcoes(nomesDosNos, barra.no1)}</select></td>
      <td><select data-indice="${i}" data-campo="no2">${opcoes(nomesDosNos, barra.no2)}</select></td>
      <td><input type="number" step="any" min="0" data-indice="${i}" data-campo="area" value="${barra.area}"></td>
      <td><button class="remover" data-indice="${i}" title="Remover a barra ${nomeDaBarra(barra)}">×</button></td>
    </tr>`).join('');
}

function mostrarUnidades() {
  const unidades = SISTEMAS_DE_UNIDADES[trelica.unidades];
  document.querySelectorAll('[data-unidade]').forEach(campo => {
    campo.textContent = unidades[campo.dataset.unidade];
  });
  elemento('selecao-unidades').value = trelica.unidades;
  elemento('tensao-tracao').value = trelica.tensaoAdmTracao;
  elemento('tensao-compressao').value = trelica.tensaoAdmCompressao;
}

// Opções do desenho lidas da tela (rótulos, grade e espessura).
function opcoesDoDesenho() {
  return {
    rotulos: elemento('selecao-rotulos').value,
    grade: elemento('mostrar-grade').checked,
    espessura: elemento('espessura-proporcional').checked
  };
}

function desenhar() {
  desenharTrelica(elemento('desenho'), trelica, resultadoAtual, opcoesDoDesenho());
}

function mostrarTudo() {
  mostrarTabelaDeNos();
  mostrarTabelaDeBarras();
  mostrarUnidades();
  aoMudarDados();
}

function aoMudarDados() {
  resultadoAtual = null;
  desenhar();
  mostrarResultados();
  elemento('conteudo-passo-a-passo').innerHTML = gerarPassoAPasso(null);
}

function calcular() {
  resultadoAtual = resolverTrelica(trelica);
  desenhar();
  mostrarResultados();
  elemento('conteudo-passo-a-passo').innerHTML = gerarPassoAPasso(resultadoAtual);
}

// Redesenha tela e passo a passo com o resultado que já está na memória.
// Usado ao trocar as casas decimais: não é preciso calcular a treliça de novo.
function redesenharTudo() {
  desenhar();
  mostrarResultados();
  elemento('conteudo-passo-a-passo').innerHTML = gerarPassoAPasso(resultadoAtual);
}

function mostrarResultados() {
  const caixa = elemento('conteudo-resultados');
  const r = resultadoAtual;
  if (!r) {
    caixa.innerHTML = '<p class="aviso">Clique em <strong>Calcular</strong> para resolver a treliça.</p>';
    return;
  }
  if (!r.sucesso) {
    const lista = r.erros ? `<ul>${r.erros.map(erro => `<li>${erro}</li>`).join('')}</ul>` : '';
    caixa.innerHTML = `<p class="erro">${r.mensagem}</p>${lista}`;
    return;
  }

  const u = SISTEMAS_DE_UNIDADES[trelica.unidades];
  const e = r.estaticidade;
  const linhasReacoes = r.reacoes.map(reacao => `<tr><td>${reacao.nome}</td><td class="numero">${formatarComSinal(reacao.valor)}</td></tr>`).join('');
  const ordemAlfabetica = r.barras.map((barra, i) => i).sort((i, j) => r.barras[i].nome.localeCompare(r.barras[j].nome));
  const linhasBarras = ordemAlfabetica.map(i => {
    const barra = r.barras[i];
    const t = r.tensoes[i];
    const classe = barra.situacao === 'Tração' ? 'tracao' : barra.situacao === 'Compressão' ? 'compressao' : 'nula';
    return `<tr data-barra="${barra.nome}"><td>${barra.nome}</td><td class="numero">${formatarNumero(barra.comprimento)}</td>
      <td class="numero">${formatarNumero(barra.anguloGraus)}</td>
      <td class="numero">${formatarComSinal(barra.forca)}</td><td class="${classe}">${barra.situacao}</td>
      <td class="numero">${formatarNumero(t.area, 2)}</td><td class="numero">${formatarComSinal(t.tensao)}</td>
      <td class="numero">${formatarNumero(t.areaNecessaria)}</td><td class="${t.verificacao === 'Excede' ? 'compressao' : ''}">${t.verificacao || '—'}</td></tr>`;
  }).join('');
  const zeradas = r.barras.filter(barra => barra.situacao === 'Força zero').map(barra => barra.nome);
  const c = r.conferencia;

  caixa.innerHTML = `
    <p class="sucesso">Treliça ${e.tipo}: b + r = ${e.b} + ${e.r} = ${e.incognitas} = 2n = ${e.equacoes}. Resolvida.</p>
    <div class="lado-a-lado">
      <div>
        <h3>Reações de apoio</h3>
        <table class="dados"><thead><tr><th>Reação</th><th>Valor (${u.forca})</th></tr></thead><tbody>${linhasReacoes}</tbody></table>
        <h3>Conferência</h3>
        <p>ΣFx = ${formatarNumero(c.somaFx)} · ΣFy = ${formatarNumero(c.somaFy)} · ΣM = ${formatarNumero(c.somaMomentos)}
          ${c.somaFx === 0 && c.somaFy === 0 && c.somaMomentos === 0 ? '✓ equilíbrio verificado' : '✗'}</p>
        <p>Barras de força zero: ${zeradas.length ? zeradas.join(', ') : 'nenhuma'}</p>
      </div>
      <div class="rolagem">
        <div class="titulo-tabela">
          <h3>Forças nas barras <small>(+ tração, − compressão)</small></h3>
          <button id="botao-copiar-resumo" class="secundario">Copiar resumo</button>
        </div>
        <table class="dados">
          <thead><tr><th>Barra</th><th>L (${u.comprimento})</th><th>θ (°)</th><th>N (${u.forca})</th><th>Situação</th>
            <th>A (${u.area})</th><th>σ (${u.tensao})</th><th>A nec. (${u.area})</th><th>Tensão</th></tr></thead>
          <tbody>${linhasBarras}</tbody>
        </table>
      </div>
    </div>`;
}


// Texto da lista de forças para copiar (ordem alfabética, valor em módulo + tipo).
function resumoDasForcas() {
  if (!resultadoAtual || !resultadoAtual.sucesso) return '';
  return resultadoAtual.barras
    .slice()
    .sort((a, b) => a.nome.localeCompare(b.nome))
    .map(barra => `${barra.nome}: ${formatarNumero(Math.abs(barra.forca))} kN (${barra.situacao})`)
    .join('\n');
}

function copiarResumo() {
  const texto = resumoDasForcas();
  if (!texto) return;
  const botao = elemento('botao-copiar-resumo');
  const avisar = () => {
    const original = botao.textContent;
    botao.textContent = 'Copiado!';
    setTimeout(() => { botao.textContent = original; }, 1500);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(texto).then(avisar, () => copiarComTextarea(texto, avisar));
  } else {
    copiarComTextarea(texto, avisar);
  }
}

// Alternativa para quando a área de transferência não está disponível.
function copiarComTextarea(texto, avisar) {
  const area = document.createElement('textarea');
  area.value = texto;
  area.setAttribute('readonly', '');
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.appendChild(area);
  area.select();
  try {
    document.execCommand('copy');
    avisar();
  } catch (erro) {
    alert('Não foi possível copiar. Selecione o texto manualmente.');
  }
  document.body.removeChild(area);
}

// Destaque sincronizado entre a tabela de forças e o desenho.
function destacarBarra(nome) {
  document.querySelectorAll('[data-barra]').forEach(alvo => {
    const igual = nome !== null && alvo.dataset.barra === nome;
    alvo.classList.toggle('barra-destaque', igual);
    alvo.classList.toggle('barra-atenuada', nome !== null && !igual);
    if (alvo.tagName === 'TR') alvo.classList.toggle('linha-destaque', igual);
  });
}

function ligarDestaque() {
  const caixa = elemento('conteudo-resultados');
  caixa.addEventListener('mouseover', evento => {
    const linha = evento.target.closest('tr[data-barra]');
    destacarBarra(linha ? linha.dataset.barra : null);
  });
  caixa.addEventListener('mouseleave', () => destacarBarra(null));
  const svg = elemento('desenho');
  svg.addEventListener('mouseover', evento => {
    const grupo = evento.target.closest('[data-barra]');
    destacarBarra(grupo ? grupo.dataset.barra : null);
  });
  svg.addEventListener('mouseleave', () => destacarBarra(null));
}
function adicionarNo() {
  trelica.nos.push({ nome: proximoNomeLivre(), x: 0, y: 0, apoio: 'livre', fx: 0, fy: 0 });
  mostrarTabelaDeNos();
  mostrarTabelaDeBarras();
  aoMudarDados();
}

function adicionarBarra() {
  if (trelica.nos.length < 2) return;
  trelica.barras.push({ no1: trelica.nos[0].nome, no2: trelica.nos[trelica.nos.length - 1].nome, area: 0 });
  mostrarTabelaDeBarras();
  aoMudarDados();
}

function alterarNo(campo) {
  const no = trelica.nos[campo.dataset.indice];
  if (campo.dataset.campo === 'apoio') no.apoio = campo.value;
  else no[campo.dataset.campo] = Number(campo.value);
  aoMudarDados();
}

function alterarBarra(campo) {
  const barra = trelica.barras[campo.dataset.indice];
  if (campo.dataset.campo === 'area') {
    barra.area = Number(campo.value);
  } else {
    barra[campo.dataset.campo] = campo.value;
    mostrarTabelaDeBarras();
  }
  aoMudarDados();
}

function removerNo(indice) {
  const nome = trelica.nos[indice].nome;
  trelica.nos.splice(indice, 1);
  trelica.barras = trelica.barras.filter(barra => barra.no1 !== nome && barra.no2 !== nome);
  mostrarTabelaDeNos();
  mostrarTabelaDeBarras();
  aoMudarDados();
}

function removerBarra(indice) {
  trelica.barras.splice(indice, 1);
  mostrarTabelaDeBarras();
  aoMudarDados();
}

function aplicarAreaEmTodas() {
  const area = Number(elemento('area-todas').value) || 0;
  trelica.barras.forEach(barra => { barra.area = area; });
  mostrarTabelaDeBarras();
  aoMudarDados();
}

function carregarExemplo(indice) {
  trelica = normalizarTrelica(EXEMPLOS[indice]);
  mostrarTudo();
}

function salvarArquivo() {
  const texto = JSON.stringify(trelica, null, 2);
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([texto], { type: 'application/json' }));
  link.download = 'trelica.json';
  link.click();
  URL.revokeObjectURL(link.href);
}

function abrirArquivo(arquivo) {
  const leitor = new FileReader();
  leitor.onload = () => {
    try {
      trelica = normalizarTrelica(JSON.parse(leitor.result));
      elemento('selecao-exemplo').value = '';
      mostrarTudo();
    } catch (erro) {
      alert('Não foi possível ler o arquivo. Ele precisa ser um JSON salvo por este programa.');
    }
  };
  leitor.readAsText(arquivo);
}

function trocarAba(nomeDaAba) {
  document.querySelectorAll('.aba').forEach(botao => botao.classList.toggle('ativa', botao.dataset.aba === nomeDaAba));
  elemento('conteudo-resultados').hidden = nomeDaAba !== 'resultados';
  elemento('conteudo-passo-a-passo').hidden = nomeDaAba !== 'passo-a-passo';
}

function ligarEventos() {
  elemento('selecao-exemplo').addEventListener('change', evento => {
    if (evento.target.value !== '') carregarExemplo(Number(evento.target.value));
  });
  elemento('selecao-unidades').addEventListener('change', evento => {
    trelica.unidades = evento.target.value;
    mostrarUnidades();
    aoMudarDados();
  });
  elemento('tensao-tracao').addEventListener('input', evento => {
    trelica.tensaoAdmTracao = Number(evento.target.value) || 0;
    aoMudarDados();
  });
  elemento('tensao-compressao').addEventListener('input', evento => {
    trelica.tensaoAdmCompressao = Number(evento.target.value) || 0;
    aoMudarDados();
  });

  elemento('corpo-nos').addEventListener('input', evento => alterarNo(evento.target));
  elemento('corpo-barras').addEventListener('change', evento => alterarBarra(evento.target));
  elemento('corpo-nos').addEventListener('click', evento => {
    if (evento.target.classList.contains('remover')) removerNo(Number(evento.target.dataset.indice));
  });
  elemento('corpo-barras').addEventListener('click', evento => {
    if (evento.target.classList.contains('remover')) removerBarra(Number(evento.target.dataset.indice));
  });

  elemento('botao-adicionar-no').addEventListener('click', adicionarNo);
  elemento('botao-adicionar-barra').addEventListener('click', adicionarBarra);
  elemento('botao-aplicar-area').addEventListener('click', aplicarAreaEmTodas);
  elemento('botao-calcular').addEventListener('click', calcular);
  elemento('corpo-barras').addEventListener('input', evento => {
    if (evento.target.dataset.campo === 'area') alterarBarra(evento.target);
  });
  elemento('selecao-casas').addEventListener('change', evento => {
    casasDecimaisPadrao = Number(evento.target.value) || 3;
    redesenharTudo();
  });
  ['selecao-rotulos', 'mostrar-grade', 'espessura-proporcional'].forEach(id =>
    elemento(id).addEventListener('change', desenhar));
  elemento('conteudo-resultados').addEventListener('click', evento => {
    if (evento.target.id === 'botao-copiar-resumo') copiarResumo();
  });
  ligarDestaque();

  elemento('botao-novo').addEventListener('click', () => {
    trelica = criarTrelicaVazia();
    elemento('selecao-exemplo').value = '';
    mostrarTudo();
  });
  elemento('botao-salvar').addEventListener('click', salvarArquivo);
  elemento('botao-abrir').addEventListener('click', () => elemento('arquivo').click());
  elemento('arquivo').addEventListener('change', evento => {
    if (evento.target.files.length > 0) abrirArquivo(evento.target.files[0]);
    evento.target.value = '';
  });
  elemento('botao-imprimir').addEventListener('click', () => window.print());

  document.querySelectorAll('.aba').forEach(botao => botao.addEventListener('click', () => trocarAba(botao.dataset.aba)));
}

function iniciar() {
  elemento('selecao-exemplo').innerHTML = '<option value="">— escolha —</option>' +
    EXEMPLOS.map((exemplo, i) => `<option value="${i}">${exemplo.titulo}</option>`).join('');
  elemento('selecao-unidades').innerHTML = Object.keys(SISTEMAS_DE_UNIDADES)
    .map(chave => `<option value="${chave}">${SISTEMAS_DE_UNIDADES[chave].descricao}</option>`).join('');
  elemento('selecao-casas').value = String(casasDecimaisPadrao);
  ligarEventos();
  elemento('selecao-exemplo').value = '0';
  carregarExemplo(0);
  trocarAba('resultados');
}

iniciar();
