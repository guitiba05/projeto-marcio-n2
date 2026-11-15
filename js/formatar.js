function formatarNumero(valor, casas = 3) {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '—';
  const limite = 0.5 * Math.pow(10, -casas);
  const numero = Math.abs(valor) < limite ? 0 : valor;
  return numero.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }).replace('-', '−');
}

function formatarComSinal(valor, casas = 3) {
  const texto = formatarNumero(valor, casas);
  return valor > 0 && texto !== formatarNumero(0, casas) ? '+' + texto : texto;
}

function formatarEntreParenteses(valor, casas = 3) {
  return valor < 0 ? '(' + formatarNumero(valor, casas) + ')' : formatarNumero(valor, casas);
}
