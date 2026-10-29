import { reactive } from 'vue';

const emptyPreview = () => ({
  columns: [],
  rows: [],
  data_types: {},
  total_rows: 0,
  total_columns: 0,
  execution_time: 0
});

export const state = reactive({
  activeProject: 'default',
  selectedTable: null,
  tables: [],
  activeStepIndex: 0,
  appliedStepsByTable: {},
  previewData: emptyPreview(),
  isLoadingPreview: false,
  isSaving: false,
  isExecuting: false,
  error: null,
  statusMessage: '',
  currentView: 'grid',
  showProfilingBar: true,
  profilingColumn: null,
  selectedStepIndex: -1
});

let previewToken = 0;
let stepCounter = 0;

function projectId() {
  return state.activeProject || 'default';
}

function fileTable(name) {
  return typeof name === 'string' && /\.[A-Za-z0-9]+$/.test(name);
}

function sourceFor(tableName) {
  if (!tableName) return {};
  if (!fileTable(tableName)) return { table_name: tableName };
  const ext = tableName.split('.').pop().toLowerCase();
  const type = ext === 'parquet' ? 'parquet' : (ext === 'sqlite' || ext === 'db') ? 'sqlite' : 'csv';
  return { type, path: tableName, table_name: tableName };
}

function stepKey() {
  stepCounter += 1;
  return `step_${Date.now()}_${stepCounter}`;
}

function clampStepIndex(index, length) {
  const parsed = Number.isFinite(Number(index)) ? Number(index) : length;
  return Math.max(0, Math.min(parsed, length));
}

function normalizePreview(data) {
  if (!data || typeof data !== 'object') return emptyPreview();
  const columns = Array.isArray(data.columns) ? data.columns : [];
  return {
    columns: columns.map(col => (typeof col === 'string' ? col : col.name)).filter(Boolean),
    rows: Array.isArray(data.rows) ? data.rows : [],
    data_types: data.data_types || {},
    total_rows: data.total_rows ?? (Array.isArray(data.rows) ? data.rows.length : 0),
    total_columns: data.total_columns ?? columns.length,
    execution_time: data.execution_time || 0
  };
}

