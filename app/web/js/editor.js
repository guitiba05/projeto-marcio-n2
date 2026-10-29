/* ============================================================================
   editor.js — quadro de edição em SVG.

   Fluxo de entrada inspirado no módulo Trusses do MdSolids: a grade é definida
   por espaçamento e número de intervalos, e as barras são criadas **arrastando**
   de um ponto de grade a outro. Apoios e cargas são editados pelo inspetor.

   Nenhuma conta de engenharia acontece aqui: geometria, apoios, cargas e áreas.
   ========================================================================== */

const Editor = (() => {
  const svg = document.getElementById('canvas');
  const emptyHint = document.getElementById('canvas-empty');
  const inspector = document.getElementById('inspector');
  const toolHint = document.getElementById('tool-hint');

  const state = {
    tool: 'select',
    snap: true,
    showGrid: true,
    showLabels: true,
    hoverNode: null,
    // Cursor de teclado (grade navegável sem mouse). `null` até o primeiro uso.
    cursor: null,
  };

  // Grade com extensão definida: pontos em (i·dx, j·dy) para i em 0..nx, j em 0..ny
  const grid = { dx: 1, dy: 1, nx: 8, ny: 5 };

  const view = { scale: 42, panX: 70, panY: 320 };
  let drag = null;
  let rubber = null;        // { fromId, fromX, fromY, x, y } linha fantasma
  let lastNodeClick = null; // { id, time } para detectar duplo clique em nó
  let inspectorKey = null;
  let userAdjusted = false;
  let keyboardStart = null; // nó de origem ao criar barra pelo teclado

  const NODE_R = 5;
  const HIT_R = 14;

  /* ------------------------------------------------------------ conversões */
  const toScreenX = (x) => view.panX + x * view.scale;
  const toScreenY = (y) => view.panY - y * view.scale;
  const toWorldX = (sx) => (sx - view.panX) / view.scale;
  const toWorldY = (sy) => (view.panY - sy) / view.scale;

  /** Escape HTML/SVG: ids e unidades vêm do JSON importado e não são confiáveis. */
  const esc = (value) =>
    String(value === null || value === undefined ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  function gridExtent() {
    return { maxX: grid.dx * grid.nx, maxY: grid.dy * grid.ny };
  }

  function snapValue(value, step) {
    if (!state.snap) return Math.round(value * 1000) / 1000;
    const s = step > 0 ? step : 1;
    return Math.round(value / s) * s;
  }

  function fmt(value, decimals = 2) {
    const rounded = Math.round(Number(value) * 10 ** decimals) / 10 ** decimals;
    const text = (rounded === 0 ? 0 : rounded).toFixed(decimals);
    return text.replace('-', '\u2212');
  }

  function setGrid(next) {
    grid.dx = Math.max(0.001, Number(next.dx) || 1);
    grid.dy = Math.max(0.001, Number(next.dy) || 1);
    grid.nx = Math.max(1, Math.round(Number(next.nx) || 8));
    grid.ny = Math.max(1, Math.round(Number(next.ny) || 5));
    userAdjusted = false;
    fit();
    render();
  }

  function getGrid() {
    return { ...grid };
  }

  /* ------------------------------------------------------------------ fit */
  function bounds() {
    const model = Store.getModel();
    const ext = gridExtent();
    let minX = 0;
    let maxX = ext.maxX;
    let minY = 0;
    let maxY = ext.maxY;
    for (const node of model.nodes) {
      minX = Math.min(minX, node.x);
      maxX = Math.max(maxX, node.x);
      minY = Math.min(minY, node.y);
      maxY = Math.max(maxY, node.y);
    }
    return { minX, maxX, minY, maxY };
  }

  function fit() {
    const rect = svg.getBoundingClientRect();
    const width = Math.max(rect.width || 640, 240);
    const height = Math.max(rect.height || 380, 220);
    const pad = 58;

    const { minX, maxX, minY, maxY } = bounds();
    const spanX = maxX - minX;
    const spanY = maxY - minY;
    const usableW = Math.max(width - 2 * pad, 40);
    const usableH = Math.max(height - 2 * pad, 40);

    let scale;
    if (spanX < 1e-9 && spanY < 1e-9) scale = 42;
    else if (spanX < 1e-9) scale = usableH / spanY;
    else if (spanY < 1e-9) scale = usableW / spanX;
    else scale = Math.min(usableW / spanX, usableH / spanY);
    scale = Math.max(3, Math.min(scale, 220));

    view.scale = scale;
    view.panX = pad + (usableW - spanX * scale) / 2 - minX * scale;
    view.panY = height - pad - (usableH - spanY * scale) / 2 + minY * scale;
  }

  /* ------------------------------------------------------------- desenho */
  function gridSvg(width, height) {
    const parts = [];
    const ext = gridExtent();
    const xs = [];
    for (let i = 0; i <= grid.nx; i += 1) xs.push(i * grid.dx);
    const ys = [];
    for (let j = 0; j <= grid.ny; j += 1) ys.push(j * grid.dy);

    for (const x of xs) {
      const sx = toScreenX(x);
      parts.push(
        `<line class="grid-line${x === 0 ? ' major' : ''}" x1="${sx.toFixed(1)}" y1="0" ` +
          `x2="${sx.toFixed(1)}" y2="${height}"/>`
      );
    }
    for (const y of ys) {
      const sy = toScreenY(y);
      parts.push(
        `<line class="grid-line${y === 0 ? ' major' : ''}" x1="0" y1="${sy.toFixed(1)}" ` +
          `x2="${width}" y2="${sy.toFixed(1)}"/>`
      );
    }

    // pontos de grade: onde o usuário pode soltar
    const dotR = view.scale > 26 ? 1.7 : 1.2;
    for (const x of xs) {
      for (const y of ys) {
        parts.push(
          `<circle cx="${toScreenX(x).toFixed(1)}" cy="${toScreenY(y).toFixed(1)}" ` +
            `r="${dotR}" fill="#c3ccda"/>`
        );
      }
    }
    return parts.join('');
  }

  function arrowSvg(x1, y1, x2, y2, label, labelX, labelY) {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const size = 8;
    const a1 = angle + (150 * Math.PI) / 180;
    const a2 = angle - (150 * Math.PI) / 180;
    const head = [
      `${x2.toFixed(1)},${y2.toFixed(1)}`,
      `${(x2 + size * Math.cos(a1)).toFixed(1)},${(y2 + size * Math.sin(a1)).toFixed(1)}`,
      `${(x2 + size * Math.cos(a2)).toFixed(1)},${(y2 + size * Math.sin(a2)).toFixed(1)}`,
    ].join(' ');
    return (
      `<line class="load-arrow" x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" ` +
      `x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"/>` +
      `<polygon class="load-head" points="${head}"/>` +
      `<text class="load-label" x="${labelX.toFixed(1)}" y="${labelY.toFixed(1)}" ` +
      `text-anchor="middle" dominant-baseline="middle">${label}</text>`
    );
  }

  function supportSvg(support, sx, sy) {
    if (!support || support === 'none') return '';
    const base = sy + 12;
    let out =
      `<polygon class="support-sym" points="${sx.toFixed(1)},${sy.toFixed(1)} ` +
      `${(sx - 8).toFixed(1)},${base.toFixed(1)} ${(sx + 8).toFixed(1)},${base.toFixed(1)}"/>`;
    if (support === 'roller') {
      out +=
        `<circle class="support-sym" cx="${(sx - 4.5).toFixed(1)}" cy="${(base + 3).toFixed(1)}" r="2.3"/>` +
        `<circle class="support-sym" cx="${(sx + 4.5).toFixed(1)}" cy="${(base + 3).toFixed(1)}" r="2.3"/>` +
        `<line class="support-sym" x1="${(sx - 12).toFixed(1)}" y1="${(base + 6).toFixed(1)}" ` +
        `x2="${(sx + 12).toFixed(1)}" y2="${(base + 6).toFixed(1)}"/>`;
    } else if (support === 'roller_x') {
      out +=
        `<circle class="support-sym" cx="${(sx - 12).toFixed(1)}" cy="${(sy - 4.5).toFixed(1)}" r="2.3"/>` +
        `<circle class="support-sym" cx="${(sx - 12).toFixed(1)}" cy="${(sy + 4.5).toFixed(1)}" r="2.3"/>` +
        `<line class="support-sym" x1="${(sx - 15).toFixed(1)}" y1="${(sy - 12).toFixed(1)}" ` +
        `x2="${(sx - 15).toFixed(1)}" y2="${(sy + 12).toFixed(1)}"/>`;
    } else {
      out +=
        `<line class="support-sym" x1="${(sx - 12).toFixed(1)}" y1="${(base + 4).toFixed(1)}" ` +
        `x2="${(sx + 12).toFixed(1)}" y2="${(base + 4).toFixed(1)}"/>`;
    }
    return out;
  }

  function render() {
    const model = Store.getModel();
    const selection = Store.getSelection();
    const rect = svg.getBoundingClientRect();
    const width = Math.max(rect.width || 640, 120);
    const height = Math.max(rect.height || 380, 120);

    svg.setAttribute('viewBox', `0 0 ${width.toFixed(0)} ${height.toFixed(0)}`);

    const parts = [];
    if (state.showGrid) parts.push(gridSvg(width, height));

    // barras
    for (const member of model.members) {
      const a = Store.nodeById(member.a);
      const b = Store.nodeById(member.b);
      if (!a || !b) continue;
      const x1 = toScreenX(a.x);
      const y1 = toScreenY(a.y);
      const x2 = toScreenX(b.x);
      const y2 = toScreenY(b.y);
      const selected =
        selection && selection.type === 'member' && selection.id === member.id;
      parts.push(
        `<line class="member-line${selected ? ' selected' : ''}" x1="${x1.toFixed(1)}" ` +
          `y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"/>`
      );
      parts.push(
        `<line class="member-line hit" data-member="${esc(member.id)}" x1="${x1.toFixed(1)}" ` +
          `y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"/>`
      );
    }

    // linha fantasma do arraste
    if (rubber) {
      parts.push(
        `<line class="member-line pending" x1="${rubber.fromX.toFixed(1)}" ` +
          `y1="${rubber.fromY.toFixed(1)}" x2="${rubber.x.toFixed(1)}" y2="${rubber.y.toFixed(1)}"/>`
      );
    }

    // cargas
    for (const load of model.loads) {
      const node = Store.nodeById(load.node);
      if (!node) continue;
      const fx = Number(load.Fx) || 0;
      const fy = Number(load.Fy) || 0;
      const magnitude = Math.hypot(fx, fy);
      if (magnitude <= 0) continue;
      const sx = toScreenX(node.x);
      const sy = toScreenY(node.y);
      const ux = fx / magnitude;
      const uy = -fy / magnitude;
      const len = 40;
      parts.push(
        arrowSvg(
          sx - ux * len,
          sy - uy * len,
          sx - ux * 10,
          sy - uy * 10,
          fmt(magnitude, 1),
          sx - ux * (len + 12),
          sy - uy * (len + 12)
        )
      );
    }

    // apoios
    for (const node of model.nodes) {
      parts.push(supportSvg(node.support, toScreenX(node.x), toScreenY(node.y)));
    }

    // nós
    for (const node of model.nodes) {
      const sx = toScreenX(node.x);
      const sy = toScreenY(node.y);
      const selected = selection && selection.type === 'node' && selection.id === node.id;
      const hover = state.hoverNode === node.id;
      parts.push(
        `<circle class="node-dot${selected ? ' selected' : ''}${hover && !selected ? ' hover' : ''}" ` +
          `cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="${NODE_R}"/>`
      );
      parts.push(
        `<circle class="node-hit" data-node="${esc(node.id)}" cx="${sx.toFixed(1)}" ` +
          `cy="${sy.toFixed(1)}" r="${HIT_R}"/>`
      );
      if (state.showLabels) {
        parts.push(
          `<text class="node-label" x="${(sx + 9).toFixed(1)}" y="${(sy - 9).toFixed(1)}">` +
            `${esc(node.id)}</text>`
        );
      }
    }

    // cursor de teclado: mostra onde Enter vai criar o nó/barra
    if (state.cursor && document.activeElement === svg) {
      const cx = toScreenX(state.cursor.x);
      const cy = toScreenY(state.cursor.y);
      parts.push(
        `<circle class="cursor-mark" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="8"/>`
      );
      parts.push(
        `<line class="cursor-cross" x1="${(cx - 13).toFixed(1)}" y1="${cy.toFixed(1)}" ` +
          `x2="${(cx + 13).toFixed(1)}" y2="${cy.toFixed(1)}"/>`
      );
      parts.push(
        `<line class="cursor-cross" x1="${cx.toFixed(1)}" y1="${(cy - 13).toFixed(1)}" ` +
          `x2="${cx.toFixed(1)}" y2="${(cy + 13).toFixed(1)}"/>`
      );
    }

    svg.innerHTML = parts.join('');
    emptyHint.classList.toggle('hidden', model.nodes.length > 0);
    renderInspector(false);
  }

  /* ------------------------------------------------------------ inspetor */
  function renderInspector(force) {
    const selection = Store.getSelection();
    const key = selection ? `${selection.type}:${selection.id}` : 'none';
    if (!force && key === inspectorKey) {
      syncInspectorValues();
      return;
    }
    inspectorKey = key;

    if (!selection) {
      inspector.innerHTML =
        '<p class="muted small">Nada selecionado. Clique em um nó ou barra para editar. ' +
        'Duplo clique em um nó alterna o tipo de apoio.</p>';
      return;
    }

    const units = Store.getModel().units;

    if (selection.type === 'node') {
      const node = Store.nodeById(selection.id);
      if (!node) {
        inspector.innerHTML = '<p class="muted small">Nó removido.</p>';
        return;
      }
      const load = Store.loadAt(node.id);
      inspector.innerHTML = `
        <div class="inspector-head">
          <h3>Nó ${esc(node.id)}</h3>
          <span class="chip neutral">${node.support === 'none' ? 'sem apoio' : esc(node.support)}</span>
        </div>
        <div class="inspector-grid">
          <label>x <span class="unit">[${esc(units.length)}]</span>
            <input type="number" step="any" data-field="x" value="${node.x}">
          </label>
          <label>y <span class="unit">[${esc(units.length)}]</span>
            <input type="number" step="any" data-field="y" value="${node.y}">
          </label>
          <label>apoio
            <select data-field="support">
              <option value="none"${node.support === 'none' ? ' selected' : ''}>livre</option>
              <option value="pin"${node.support === 'pin' ? ' selected' : ''}>articulação (2 reações)</option>
              <option value="roller"${node.support === 'roller' ? ' selected' : ''}>roleto vertical</option>
              <option value="roller_x"${node.support === 'roller_x' ? ' selected' : ''}>roleto horizontal</option>
            </select>
          </label>
          <label>Fx <span class="unit">[${esc(units.force)}]</span>
            <input type="number" step="any" data-field="Fx" value="${load.Fx}">
          </label>
          <label>Fy <span class="unit">[${esc(units.force)}]</span>
            <input type="number" step="any" data-field="Fy" value="${load.Fy}">
          </label>
        </div>
        <div class="inspector-actions">
          <button class="btn danger" type="button" data-action="delete-node">Remover nó</button>
        </div>`;
      return;
    }

    const member = Store.memberById(selection.id);
    if (!member) {
      inspector.innerHTML = '<p class="muted small">Barra removida.</p>';
      return;
    }
    const areaValue = member.area === null || member.area === undefined ? '' : member.area;
    inspector.innerHTML = `
      <div class="inspector-head">
        <h3>Barra ${esc(member.id)}</h3>
        <span class="chip neutral">${esc(member.a)} — ${esc(member.b)}</span>
      </div>
      <div class="inspector-grid">
        <label>área A <span class="unit">[${esc(units.area)}]</span>
          <input type="number" step="any" min="0" placeholder="opcional"
                 data-field="area" value="${areaValue}">
        </label>
        <label>EA <span class="unit">[${esc(units.force)}]</span>
          <input type="number" step="any" min="0.000001" data-field="EA" value="${member.EA}">
        </label>
      </div>
      <div class="inspector-actions">
        <button class="btn danger" type="button" data-action="delete-member">Remover barra</button>
        <button class="btn" type="button" data-action="area-all">Aplicar esta área a todas</button>
      </div>
      <p class="muted small" style="margin-top:9px">A área entra no cálculo da tensão
      normal (σ = N/A) e no modo "área requerida". Em treliça isostática os esforços não
      dependem de EA.</p>`;
  }

  function syncInspectorValues() {
    const selection = Store.getSelection();
    if (!selection) return;
    if (selection.type === 'node') {
      const node = Store.nodeById(selection.id);
      if (!node) return;
      const xInput = inspector.querySelector('[data-field="x"]');
      const yInput = inspector.querySelector('[data-field="y"]');
      if (xInput && document.activeElement !== xInput) xInput.value = node.x;
      if (yInput && document.activeElement !== yInput) yInput.value = node.y;
    }
  }

  /* ------------------------------------------------------------- eventos */
  function pointerWorld(event) {
    const rect = svg.getBoundingClientRect();
    return {
      x: toWorldX(event.clientX - rect.left),
      y: toWorldY(event.clientY - rect.top),
      screenX: event.clientX - rect.left,
      screenY: event.clientY - rect.top,
    };
  }

  function nearestNode(clientX, clientY, maxPx = 22) {
    const rect = svg.getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    let best = null;
    let bestDist = maxPx;
    for (const node of Store.getModel().nodes) {
      const d = Math.hypot(toScreenX(node.x) - px, toScreenY(node.y) - py);
      if (d < bestDist) {
        bestDist = d;
        best = node;
      }
    }
    return best;
  }

  function setTool(tool) {
    state.tool = tool;
    rubber = null;
    keyboardStart = null;
    for (const button of document.querySelectorAll('[data-tool]')) {
      button.setAttribute('aria-pressed', String(button.dataset.tool === tool));
    }
    svg.classList.toggle('mode-select', tool === 'select');
    svg.classList.toggle('mode-member', tool === 'member');
    const hints = {
      select: 'Arraste um nó para mover. Duplo clique (ou Enter com o quadro em foco) alterna o apoio. Setas movem o cursor; role para zoom.',
      node: 'Clique em um ponto da grade para criar um nó — ou foque o quadro e use setas + Enter.',
      member: 'Arraste de um nó (ou de um ponto da grade) até outro — ou foque o quadro, use setas + Enter na origem e no destino.',
    };
    toolHint.textContent = hints[tool] || '';
  }

  function onPointerDown(event) {
    if (event.button !== 0 && event.button !== 1) return;
    const target = event.target;
    const nodeId = target.dataset ? target.dataset.node : null;
    const memberId = target.dataset ? target.dataset.member : null;
    const world = pointerWorld(event);

    // pan: botão do meio ou Shift
    if (event.button === 1 || event.shiftKey) {
      drag = { mode: 'pan', startX: event.clientX, startY: event.clientY,
               panX: view.panX, panY: view.panY };
      userAdjusted = true;
      svg.setPointerCapture(event.pointerId);
      return;
    }

    if (state.tool === 'node' && !nodeId) {
      const x = snapValue(world.x, grid.dx);
      const y = snapValue(world.y, grid.dy);
      const existing = Store.nodeAt(x, y);
      if (existing) {
        Store.setSelection({ type: 'node', id: existing.id });
      } else {
        Store.addNode(x, y);
      }
      return;
    }

    if (state.tool === 'member') {
      let node = nodeId ? Store.nodeById(nodeId) : null;
      if (!node) {
        // arrastar a partir de um ponto de grade vazio: cria o nó de origem
        const x = snapValue(world.x, grid.dx);
        const y = snapValue(world.y, grid.dy);
        node = Store.nodeAt(x, y) || Store.addNode(x, y);
      }
      if (node) {
        rubber = {
          fromId: node.id,
          fromX: toScreenX(node.x),
          fromY: toScreenY(node.y),
          x: world.screenX,
          y: world.screenY,
        };
        svg.setPointerCapture(event.pointerId);
        render();
      }
      return;
    }

    if (nodeId) {
      // Duplo clique em nó alterna o apoio. Não dá para depender do evento
      // `dblclick`: o primeiro clique redesenha o SVG e o nó alvo deixa de
      // existir, então o navegador nunca emite o segundo clique no mesmo alvo.
      const now = Date.now();
      const repeated =
        lastNodeClick && lastNodeClick.id === nodeId && now - lastNodeClick.time < 400;
      if (repeated) {
        lastNodeClick = null;
        Store.cycleSupport(nodeId);
        drag = null;
        render();
        return;
      }
      lastNodeClick = { id: nodeId, time: now };
      Store.setSelection({ type: 'node', id: nodeId });
      drag = { mode: 'node', id: nodeId, pointerId: event.pointerId };
      svg.setPointerCapture(event.pointerId);
      render();
      return;
    }

    if (memberId) {
      Store.setSelection({ type: 'member', id: memberId });
      render();
      return;
    }

    Store.setSelection(null);
    drag = { mode: 'pan', startX: event.clientX, startY: event.clientY,
             panX: view.panX, panY: view.panY };
    userAdjusted = true;
    svg.setPointerCapture(event.pointerId);
    render();
  }

  function onPointerMove(event) {
    const world = pointerWorld(event);

    if (drag && drag.mode === 'pan') {
      view.panX = drag.panX + (event.clientX - drag.startX);
      view.panY = drag.panY + (event.clientY - drag.startY);
      render();
      return;
    }

    if (drag && drag.mode === 'node') {
      const node = Store.nodeById(drag.id);
      if (!node) return;
      const nextX = snapValue(world.x, grid.dx);
      const nextY = snapValue(world.y, grid.dy);
      node.x = nextX;
      node.y = nextY;
      render();
      return;
    }

    if (rubber) {
      rubber.x = world.screenX;
      rubber.y = world.screenY;
      const over = nearestNode(event.clientX, event.clientY);
      state.hoverNode = over ? over.id : null;
      render();
      return;
    }

    const target = event.target;
    const hovered = target && target.dataset ? target.dataset.node : null;
    if (hovered !== state.hoverNode) {
      state.hoverNode = hovered || null;
      render();
    }
  }

  function onPointerUp(event) {
    if (rubber) {
      const from = rubber.fromId;
      rubber = null;

      let target = nearestNode(event.clientX, event.clientY);
      if (!target) {
        // soltou em ponto de grade vazio: cria o nó e conecta
        const world = pointerWorld(event);
        const x = snapValue(world.x, grid.dx);
        const y = snapValue(world.y, grid.dy);
        const existing = Store.nodeAt(x, y);
        target = existing || Store.addNode(x, y);
      }
      if (target && target.id !== from) {
        Store.addMember(from, target.id);
      }
      drag = null;
      render();
      return;
    }
    drag = null;
  }

  function onDoubleClick(event) {
    const target = event.target;
    const nodeId = target && target.dataset ? target.dataset.node : null;
    if (nodeId) {
      Store.cycleSupport(nodeId);
      event.preventDefault();
    }
  }

  function onWheel(event) {
    event.preventDefault();
    const rect = svg.getBoundingClientRect();
    const sx = event.clientX - rect.left;
    const sy = event.clientY - rect.top;
    const worldX = toWorldX(sx);
    const worldY = toWorldY(sy);
    const factor = event.deltaY < 0 ? 1.12 : 1 / 1.12;
    view.scale = Math.max(3, Math.min(view.scale * factor, 400));
    view.panX = sx - worldX * view.scale;
    view.panY = sy + worldY * view.scale;
    userAdjusted = true;
    render();
  }

  function onInspectorInput(event) {
    const selection = Store.getSelection();
    if (!selection) return;
    const field = event.target.dataset ? event.target.dataset.field : null;
    if (!field) return;
    const value = event.target.value;

    if (selection.type === 'node') {
      const node = Store.nodeById(selection.id);
      if (!node) return;
      if (field === 'support') {
        Store.updateNode(node.id, { support: value });
      } else if (field === 'Fx' || field === 'Fy') {
        const load = Store.loadAt(node.id);
        const next = { ...load, [field]: Number(value) || 0 };
        Store.setLoad(node.id, next.Fx, next.Fy);
      } else {
        const number = Number(value);
        if (Number.isFinite(number)) Store.updateNode(node.id, { [field]: number });
      }
      return;
    }

    if (selection.type === 'member') {
      const member = Store.memberById(selection.id);
      if (!member) return;
      if (field === 'EA') {
        const number = Number(value);
        if (Number.isFinite(number) && number > 0) Store.updateMember(member.id, { EA: number });
      } else if (field === 'area') {
        const trimmed = String(value).trim();
        if (trimmed === '') {
          Store.updateMember(member.id, { area: null });
        } else {
          const number = Number(trimmed);
          if (Number.isFinite(number) && number > 0) {
            Store.updateMember(member.id, { area: number });
          }
        }
      }
    }
  }

  function onInspectorClick(event) {
    const action = event.target.dataset ? event.target.dataset.action : null;
    if (!action) return;
    const selection = Store.getSelection();
    if (!selection) return;
    if (action === 'delete-node') Store.removeNode(selection.id);
    if (action === 'delete-member') Store.removeMember(selection.id);
    if (action === 'area-all') {
      const member = Store.memberById(selection.id);
      if (member && member.area > 0) Store.setAllAreas(member.area);
    }
    renderInspector(true);
  }

  /* --------------------------------------------------- teclado no quadro */
  function ensureCursor() {
    if (state.cursor) return state.cursor;
    const first = Store.getModel().nodes[0];
    state.cursor = first ? { x: first.x, y: first.y } : { x: 0, y: 0 };
    return state.cursor;
  }

  function moveCursor(dx, dy) {
    const cursor = ensureCursor();
    cursor.x = Math.round((cursor.x + dx * grid.dx) * 1e6) / 1e6;
    cursor.y = Math.round((cursor.y + dy * grid.dy) * 1e6) / 1e6;
    render();
  }

  function nodeAtCursor(create) {
    const cursor = ensureCursor();
    const existing = Store.nodeAt(cursor.x, cursor.y);
    if (existing) return existing;
    return create ? Store.addNode(cursor.x, cursor.y) : null;
  }

  /** Setas movem o cursor de grade; Enter cria nó/barra ou alterna o apoio. */
  function onCanvasKeyDown(event) {
    const moves = {
      ArrowLeft: [-1, 0],
      ArrowRight: [1, 0],
      ArrowUp: [0, 1],
      ArrowDown: [0, -1],
    };
    const move = moves[event.key];
    if (move) {
      event.preventDefault();
      moveCursor(move[0], move[1]);
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      if (state.tool === 'node') {
        nodeAtCursor(true);
      } else if (state.tool === 'member') {
        const node = nodeAtCursor(true);
        if (!keyboardStart) {
          keyboardStart = node.id;
          toolHint.textContent = `Origem ${node.id}. Setas movem o cursor; Enter no nó de destino cria a barra.`;
        } else if (keyboardStart !== node.id) {
          Store.addMember(keyboardStart, node.id);
          keyboardStart = null;
          toolHint.textContent = 'Barra criada. Setas movem o cursor; Enter define a próxima origem.';
        }
      } else {
        const node = nodeAtCursor(false);
        if (node) Store.cycleSupport(node.id);
      }
      return;
    }

    if (event.key === 'Escape' && keyboardStart) {
      event.preventDefault();
      keyboardStart = null;
      render();
    }
  }

  function onKeyDown(event) {
    const tag = (event.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'select' || tag === 'textarea') return;

    if (event.key === 'v' || event.key === 'V') setTool('select');
    else if (event.key === 'n' || event.key === 'N') setTool('node');
    else if (event.key === 'b' || event.key === 'B') setTool('member');
    else if (event.key === 'Escape') {
      rubber = null;
      Store.setSelection(null);
      render();
    } else if (event.key === 'Delete' || event.key === 'Backspace') {
      const selection = Store.getSelection();
      if (!selection) return;
      event.preventDefault();
      if (selection.type === 'node') Store.removeNode(selection.id);
      else Store.removeMember(selection.id);
    } else if (event.key === 'f' || event.key === 'F') {
      userAdjusted = false;
      fit();
      render();
    }
  }

  /* -------------------------------------------------------------- setup */
  function init() {
    svg.addEventListener('pointerdown', onPointerDown);
    svg.addEventListener('pointermove', onPointerMove);
    svg.addEventListener('pointerup', onPointerUp);
    svg.addEventListener('pointercancel', onPointerUp);
    svg.addEventListener('dblclick', onDoubleClick);
    svg.addEventListener('wheel', onWheel, { passive: false });
    svg.addEventListener('contextmenu', (event) => event.preventDefault());
    svg.addEventListener('keydown', onCanvasKeyDown);
    svg.addEventListener('focus', () => render());
    svg.addEventListener('blur', () => render());

    inspector.addEventListener('input', onInspectorInput);
    inspector.addEventListener('change', onInspectorInput);
    inspector.addEventListener('click', onInspectorClick);

    document.addEventListener('keydown', onKeyDown);

    for (const button of document.querySelectorAll('[data-tool]')) {
      button.addEventListener('click', () => setTool(button.dataset.tool));
    }

    const snapBox = document.getElementById('snap');
    const gridBox = document.getElementById('show-grid');
    const labelBox = document.getElementById('show-labels');
    snapBox.addEventListener('change', () => { state.snap = snapBox.checked; });
    gridBox.addEventListener('change', () => { state.showGrid = gridBox.checked; render(); });
    labelBox.addEventListener('change', () => { state.showLabels = labelBox.checked; render(); });
    document.getElementById('btn-fit').addEventListener('click', () => {
      userAdjusted = false;
      fit();
      render();
    });

    window.addEventListener('resize', () => {
      if (!userAdjusted) fit();
      render();
    });

    Store.subscribe(() => render());
    setTool('select');
    fit();
    render();
  }

  return { init, fit, render, setTool, setGrid, getGrid };
})();
