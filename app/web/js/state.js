/* ============================================================================
   state.js — modelo da treliça no cliente.

   Este arquivo NÃO faz cálculo de engenharia: ele só mantém a geometria, os
   apoios e as cargas, e serializa para o contrato JSON consumido pela API.
   ========================================================================== */

const Store = (() => {
  const listeners = [];

  const emptyModel = () => ({
    units: { force: 'kN', length: 'm', area: 'mm²', stress: 'MPa' },
    nodes: [],
    members: [],
    loads: [],
  });

  let model = emptyModel();
  let selection = null; // { type: 'node' | 'member', id: string }

  function emit() {
    for (const fn of listeners) fn();
  }

  function subscribe(fn) {
    listeners.push(fn);
    return () => {
      const index = listeners.indexOf(fn);
      if (index >= 0) listeners.splice(index, 1);
    };
  }

  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function nextNodeId() {
    const used = new Set(model.nodes.map((n) => n.id));
    for (const letter of LETTERS) {
      if (!used.has(letter)) return letter;
    }
    for (let suffix = 1; suffix < 100; suffix += 1) {
      for (const letter of LETTERS) {
        const candidate = `${letter}${suffix}`;
        if (!used.has(candidate)) return candidate;
      }
    }
    return `N${model.nodes.length + 1}`;
  }

  function nodeById(id) {
    return model.nodes.find((n) => n.id === id) || null;
  }

  function memberById(id) {
    return model.members.find((m) => m.id === id) || null;
  }

  function findMember(a, b) {
    return (
      model.members.find(
        (m) => (m.a === a && m.b === b) || (m.a === b && m.b === a)
      ) || null
    );
  }

  function addNode(x, y) {
    const node = { id: nextNodeId(), x: round(x), y: round(y), support: 'none' };
    model.nodes.push(node);
    selection = { type: 'node', id: node.id };
    emit();
    return node;
  }

  /** Nó existente na posição informada (tolerância de 1e-6 na unidade do modelo). */
  function nodeAt(x, y) {
    const tol = 1e-6;
    return (
      model.nodes.find(
        (n) => Math.abs(n.x - Number(x)) <= tol && Math.abs(n.y - Number(y)) <= tol
      ) || null
    );
  }

  /** Copia uma área para todas as barras (área em branco = remover). */
  function setAllAreas(area) {
    const value = area === null || area === undefined || area === '' ? null : Number(area);
    if (value !== null && (!Number.isFinite(value) || value <= 0)) return;
    for (const member of model.members) member.area = value;
    emit();
  }

  function round(value) {
    return Math.round(value * 1000) / 1000;
  }

  function removeNode(id) {
    model.nodes = model.nodes.filter((n) => n.id !== id);
    model.members = model.members.filter((m) => m.a !== id && m.b !== id);
    model.loads = model.loads.filter((l) => l.node !== id);
    if (selection && selection.id === id) selection = null;
    emit();
  }

  function addMember(a, b) {
    if (a === b) return null;
    if (!nodeById(a) || !nodeById(b)) return null;
    if (findMember(a, b)) return null;
    const member = { id: `${a}${b}`, a, b, EA: 1, area: null };
    model.members.push(member);
    selection = { type: 'member', id: member.id };
    emit();
    return member;
  }

  function removeMember(id) {
    model.members = model.members.filter((m) => m.id !== id);
    if (selection && selection.id === id) selection = null;
    emit();
  }

  function updateNode(id, patch) {
    const node = nodeById(id);
    if (!node) return;
    Object.assign(node, patch);
    emit();
  }

  function updateMember(id, patch) {
    const member = memberById(id);
    if (!member) return;
    Object.assign(member, patch);
    emit();
  }

  function loadAt(nodeId) {
    const load = model.loads.find((l) => l.node === nodeId);
    return load ? { Fx: load.Fx || 0, Fy: load.Fy || 0 } : { Fx: 0, Fy: 0 };
  }

  function setLoad(nodeId, Fx, Fy) {
    model.loads = model.loads.filter((l) => l.node !== nodeId);
    if (Number(Fx) !== 0 || Number(Fy) !== 0) {
      model.loads.push({ node: nodeId, Fx: round(Fx), Fy: round(Fy) });
    }
    emit();
  }

  function cycleSupport(nodeId) {
    const node = nodeById(nodeId);
    if (!node) return;
    const order = ['none', 'pin', 'roller', 'roller_x'];
    const next = order[(order.indexOf(node.support || 'none') + 1) % order.length];
    node.support = next;
    emit();
  }

  function setUnits(force, length, area, stress) {
    model.units = {
      force,
      length,
      area: area || model.units.area || 'mm²',
      stress: stress || model.units.stress || 'MPa',
    };
    emit();
  }

  function setSelection(next) {
    selection = next;
    emit();
  }

  function getSelection() {
    return selection;
  }

  function getModel() {
    return model;
  }

  function setModel(next) {
    model = {
      units: {
        force: (next.units && next.units.force) || 'kN',
        length: (next.units && next.units.length) || 'm',
        area: (next.units && next.units.area) || 'mm²',
        stress: (next.units && next.units.stress) || 'MPa',
      },
      nodes: (next.nodes || []).map((n) => ({
        id: String(n.id),
        x: Number(n.x) || 0,
        y: Number(n.y) || 0,
        support: n.support || 'none',
      })),
      members: (next.members || []).map((m, index) => {
        const rawArea = Number(m.area);
        return {
          id: String(m.id || `${m.a}${m.b}` || `M${index + 1}`),
          a: String(m.a),
          b: String(m.b),
          EA: m.EA === undefined ? 1 : Number(m.EA),
          area: Number.isFinite(rawArea) && rawArea > 0 ? rawArea : null,
        };
      }),
      loads: (next.loads || []).map((l) => ({
        node: String(l.node),
        Fx: Number(l.Fx) || 0,
        Fy: Number(l.Fy) || 0,
      })),
    };
    selection = null;
    emit();
  }

  function reset() {
    model = emptyModel();
    selection = null;
    emit();
  }

  /** Payload no contrato de `docs/plano.md` §4. */
  function toPayload() {
    return {
      units: { ...model.units },
      nodes: model.nodes.map((n) => ({
        id: n.id,
        x: n.x,
        y: n.y,
        support: n.support || 'none',
      })),
      members: model.members.map((m) => {
        const entry = { id: m.id, a: m.a, b: m.b, EA: m.EA };
        if (m.area !== null && m.area !== undefined && Number(m.area) > 0) {
          entry.area = Number(m.area);
        }
        return entry;
      }),
      loads: model.loads.map((l) => ({ node: l.node, Fx: l.Fx, Fy: l.Fy })),
    };
  }

  return {
    subscribe,
    getModel,
    getSelection,
    setSelection,
    setModel,
    setUnits,
    reset,
    toPayload,
    addNode,
    removeNode,
    addMember,
    removeMember,
    updateNode,
    updateMember,
    setLoad,
    loadAt,
    cycleSupport,
    nodeById,
    memberById,
    findMember,
    nodeAt,
    setAllAreas,
  };
})();