async function fetchPreview() {
  const target = state.selectedTable;
  if (!target) {
    state.previewData = emptyPreview();
    return null;
  }
  const token = ++previewToken;
  const steps = getStepsForTable(target);
  const stepIndex = clampStepIndex(state.activeStepIndex, steps.length);
  state.activeStepIndex = stepIndex;
  state.selectedStepIndex = stepIndex - 1;
  state.isLoadingPreview = true;
  state.error = null;
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(projectId())}/etl/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: {
          query_name: target,
          source: sourceFor(target),
          steps
        },
        step_index: stepIndex
      })
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Preview failed (${response.status})`);
    }
    const data = await response.json();
    if (token !== previewToken) return null;
    state.previewData = normalizePreview(data);
    return state.previewData;
  } catch (err) {
    if (token !== previewToken) return null;
    state.error = err.message || String(err);
    state.previewData = emptyPreview();
    return null;
  } finally {
    if (token === previewToken) state.isLoadingPreview = false;
  }
}

function ensureTable(tableName) {
  if (!tableName) return;
  if (!state.appliedStepsByTable[tableName]) {
    state.appliedStepsByTable[tableName] = [];
  }
  if (!state.tables.includes(tableName)) {
    state.tables.push(tableName);
  }
}

function setTables(tables) {
  state.tables = (tables || []).map(table => (typeof table === 'string' ? table : table.name)).filter(Boolean);
}

function setProject(id) {
  state.activeProject = id || 'default';
}

function getStepsForTable(tableName) {
  const target = tableName || state.selectedTable;
  if (!target) return [];
  if (!state.appliedStepsByTable[target]) state.appliedStepsByTable[target] = [];
  return state.appliedStepsByTable[target];
}

function setStepsForTable(tableName, steps) {
  if (!tableName) return;
  state.appliedStepsByTable[tableName] = (steps || []).map(step => ({ ...step, id: step.id || step.step_id || stepKey() }));
  ensureTable(tableName);
  state.activeStepIndex = state.appliedStepsByTable[tableName].length;
  state.selectedStepIndex = state.activeStepIndex - 1;
}

function setSelectedTable(tableName, options = {}) {
  if (!tableName) return;
  if (state.selectedTable === tableName && options.force !== true) {
    ensureTable(tableName);
    return;
  }
  state.selectedTable = tableName;
  ensureTable(tableName);
  const steps = getStepsForTable(tableName);
  state.activeStepIndex = options.previewStepIndex ?? steps.length;
  state.selectedStepIndex = state.activeStepIndex - 1;
  state.profilingColumn = null;
  if (options.fetch !== false) fetchPreview();
}

function setActiveStepIndex(index) {
  const target = state.selectedTable;
  const steps = target ? getStepsForTable(target) : [];
  state.activeStepIndex = clampStepIndex(index, steps.length);
  state.selectedStepIndex = state.activeStepIndex - 1;
  return fetchPreview();
}

function addStep(step, tableName) {
  const target = tableName || state.selectedTable;
  if (!target || !step) return null;
  ensureTable(target);
  const nextStep = { ...step, id: step.id || step.step_id || stepKey() };
  state.appliedStepsByTable[target].push(nextStep);
  state.activeStepIndex = state.appliedStepsByTable[target].length;
  state.selectedStepIndex = state.activeStepIndex - 1;
  fetchPreview();
  return nextStep;
}

function addStepForTable(tableName, step) {
  return addStep(step, tableName);
}

function removeStep(index, tableName) {
  const target = tableName || state.selectedTable;
  const steps = target ? getStepsForTable(target) : [];
  if (index < 0 || index >= steps.length) return;
  steps.splice(index, 1);
  state.activeStepIndex = clampStepIndex(state.activeStepIndex, steps.length);
  state.selectedStepIndex = state.activeStepIndex - 1;
  fetchPreview();
}

function deleteStep(index, tableName) {
  removeStep(index, tableName);
}

function updateStep(index, step, tableName) {
  const target = tableName || state.selectedTable;
  const steps = target ? getStepsForTable(target) : [];
  if (index < 0 || index >= steps.length) return;
  steps.splice(index, 1, { ...step, id: step.id || steps[index].id || stepKey() });
  fetchPreview();
}

function clearSteps(tableName) {
  const target = tableName || state.selectedTable;
  if (!target) return;
  state.appliedStepsByTable[target] = [];
  state.activeStepIndex = 0;
  state.selectedStepIndex = -1;
  fetchPreview();
}

function selectProfilingColumn(column) {
  state.profilingColumn = state.profilingColumn === column ? null : column;
}

function setView(view) {
  state.currentView = view === 'diagram' ? 'diagram' : 'grid';
}

function setStatus(message) {
  state.statusMessage = message || '';
}

function currentQuery() {
  const target = state.selectedTable;
  return {
    query_name: target || 'Query1',
    source: sourceFor(target),
    steps: target ? getStepsForTable(target) : []
  };
}

async function saveQuery() {
  const target = state.selectedTable;
  if (!target) return null;
  state.isSaving = true;
  state.error = null;
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(projectId())}/etl/query`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentQuery())
    });
    if (!response.ok) throw new Error(await response.text());
    state.statusMessage = `Query "${target}" salvata.`;
    return await response.json();
  } catch (err) {
    state.error = err.message || String(err);
    return null;
  } finally {
    state.isSaving = false;
  }
}

