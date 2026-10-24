/* ============================================================================
   app.js — ligação entre a interface, o editor e a API.

   Fluxo: Store (modelo) → POST /api/solve → Results (tabelas)
                        → POST /api/figure → diagrama colorido
                        → POST /api/stress → tensões normais / área requerida
                        → POST /api/report → relatório imprimível
   ========================================================================== */

const App = (() => {
  const presetSelect = document.getElementById('preset-select');
  const unitForce = document.getElementById('unit-force');
  const unitLength = document.getElementById('unit-length');
  const unitArea = document.getElementById('unit-area');
  const unitStress = document.getElementById('unit-stress');
  const paletteSelect = document.getElementById('palette-select');
  const showStressBox = document.getElementById('show-stress');
  const solveButton = document.getElementById('btn-solve');
  const reportButton = document.getElementById('btn-report');
  const exportButton = document.getElementById('btn-export');
  const importInput = document.getElementById('file-import');
  const clearButton = document.getElementById('btn-clear');

  const gridDx = document.getElementById('grid-dx');
  const gridDy = document.getElementById('grid-dy');
  const gridNx = document.getElementById('grid-nx');
  const gridNy = document.getElementById('grid-ny');
  const gridButton = document.getElementById('btn-grid');

  const stressMode = document.getElementById('stress-mode');
  const stressAllowable = document.getElementById('stress-allowable');
  const stressUnit = document.getElementById('stress-unit');
  const stressButton = document.getElementById('btn-stress');

  let lastSolution = null;
  let presets = [];

  const palette = () => paletteSelect.value || 'padrao';
  const showStress = () => Boolean(showStressBox && showStressBox.checked);

  /* ------------------------------------------------------------------ API */
  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`o servidor respondeu ${response.status}`);
    }
    return response;
  }

  async function fetchFigure(model) {
    try {
      const response = await postJson('/api/figure', {
        model,
        width: 880,
        height: 520,
        showValues: true,
        palette: palette(),
        showStress: showStress(),
      });
      return await response.text();
    } catch (error) {
      return null;
    }
  }

  /* ---------------------------------------------------------------- ações */
  async function solve(options = {}) {
    const model = Store.toPayload();
    if (!model.nodes.length) {
      Results.clear();
      Results.clearStress();
      return;
    }

    solveButton.disabled = true;
    Results.setBusy('calculando…');

    try {
      const response = await postJson('/api/solve', model);
      const solution = await response.json();
      lastSolution = solution;

      const figure = await fetchFigure(model);
      Results.render(solution, figure);

      reportButton.disabled = solution.status !== 'ok';
      if (solution.status === 'ok' && solution.stress) {
        Results.renderStress({
          status: 'ok',
          mode: 'stress',
          units: solution.units,
          stress: solution.stress,
        });
      } else {
        // sem resultado de esforços não há tensão a mostrar
        Results.clearStress();
      }
      if (options.scroll !== false) {
        document.getElementById('results-body').scrollTop = 0;
      }
    } catch (error) {
      lastSolution = null;
      reportButton.disabled = true;
      Results.setError(
        `não foi possível falar com o servidor local (${error.message}). ` +
          'Confirme que ele está rodando.'
      );
    } finally {
      solveButton.disabled = false;
    }
  }

  /** POST /api/stress — modo "tensão por área" ou "área requerida". */
  async function runStress() {
    const model = Store.toPayload();
    if (!model.nodes.length) {
      Results.clearStress();
      return;
    }

    const mode = stressMode.value === 'area' ? 'area' : 'stress';
    const payload = { model, mode };

    if (mode === 'area') {
      const allowable = Number(stressAllowable.value);
      if (!Number.isFinite(allowable) || allowable <= 0) {
        Results.renderStress({
          status: 'error',
          errors: [{ message: 'informe uma tensão admissível maior que zero.' }],
        });
        return;
      }
      payload.allowable = allowable;
    }

    stressButton.disabled = true;
    try {
      const response = await postJson('/api/stress', payload);
      const result = await response.json();
      Results.renderStress(result);
      syncStressUnit(result.units && result.units.stress);
    } catch (error) {
      Results.renderStress({
        status: 'error',
        errors: [{ message: `falha ao calcular tensões (${error.message}).` }],
      });
    } finally {
      stressButton.disabled = false;
    }
  }

  async function openReport() {
    const model = Store.toPayload();
    const presetName =
      presetSelect.selectedIndex > 0 ? presetSelect.options[presetSelect.selectedIndex].text : '';
    try {
      const response = await postJson('/api/report', {
        model,
        title: presetName ? `Treliça — ${presetName}` : 'Treliça plana — relatório de cálculo',
        palette: palette(),
        showStress: showStress(),
      });
      const html = await response.text();
      const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const win = window.open(url, '_blank');
      if (!win) {
        Results.setError(
          'o navegador bloqueou a janela do relatório. Permita pop-ups e tente de novo.'
        );
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) {
      Results.setError(`não foi possível gerar o relatório (${error.message}).`);
    }
  }

  function exportJson() {
    const payload = Store.toPayload();
    const text = JSON.stringify(payload, null, 2);
    const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'trelica.json';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }

  async function importJson(file) {
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      Store.setModel(data);
      syncUnitSelects();
      Editor.fit();
      Editor.render();
      await solve();
    } catch (error) {
      Results.setError(`arquivo JSON inválido: ${error.message}`);
    }
  }

  function clearAll() {
    Store.reset();
    lastSolution = null;
    presetSelect.value = '';
    reportButton.disabled = true;
    Editor.fit();
    Editor.render();
    Results.clear();
    Results.clearStress();
  }

  /* -------------------------------------------------------------- unidades */
  function syncStressUnit(unit) {
    stressUnit.textContent = unit || Store.getModel().units.stress || 'MPa';
  }

  function syncUnitSelects() {
    const units = Store.getModel().units;
    unitForce.value = units.force;
    unitLength.value = units.length;
    unitArea.value = units.area || 'mm²';
    unitStress.value = units.stress || 'MPa';
    syncStressUnit(units.stress);
  }

  /* ----------------------------------------------------------------- grade */
  function syncGridInputs() {
    const grid = Editor.getGrid();
    gridDx.value = grid.dx;
    gridDy.value = grid.dy;
    gridNx.value = grid.nx;
    gridNy.value = grid.ny;
  }

  function applyGrid() {
    Editor.setGrid({
      dx: Number(gridDx.value) || 1,
      dy: Number(gridDy.value) || 1,
      nx: Number(gridNx.value) || 8,
      ny: Number(gridNy.value) || 5,
    });
    syncGridInputs();
  }

  /* --------------------------------------------------------------- presets */
  async function loadPresets() {
    try {
      const response = await fetch('/api/presets');
      const data = await response.json();
      presets = data.presets || [];
      for (const preset of presets) {
        const option = document.createElement('option');
        option.value = preset.slug;
        option.textContent = preset.name;
        if (preset.expectError) option.textContent += ' (caso de erro)';
        presetSelect.appendChild(option);
      }
    } catch (error) {
      /* o seletor simplesmente fica vazio; o editor continua utilizável */
    }
  }

  async function applyPreset(slug) {
    if (!slug) return;
    try {
      const response = await fetch(`/api/presets/${encodeURIComponent(slug)}`);
      if (!response.ok) throw new Error('caso não encontrado');
      const preset = await response.json();
      Store.setModel(preset.input);
      syncUnitSelects();
      Editor.fit();
      Editor.render();
      await solve();
    } catch (error) {
      Results.setError(`não foi possível carregar o caso: ${error.message}`);
    }
  }

  /* ------------------------------------------------------------------ init */
  function init() {
    Editor.init();
    Results.clear();
    Results.clearStress();
    syncUnitSelects();
    syncGridInputs();

    solveButton.addEventListener('click', () => solve());
    reportButton.addEventListener('click', openReport);
    exportButton.addEventListener('click', exportJson);
    clearButton.addEventListener('click', clearAll);

    importInput.addEventListener('change', () => {
      const file = importInput.files && importInput.files[0];
      if (file) importJson(file);
      importInput.value = '';
    });

    presetSelect.addEventListener('change', () => applyPreset(presetSelect.value));

    const onUnitsChanged = () => {
      Store.setUnits(unitForce.value, unitLength.value, unitArea.value, unitStress.value);
      syncStressUnit(unitStress.value);
      if (lastSolution) solve({ scroll: false });
    };
    unitForce.addEventListener('change', onUnitsChanged);
    unitLength.addEventListener('change', onUnitsChanged);
    unitArea.addEventListener('change', onUnitsChanged);
    unitStress.addEventListener('change', onUnitsChanged);

    const refreshFigure = () => {
      if (lastSolution) solve({ scroll: false });
    };
    paletteSelect.addEventListener('change', refreshFigure);
    if (showStressBox) showStressBox.addEventListener('change', refreshFigure);

    gridButton.addEventListener('click', applyGrid);
    for (const input of [gridDx, gridDy, gridNx, gridNy]) {
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          applyGrid();
        }
      });
    }

    stressButton.addEventListener('click', runStress);
    stressAllowable.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        runStress();
      }
    });
    stressMode.addEventListener('change', () => {
      const areaMode = stressMode.value === 'area';
      stressAllowable.disabled = !areaMode;
      stressButton.textContent = areaMode ? 'Calcular áreas' : 'Calcular tensões';
    });

    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        solve();
      }
    });

    loadPresets();
  }

  return { init, solve, applyPreset, runStress };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
