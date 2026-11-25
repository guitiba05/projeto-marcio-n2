// Quadro "Posicionar nó por ângulo": lê o ângulo da figura e calcula as coordenadas do nó.
// A conta fica em posicionarPorAngulo (calculo.js); aqui só lemos a tela e aplicamos o resultado.

function mostrarSeletoresDePosicao() {
  const nomes = trelica.nos.map(no => ({ valor: no.nome, texto: no.nome }));
  ['pos-no', 'pos-ref'].forEach(id => {
    const seletor = elemento(id);
    seletor.innerHTML = opcoes(nomes, seletor.value);
  });
  if (elemento('pos-no').value === elemento('pos-ref').value && trelica.nos.length > 1) {
    elemento('pos-no').value = trelica.nos[trelica.nos.length - 1].nome;
  }
  mostrarPreviaDaPosicao();
}

function calcularPosicao() {
  const no = buscarNo(trelica, elemento('pos-no').value);
  const referencia = buscarNo(trelica, elemento('pos-ref').value);
  if (!no || !referencia) return { erro: 'Cadastre pelo menos 2 nós.' };
  if (no === referencia) return { erro: 'Escolha nós diferentes.' };
  const resultado = posicionarPorAngulo(
    referencia,
    Number(elemento('pos-angulo').value),
    elemento('pos-sentido').value,
    { tipo: elemento('pos-dado').value, valor: Number(elemento('pos-valor').value) }
  );
  if (resultado.erro) return resultado;
  const arredondar = elemento('pos-arredondar').checked;
  const limpar = valor => arredondar ? Math.round(valor) : Math.round(valor * 1e6) / 1e6;
  return { no: no, referencia: referencia, x: limpar(resultado.x), y: limpar(resultado.y) };
}

function mostrarPreviaDaPosicao() {
  const posicao = calcularPosicao();
  elemento('pos-previa').textContent = posicao.erro
    ? '→ ' + posicao.erro
    : `→ ${posicao.no.nome} = (${formatarNumero(posicao.x)} ; ${formatarNumero(posicao.y)})`;
}

function aplicarPosicao() {
  const posicao = calcularPosicao();
  if (posicao.erro) {
    alert(posicao.erro);
    return;
  }
  posicao.no.x = posicao.x;
  posicao.no.y = posicao.y;
  const nomes = [posicao.no.nome, posicao.referencia.nome].sort().join('-');
  const barraExiste = trelica.barras.some(barra => [barra.no1, barra.no2].sort().join('-') === nomes);
  if (elemento('pos-criar-barra').checked && !barraExiste) {
    trelica.barras.push({ no1: posicao.referencia.nome, no2: posicao.no.nome, area: 0 });
  }
  mostrarTabelaDeNos();
  mostrarTabelaDeBarras();
  aoMudarDados();
}

function ligarPosicionarNo() {
  elemento('pos-sentido').innerHTML = Object.keys(SENTIDOS_DA_BARRA)
    .map(chave => `<option value="${chave}">${SENTIDOS_DA_BARRA[chave].descricao}</option>`).join('');
  ['pos-no', 'pos-ref', 'pos-sentido', 'pos-dado', 'pos-arredondar'].forEach(id =>
    elemento(id).addEventListener('change', mostrarPreviaDaPosicao));
  ['pos-angulo', 'pos-valor'].forEach(id => elemento(id).addEventListener('input', mostrarPreviaDaPosicao));
  elemento('botao-posicionar').addEventListener('click', aplicarPosicao);
}
