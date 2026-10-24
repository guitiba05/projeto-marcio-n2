/* ============================================================================
   results.js — painel de resultados.

   Recebe o objeto de saída do solver e monta as tabelas. Todos os números já
   vêm convertidos para as unidades de entrada, então aqui só há formatação.
   ========================================================================== */

const Results = (() => {
  const body = document.getElementById('results-body');
  const stateChip = document.getElementById('results-state');

  const esc = (value) =>
    String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

  function num(value, decimals = 3) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '—';
    const rounded = Math.round(number * 10 ** decimals) / 10 ** decimals;
    const text = (rounded === 0 ? 0 : rounded).toFixed(decimals);
    return text.replace('-', '\u2212');
  }

  function tiny(value) {
    const number = Math.abs(Number(value));
    if (!Number.isFinite(number)) return '—';
    if (number === 0) return '0';
    if (number < 1e-4) return number.toExponential(2).replace('-', '\u2212').replace('e', '·10^');
    return num(number, 6);
  }

  function stateClass(state) {
    if (state === 'tração') return 'state-tensao';
    if (state === 'compressão') return 'state-compressao';
    return 'state-zero';
  }

  function setChip(kind, text) {
    stateChip.className = `chip ${kind}`;
    stateChip.textContent = text;
  }

  function renderErrors(solution) {
    setChip('bad', 'não foi possível calcular');
    const items = (solution.errors || []).map((error) => `<li>${esc(error.message)}</li>`);
    let html = `<div class="block"><h4>Entrada recusada</h4>
      <ul class="errors">${items.join('')}</ul></div>`;

    if (solution.determinacy) {
      const det = solution.determinacy;
      html += `<div class="block"><h4>Estaticidade</h4>
        <div class="kv">
          <div><span class="k">nós</span><span class="v">${det.n}</span></div>
          <div><span class="k">barras</span><span class="v">${det.b}</span></div>
          <div><span class="k">reações</span><span class="v">${det.r}</span></div>
          <div><span class="k math">grau b+r−2n</span><span class="v">${det.degree}</span></div>
          <div><span class="k">classificação</span><span class="v">${esc(det.label)}</span></div>
        </div>
        <p class="note" style="margin:0 11px 11px">${esc(det.detail)}</p>
      </div>`;
    }
    body.innerHTML = html;
  }

  function renderDeterminacy(det) {
    const degreeLabel = det.degree === 0 ? 'isostática' : det.degree > 0 ? 'hiperestática' : 'hipostática';
    return `<div class="block">
      <h4>Estaticidade <span class="chip neutral">${esc(degreeLabel)}</span></h4>
      <div class="kv">
        <div><span class="k">nós</span><span class="v">${det.n}</span></div>
        <div><span class="k">barras</span><span class="v">${det.b}</span></div>
        <div><span class="k">reações</span><span class="v">${det.r}</span></div>
        <div><span class="k math">grau b+r−2n</span><span class="v">${det.degree}</span></div>
      </div>
      <p class="note" style="margin:0 11px 11px">${esc(det.detail)}</p>
    </div>`;
  }

  function renderReactions(reactions, units) {
    if (!reactions.length) return '';
    const rows = reactions
      .map((entry) => {
        const hasX = (entry.components || []).includes('ux');
        const hasY = (entry.components || []).includes('uy');
        return `<tr>
          <td>${esc(entry.node)}</td>
          <td class="muted">${esc(entry.support)}</td>
          <td class="num">${hasX ? num(entry.Rx) : '—'}</td>
          <td class="num">${hasY ? num(entry.Ry) : '—'}</td>
        </tr>`;
      })
      .join('');
    return `<div class="block">
      <h4>Reações de apoio <span class="muted small unit">${esc(units.force)}</span></h4>
      <table class="data">
        <thead><tr><th>nó</th><th>apoio</th>
          <th class="num">Rx</th><th class="num">Ry</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }

  function renderMembers(members, units, summary) {
    const rows = members
      .map((member) => `<tr>
        <td>${esc(member.id)}</td>
        <td class="muted">${esc(member.a)}–${esc(member.b)}</td>
        <td class="num">${num(member.length)}</td>
        <td class="num ${stateClass(member.state)}">${num(member.N)}</td>
        <td class="${stateClass(member.state)}">${esc(member.state)}</td>
      </tr>`)
      .join('');

    const counts = summary
      ? `<span class="muted small">${summary.tension} T · ${summary.compression} C · ${summary.zero} zero</span>`
      : '';

    return `<div class="block">
      <h4>Esforços normais ${counts}</h4>
      <table class="data">
        <thead><tr><th>barra</th><th>nós</th>
          <th class="num">L [${esc(units.length)}]</th>
          <th class="num">N [${esc(units.force)}]</th>
          <th>estado</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }

  function renderChecks(checks, cross, units) {
    if (!checks) return '';
    const ok = (value, tol) => Math.abs(Number(value)) <= tol;
    const tol = 1e-6;
    const mark = (pass) =>
      pass ? '<span class="chip ok">ok</span>' : '<span class="chip bad">fora</span>';

    let crossHtml = '';
    if (cross && cross.available) {
      crossHtml = cross.passed
        ? `<p class="note ok" style="margin:0 11px 11px">Conferido pelo método dos nós
           (algoritmo independente): diferença máxima ${tiny(cross.maxDifference)}
           ${esc(units.force)}.</p>`
        : `<p class="note bad" style="margin:0 11px 11px">Divergência de
           ${tiny(cross.maxDifference)} ${esc(units.force)} em relação ao método dos nós.</p>`;
    } else if (cross) {
      crossHtml = `<p class="note" style="margin:0 11px 11px">Método dos nós não aplicável:
        ${esc(cross.reason)}</p>`;
    }

    return `<div class="block">
      <h4>Verificações
        <span class="chip ${checks.passed ? 'ok' : 'bad'}">
          ${checks.passed ? 'equilíbrio verificado' : 'equilíbrio não fechou'}
        </span>
      </h4>
      <table class="data">
        <thead><tr><th>grandeza</th><th class="num">resíduo</th><th>situação</th></tr></thead>
        <tbody>
          <tr><td>ΣFx (cargas + reações)</td>
              <td class="num">${tiny(checks.sumFx)}</td>
              <td>${mark(ok(checks.sumFx, tol))}</td></tr>
          <tr><td>ΣFy (cargas + reações)</td>
              <td class="num">${tiny(checks.sumFy)}</td>
              <td>${mark(ok(checks.sumFy, tol))}</td></tr>
          <tr><td>ΣM na origem</td>
              <td class="num">${tiny(checks.sumM)}</td>
              <td>${mark(ok(checks.sumM, tol))}</td></tr>
          <tr><td>maior resíduo nodal${checks.worstNode ? ` (nó ${esc(checks.worstNode)})` : ''}</td>
              <td class="num">${tiny(checks.maxNodalResidual)}</td>
              <td>${mark(ok(checks.maxNodalResidual, tol))}</td></tr>
        </tbody>
      </table>
      ${crossHtml}
    </div>`;
  }

  function renderZeroForce(entries) {
    if (!entries || !entries.length) return '';
    const items = entries
      .map(
        (entry) =>
          `<li><b>${esc(entry.member)}</b> — ${esc(entry.reason)}${
            entry.confirmed ? ' <span class="chip ok">confirmado</span>' : ''
          }</li>`
      )
      .join('');
    return `<div class="block">
      <h4>Barras de força zero <span class="muted small">${entries.length}</span></h4>
      <ul class="warnings">${items}</ul>
    </div>`;
  }

  function renderWarnings(warnings) {
    if (!warnings || !warnings.length) return '';
    const items = warnings.map((text) => `<li>${esc(text)}</li>`).join('');
    return `<div class="block"><h4>Avisos</h4><ul class="warnings">${items}</ul></div>`;
  }

  /* --------------------------------------------------------- tensões normais */
  const stressBody = document.getElementById('stress-body');

  function stressMessage(html, warn) {
    stressBody.innerHTML = `<p class="stress-note${warn ? ' warn' : ''}">${html}</p>`;
  }

  function stressErrors(payload) {
    const items = (payload.errors || []).map((error) => `<li>${esc(error.message)}</li>`);
    stressBody.innerHTML = `<div class="block"><h4>Entrada recusada</h4>
      <ul class="errors">${items.join('')}</ul></div>`;
  }

  function renderStressTable(payload, units) {
    const stress = payload.stress;
    if (!stress) {
      stressMessage('Sem resultado de tensão para mostrar.');
      return;
    }

    const areaUnit = (payload.units && payload.units.area) || 'mm²';
    const stressUnit = (payload.units && payload.units.stress) || 'MPa';

    if (payload.mode === 'area') {
      const rows = (stress.entries || [])
        .map((entry) => {
          const verdict =
            entry.ok === null || entry.ok === undefined
              ? '<span class="chip neutral">sem área atual</span>'
              : entry.ok
              ? '<span class="chip ok">suficiente</span>'
              : '<span class="chip bad">insuficiente</span>';
          const current =
            entry.currentArea === null || entry.currentArea === undefined
              ? '—'
              : num(entry.currentArea);
          return `<tr>
            <td>${esc(entry.id)}</td>
            <td class="muted">${esc(entry.a)}–${esc(entry.b)}</td>
            <td class="num ${stateClass(entry.state)}">${num(entry.N)}</td>
            <td class="num">${num(entry.allowable)}</td>
            <td class="num"><b>${num(entry.requiredArea)}</b></td>
            <td class="num">${current}</td>
            <td>${verdict}</td>
          </tr>`;
        })
        .join('');

      const summary = stress.summary || {};
      const governing = summary.governing
        ? `<span>barra governante <b>${esc(summary.governing.id)}</b> · ${num(
            summary.governing.requiredArea
          )} ${esc(areaUnit)}</span>`
        : '';
      const total = `<span>área requerida total <b>${num(
        summary.totalRequiredArea
      )}</b> ${esc(areaUnit)}</span>`;
      const verdict =
        summary.allSufficient === null || summary.allSufficient === undefined
          ? ''
          : summary.allSufficient
          ? '<span class="chip ok">todas as barras suficientes</span>'
          : '<span class="chip bad">há barras insuficientes</span>';

      stressBody.innerHTML = `
        <table class="data">
          <thead><tr><th>barra</th><th>nós</th>
            <th class="num">N [${esc(units.force)}]</th>
            <th class="num"><span class="sigma">σ</span> adm [${esc(stressUnit)}]</th>
            <th class="num">A req [${esc(areaUnit)}]</th>
            <th class="num">A atual [${esc(areaUnit)}]</th>
            <th>situação</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <div class="stress-summary">${total}${governing}${verdict}</div>`;
      return;
    }

    const rows = (stress.entries || [])
      .map(
        (entry) => `<tr>
          <td>${esc(entry.id)}</td>
          <td class="muted">${esc(entry.a)}–${esc(entry.b)}</td>
          <td class="num ${stateClass(entry.state)}">${num(entry.N)}</td>
          <td class="num">${num(entry.area)}</td>
          <td class="num ${stateClass(entry.state)}"><b>${num(entry.sigma)}</b></td>
          <td class="${stateClass(entry.state)}">${esc(entry.state)}</td>
        </tr>`
      )
      .join('');

    const missing = stress.missing || [];

    // nenhuma barra tem área: em vez de tabela vazia, só a instrução
    if (!rows) {
      stressMessage(
        missing.length
          ? `Nenhuma barra tem área informada, então σ não pode ser calculado.
             Preencha a área de cada barra no inspetor (ou use
             <b>Aplicar esta área a todas</b>) e calcule de novo.`
          : 'Sem barras para calcular tensão.',
        missing.length > 0
      );
      return;
    }

    const summary = stress.summary || {};
    const parts = [];
    parts.push(
      `<span>maior |σ| <b>${num(summary.maxAbsStress)}</b> ${esc(stressUnit)}${
        summary.critical ? ` (${esc(summary.critical.id)})` : ''
      }</span>`
    );
    if (summary.maxTension) {
      parts.push(
        `<span>maior tração <b>${esc(summary.maxTension.id)}</b> · ${num(
          summary.maxTension.sigma
        )} ${esc(stressUnit)}</span>`
      );
    }
    if (summary.maxCompression) {
      parts.push(
        `<span>maior compressão <b>${esc(summary.maxCompression.id)}</b> · ${num(
          summary.maxCompression.sigma
        )} ${esc(stressUnit)}</span>`
      );
    }

    const warn = missing.length
      ? `<p class="stress-note warn">Sem área informada (σ não calculado):
         ${missing.map((id) => `<b>${esc(id)}</b>`).join(', ')}.
         Preencha a área no inspetor de cada barra.</p>`
      : '';

    stressBody.innerHTML = `
      <table class="data">
        <thead><tr><th>barra</th><th>nós</th>
          <th class="num">N [${esc(units.force)}]</th>
          <th class="num">A [${esc(areaUnit)}]</th>
          <th class="num"><span class="sigma">σ</span> [${esc(stressUnit)}]</th>
          <th>estado</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="stress-summary">${parts.join('')}</div>
      ${warn}`;
  }

  function renderStress(payload) {
    if (!payload || payload.status !== 'ok') {
      stressErrors(payload || { errors: [{ message: 'sem resposta do servidor' }] });
      return;
    }
    renderStressTable(payload, payload.units || { force: 'kN', length: 'm' });
  }

  function clearStress() {
    stressBody.innerHTML =
      '<p class="muted small">Informe a área de cada barra no inspetor e clique em ' +
      '<b>Calcular tensões</b>. No modo <b>área requerida</b>, a área deixa de ser ' +
      'entrada e passa a ser resultado.</p>';
  }

  function renderSummary(summary, units) {
    if (!summary) return '';
    return `<div class="block">
      <h4>Resumo</h4>
      <div class="kv">
        <div><span class="k">maior |N|</span><span class="v">${num(summary.maxAbsForce)}</span>
             <span class="muted small unit">${esc(units.force)}</span></div>
        <div><span class="k">maior tração</span><span class="v">${
          summary.maxTension ? `${esc(summary.maxTension.id)} · ${num(summary.maxTension.N)}` : '—'
        }</span></div>
        <div><span class="k">maior compressão</span><span class="v">${
          summary.maxCompression ? `${esc(summary.maxCompression.id)} · ${num(summary.maxCompression.N)}` : '—'
        }</span></div>
        <div><span class="k">maior deslocamento</span><span class="v">${
          num(summary.maxDisplacement, 6)
        }</span> <span class="muted small unit">${esc(units.length)}</span></div>
      </div>
    </div>`;
  }

  function render(solution, figureSvg) {
    if (!solution || solution.status !== 'ok') {
      renderErrors(solution || { errors: [{ message: 'sem resposta do servidor' }] });
      return;
    }

    setChip('ok', 'calculado');
    const units = solution.units || { force: 'kN', length: 'm' };

    const parts = [];
    parts.push(renderDeterminacy(solution.determinacy));
    if (figureSvg) {
      parts.push(`<div class="figure-box">${figureSvg}</div>`);
    }
    parts.push(renderReactions(solution.reactions, units));
    parts.push(renderMembers(solution.members, units, solution.summary));
    parts.push(renderSummary(solution.summary, units));
    parts.push(renderChecks(solution.checks, solution.crossCheck, units));
    parts.push(renderZeroForce(solution.zero_force));
    parts.push(renderWarnings(solution.warnings));

    body.innerHTML = parts.join('');
  }

  function setBusy(text) {
    setChip('neutral', text);
  }

  function setError(message) {
    setChip('bad', 'erro');
    body.innerHTML = `<div class="block"><h4>Falha</h4>
      <ul class="errors"><li>${esc(message)}</li></ul></div>`;
  }

  function clear() {
    setChip('neutral', 'aguardando cálculo');
    body.innerHTML =
      '<p class="muted">Monte ou carregue uma treliça e clique em <b>Calcular</b>.</p>';
  }

  return { render, renderStress, clearStress, setBusy, setError, clear };
})();
