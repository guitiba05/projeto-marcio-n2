// Formatação de números. O cálculo é sempre em dupla precisão; só a saída é arredondada.
// casasDecimaisPadrao é controlado pelo seletor "Casas" do cabeçalho (2, 3 ou 4).
let casasDecimaisPadrao = 3;

// Arredonda compensando o erro binário: 7,725 pode estar guardado como 7,72499999...
// e cair para 7,72. O epsilon empurra o valor para o lado certo antes de arredondar.
function arredondarSeguro(valor, casas) {
  const fator = Math.pow(10, casas);
  const epsilon = Math.sign(valor) * 1e-12;
  const arredondado = Math.round((valor + epsilon) * fator) / fator;
  return Math.abs(arredondado) < 1e-12 ? 0 : arredondado;
}

function formatarNumero(valor, casas = casasDecimaisPadrao) {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '—';
  const numero = arredondarSeguro(valor, casas);
  return numero.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }).replace('-', '−');
}

function formatarComSinal(valor, casas = casasDecimaisPadrao) {
  const texto = formatarNumero(valor, casas);
  return valor > 0 && texto !== formatarNumero(0, casas) ? '+' + texto : texto;
}

function formatarEntreParenteses(valor, casas = casasDecimaisPadrao) {
  return valor < 0 ? '(' + formatarNumero(valor, casas) + ')' : formatarNumero(valor, casas);
}