async function loadQuery(tableName) {
  const target = tableName || state.selectedTable;
  state.error = null;
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(projectId())}/etl/query`);
    if (!response.ok) throw new Error(await response.text());
    const query = await response.json();
    const source = query.source || {};
    const loadedTable = source.table_name || source.path || target || 'sales_data.csv';
    setStepsForTable(loadedTable, query.steps || []);
    setSelectedTable(loadedTable, { fetch: false });
    state.activeStepIndex = getStepsForTable(loadedTable).length;
    state.selectedStepIndex = state.activeStepIndex - 1;
    state.statusMessage = `Query "${query.query_name || loadedTable}" caricata.`;
    await fetchPreview();
    return query;
  } catch (err) {
    state.error = err.message || String(err);
    return null;
  }
}

async function executeQuery(targetTable) {
  const target = state.selectedTable;
  if (!target) return null;
  state.isExecuting = true;
  state.error = null;
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(projectId())}/etl/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: currentQuery(),
        target_table_name: targetTable || target
      })
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    state.statusMessage = `Query eseguita: ${data.rows_processed || 0} righe.`;
    return data;
  } catch (err) {
    state.error = err.message || String(err);
    return null;
  } finally {
    state.isExecuting = false;
  }
}

async function exportPythonScript(tableName) {
  const target = tableName || state.selectedTable || 'Sales_Data';
  const payload = {
    query_id: target,
    query_name: target,
    source: sourceFor(target),
    steps: getStepsForTable(target)
  };
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(projectId())}/etl/export/python`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `pipeline_${target}.py`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
    state.statusMessage = `Script Python esportato per "${target}".`;
  } catch (err) {
    state.error = err.message || String(err);
  }
}

function renameTable(oldName, newName) {
  if (!oldName || !newName || oldName === newName) return;
  state.appliedStepsByTable[newName] = state.appliedStepsByTable[oldName] || [];
  delete state.appliedStepsByTable[oldName];
  state.tables = state.tables.map(table => (table === oldName ? newName : table));
  if (state.selectedTable === oldName) state.selectedTable = newName;
}

function duplicateTable(tableName) {
  if (!tableName) return null;
  let candidate = `${tableName}_copy`;
  let suffix = 2;
  while (state.appliedStepsByTable[candidate] || state.tables.includes(candidate)) {
    candidate = `${tableName}_copy${suffix}`;
    suffix += 1;
  }
  state.appliedStepsByTable[candidate] = getStepsForTable(tableName).map(step => ({ ...step, id: stepKey() }));
  state.tables.push(candidate);
  return candidate;
}

function referenceTable(tableName) {
  if (!tableName) return null;
  let candidate = `${tableName}_ref`;
  let suffix = 2;
  while (state.appliedStepsByTable[candidate] || state.tables.includes(candidate)) {
    candidate = `${tableName}_ref${suffix}`;
    suffix += 1;
  }
  state.appliedStepsByTable[candidate] = [];
  state.tables.push(candidate);
  return candidate;
}

function removeTable(tableName) {
  if (!tableName) return;
  delete state.appliedStepsByTable[tableName];
  state.tables = state.tables.filter(table => table !== tableName);
  if (state.selectedTable === tableName) {
    const next = state.tables[0] || null;
    state.selectedTable = next;
    if (next) setSelectedTable(next, { force: true });
    else state.previewData = emptyPreview();
  }
}

export const actions = {
  setTables,
  setProject,
  setSelectedTable,
  setCurrentSourceTable: setSelectedTable,
  getStepsForTable,
  setStepsForTable,
  setActiveStepIndex,
  addStep,
  addStepForTable,
  removeStep,
  deleteStep,
  updateStep,
  clearSteps,
  fetchPreview,
  selectProfilingColumn,
  setView,
  setStatus,
  saveQuery,
  loadQuery,
  executeQuery,
  exportPythonScript,
  renameTable,
  duplicateTable,
  referenceTable,
  removeTable,
  sourceFor,
  currentQuery
};

export const store = Object.assign(state, actions);

export function useUiStore() {
  return store;
}

export const useUIStore = () => ({
  state,
  loadSchema: async (pageName) => {
    const res = await fetch(`/api/ui/schema/${pageName}`);
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
  },
  triggerAction: async (action, payload = {}) => {
    if (typeof action !== 'string' || !action.startsWith('api:')) return null;
    const parts = action.split(':');
    const method = parts[1] && ['GET', 'POST', 'PUT', 'DELETE'].includes(parts[1].toUpperCase()) ? parts[1].toUpperCase() : 'POST';
    const endpoint = parts.length > 2 ? parts.slice(2).join(':') : parts[1];
    const options = { method, headers: { 'Content-Type': 'application/json' } };
    if (method !== 'GET') options.body = JSON.stringify(payload);
    const res = await fetch(endpoint, options);
    return res.json();
  },
  setCurrentSourceTable: setSelectedTable,
  getStepsForTable,
  setStepsForTable,
  addStepForTable,
  exportPythonScript
});
