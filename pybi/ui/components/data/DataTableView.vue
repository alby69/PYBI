<template>
  <div class="data-table-view flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-white text-pbi-text">
    <div class="flex h-9 shrink-0 items-center gap-2 border-b border-pbi-pane-border bg-pbi-header px-2 text-pbi-xs">
      <div class="flex items-center gap-1.5 font-semibold">
        <span>🧮</span><span>Vista dati</span>
      </div>
      <span class="h-4 w-px bg-pbi-pane-border"></span>
      <select
        :value="store.activeDataTable"
        class="max-w-[220px] rounded border border-pbi-pane-border bg-white px-1.5 py-0.5 text-[10px]"
        @change="changeTable($event.target.value)"
      >
        <option v-for="table in store.tables" :key="table.name" :value="table.name">{{ table.name }}</option>
      </select>
      <span class="rounded bg-white px-1.5 py-0.5 font-mono text-[9px] text-pbi-text-muted">
        {{ filteredRows.toLocaleString('it-IT') }} / {{ totalRows.toLocaleString('it-IT') }} righe
      </span>
      <span v-if="columnCount" class="rounded bg-white px-1.5 py-0.5 font-mono text-[9px] text-pbi-text-muted">{{ columnCount }} colonne</span>

      <div class="relative ml-auto w-64">
        <input
          :value="store.tableSearch"
          type="search"
          placeholder="Filtra tutte le colonne…"
          class="w-full rounded border border-pbi-pane-border bg-white py-0.5 pl-6 pr-6 text-[10px] outline-none focus:border-pbi-accent"
          @input="onSearchInput"
          @keydown.enter="searchNow"
        />
        <span class="pointer-events-none absolute left-1.5 top-0.5 text-[10px] text-pbi-text-muted">🔍</span>
        <button v-if="store.tableSearch" class="absolute right-1 top-0 text-[10px] text-pbi-text-muted hover:text-pbi-text" @click="clearSearch">✕</button>
      </div>

      <button class="pbi-btn pbi-btn-ghost" title="Aggiorna dati" @click="refresh">⟳</button>
      <button class="pbi-btn pbi-btn-ghost" title="Esporta CSV" @click="exportCsv">📄</button>
      <button class="pbi-btn pbi-btn-ghost" title="Esporta Excel" @click="exportXlsx">📊</button>
    </div>

    <div class="relative min-h-0 flex-1 overflow-auto">
      <div v-if="store.tableLoading" class="absolute inset-0 z-30 flex items-center justify-center bg-white/70 backdrop-blur-[1px]">
        <div class="flex items-center gap-2 rounded border border-pbi-pane-border bg-white px-3 py-2 text-pbi-xs shadow-pbi-card">
          <span class="h-3 w-3 animate-spin rounded-full border-2 border-pbi-accent border-t-transparent"></span>
          Caricamento dati…
        </div>
      </div>

      <div v-if="errorMessage" class="m-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-pbi-xs text-red-700">
        {{ errorMessage }}
      </div>

      <div v-else-if="!rows.length && !store.tableLoading" class="flex h-full flex-col items-center justify-center gap-2 text-pbi-text-muted">
        <span class="text-4xl opacity-30">🧮</span>
        <span class="text-pbi-md font-semibold">Nessun dato da mostrare</span>
        <span class="text-pbi-xs">Seleziona una tabella o carica un dataset nel progetto.</span>
      </div>

      <table v-else class="data-grid border-collapse text-left text-pbi-xs">
        <thead class="sticky top-0 z-20">
          <tr class="bg-pbi-header">
            <th class="row-number-header sticky left-0 z-30 border-b border-r border-pbi-pane-border px-1 py-1 text-center font-mono text-[9px] font-normal text-pbi-text-muted">#</th>
            <th
              v-for="column in columns"
              :key="column.name"
              class="group border-b border-r border-pbi-pane-border px-2 py-1 font-semibold"
              :style="{ minWidth: `${columnWidth(column)}px`, maxWidth: `${columnWidth(column)}px` }"
              @contextmenu.prevent="openColumnMenu(column, $event)"
            >
              <div class="flex items-center gap-1">
                <span class="shrink-0 text-[9px] text-pbi-accent">{{ columnIcon(column) }}</span>
                <span class="min-w-0 flex-1 truncate" :title="`${column.name} (${column.data_type})`">{{ column.name }}</span>
                <button class="shrink-0 text-[9px] text-pbi-text-muted hover:text-pbi-accent" :title="'Ordina ' + column.name" @click="toggleSort(column)">
                  {{ sortIndicator(column.name) }}
                </button>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, index) in rows"
            :key="index"
            :class="index % 2 ? 'bg-slate-50 hover:bg-blue-50' : 'bg-white hover:bg-blue-50'"
          >
            <td class="row-number sticky left-0 z-10 border-b border-r border-slate-200 px-1 py-0.5 text-center font-mono text-[9px] text-pbi-text-muted">
              {{ index + 1 }}
            </td>
            <td
              v-for="column in columns"
              :key="column.name"
              class="border-b border-r border-slate-100 px-2 py-0.5"
              :class="{ 'text-right font-mono': isNumericColumn(column), 'text-red-500 italic': isNull(row[column.name]) }"
              :style="{ minWidth: `${columnWidth(column)}px`, maxWidth: `${columnWidth(column)}px` }"
              :title="cellTitle(row[column.name])"
              @dblclick="copyCell(row[column.name])"
            >
              <span class="block truncate">{{ formatCell(row[column.name]) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex h-7 shrink-0 items-center gap-3 border-t border-pbi-pane-border bg-pbi-header px-2 text-[9px] text-pbi-text-muted">
      <span class="font-semibold text-pbi-text">{{ store.activeDataTable || 'Nessuna tabella' }}</span>
      <span>{{ rows.length }} righe visualizzate</span>
      <span v-if="sortColumn">Ordinamento: {{ sortColumn }} {{ store.tableSort.dir.toUpperCase() }}</span>
      <span class="ml-auto">{{ store.tableData.error || 'Doppio clic su una cella per copiarla' }}</span>
      <button v-if="canLoadMore" class="pbi-btn pbi-btn-ghost" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? 'Caricamento…' : 'Carica altre righe' }}
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="columnMenu.open"
        ref="columnMenuRef"
        class="fixed z-[140] w-52 rounded border border-pbi-pane-border bg-white py-1 text-pbi-base text-pbi-text shadow-pbi-dropdown"
        :style="{ left: `${columnMenu.x}px`, top: `${columnMenu.y}px` }"
        @click.stop
        @mousedown.stop
      >
        <div class="truncate border-b border-pbi-pane-border px-2 py-1 text-[10px] font-semibold text-pbi-text-muted">{{ columnMenu.column?.name }}</div>
        <button class="menu-item" @click="sortFromMenu('asc')"><span>↑</span> Ordina crescente</button>
        <button class="menu-item" @click="sortFromMenu('desc')"><span>↓</span> Ordina decrescente</button>
        <div class="my-1 border-t border-pbi-pane-border"></div>
        <button class="menu-item" @click="copyColumnName"><span>⧉</span> Copia nome colonna</button>
        <button class="menu-item" @click="createVisualFromColumn"><span>📊</span> Crea visual da questa colonna</button>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';

export default {
  name: 'DataTableView',
  setup() {
const store = useReportStore();
const loadingMore = ref(false);
const columnMenuRef = ref(null);
const columnMenu = reactive({ open: false, x: 0, y: 0, column: null });
let searchTimer = null;
let initialised = false;

const columns = computed(() => store.tableData.columns || []);
const rows = computed(() => store.tableData.rows || []);
const columnCount = computed(() => columns.value.length);
const totalRows = computed(() => Number(store.tableData.total_rows || rows.value.length));
const filteredRows = computed(() => Number(store.tableData.filtered_rows || rows.value.length));
const errorMessage = computed(() => store.tableData.error || '');
const sortColumn = computed(() => store.tableSort.by || '');
const canLoadMore = computed(() => rows.value.length < filteredRows.value);

function columnIcon(column) {
  const dataType = String(column.data_type || '').toLowerCase();
  if (column.is_key) return '🔑';
  if (dataType.includes('date') || dataType.includes('time')) return '📅';
  if (dataType.includes('bool')) return '◐';
  if (dataType.includes('int') || dataType.includes('number') || dataType.includes('float') || dataType.includes('decimal')) return '#';
  return 'ABC';
}

function isNumericColumn(column) {
  const dataType = String(column.data_type || '').toLowerCase();
  return ['integer', 'number'].some(token => dataType.includes(token));
}

function columnWidth(column) {
  const dataType = String(column.data_type || '').toLowerCase();
  if (column.is_key) return 110;
  if (dataType.includes('date') || dataType.includes('time')) return 150;
  if (dataType.includes('bool')) return 90;
  if (dataType.includes('int') || dataType.includes('number') || dataType.includes('float') || dataType.includes('decimal')) return 120;
  return 170;
}

function isNull(value) {
  return value === null || value === undefined;
}

function formatCell(value) {
  if (isNull(value)) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString('it-IT') : value.toLocaleString('it-IT', { maximumFractionDigits: 6 });
  }
  return String(value);
}

function cellTitle(value) {
  if (isNull(value)) return 'null';
  const text = String(value);
  return text.length > 40 ? text : '';
}

async function changeTable(tableName) {
  await store.setActiveDataTable(tableName);
}

function onSearchInput(event) {
  const value = event.target.value;
  store.tableSearch = value;
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => store.searchTable(value), 350);
}

function searchNow() {
  if (searchTimer) clearTimeout(searchTimer);
  store.searchTable(store.tableSearch);
}

function clearSearch() {
  store.tableSearch = '';
  if (searchTimer) clearTimeout(searchTimer);
  store.searchTable('');
}

async function refresh() {
  await store.fetchTableData({ table: store.activeDataTable });
}

function sortIndicator(columnName) {
  if (store.tableSort.by !== columnName) return '↕';
  return store.tableSort.dir === 'asc' ? '↑' : '↓';
}

async function toggleSort(column) {
  await store.sortTable(column.name);
}

async function loadMore() {
  if (loadingMore.value) return;
  loadingMore.value = true;
  try {
    await store.loadMoreTableData();
  } finally {
    loadingMore.value = false;
  }
}

function openColumnMenu(column, event) {
  columnMenu.column = column;
  columnMenu.x = Math.min(window.innerWidth - 220, Math.max(4, event.clientX - 180));
  columnMenu.y = Math.min(window.innerHeight - 220, Math.max(4, event.clientY));
  columnMenu.open = true;
}

function closeColumnMenu(event) {
  if (columnMenuRef.value && !columnMenuRef.value.contains(event.target)) columnMenu.open = false;
}

async function sortFromMenu(direction) {
  if (!columnMenu.column) return;
  await store.sortTable(columnMenu.column.name, direction);
  columnMenu.open = false;
}

async function copyColumnName() {
  if (!columnMenu.column) return;
  await copyText(columnMenu.column.name);
  columnMenu.open = false;
}

function createVisualFromColumn() {
  const column = columnMenu.column;
  if (!column) return;
  const table = store.activeDataTable;
  const type = isNumericColumn(column) ? 'column_chart' : 'table';
  store.addVisual(type, {
    field: store.fieldFromModel(column, table),
  });
  store.setActiveView('report');
  columnMenu.open = false;
}

async function copyCell(value) {
  if (isNull(value)) return;
  await copyText(String(value));
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    store.notify('Copiato negli appunti', 'success');
  } catch (error) {
    store.notify('Impossibile copiare negli appunti', 'warning');
  }
}

async function exportCsv() {
  const payload = { columns: columns.value.map(column => column.name), rows: rows.value, format: 'csv', filename: store.activeDataTable || 'data_view' };
  await download(payload, 'csv');
}

async function exportXlsx() {
  const payload = { columns: columns.value.map(column => column.name), rows: rows.value, format: 'xlsx', filename: store.activeDataTable || 'data_view' };
  await download(payload, 'xlsx');
}

async function download(payload, format) {
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(store.projectId)}/report/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`Export failed (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${payload.filename}.${format}`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
    store.notify(`Esportazione ${format.toUpperCase()} completata`, 'success');
  } catch (error) {
    store.notify(`Errore esportazione: ${error.message}`, 'error');
  }
}

async function ensureData() {
  if (initialised) return;
  initialised = true;
  if (!store.tables.length) await store.fetchTables();
  if (store.activeDataTable) {
    if (!store.tableData.rows?.length) await store.fetchTableData({ table: store.activeDataTable });
  }
}

onMounted(() => {
  document.addEventListener('mousedown', closeColumnMenu);
  ensureData();
});

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer);
  document.removeEventListener('mousedown', closeColumnMenu);
});

    return {
      store,
      loadingMore,
      columnMenuRef,
      columnMenu,
      columns,
      rows,
      columnCount,
      totalRows,
      filteredRows,
      errorMessage,
      sortColumn,
      canLoadMore,
      columnIcon,
      isNumericColumn,
      columnWidth,
      isNull,
      formatCell,
      cellTitle,
      changeTable,
      onSearchInput,
      searchNow,
      clearSearch,
      refresh,
      sortIndicator,
      toggleSort,
      loadMore,
      openColumnMenu,
      sortFromMenu,
      copyColumnName,
      createVisualFromColumn,
      copyCell,
      exportCsv,
      exportXlsx,
    };
  },
};
</script>

<style scoped>
.data-grid {
  width: max-content;
  min-width: 100%;
  table-layout: fixed;
}
.data-grid thead th {
  position: sticky;
  top: 0;
  background: #f0f0f0;
}
.row-number-header,
.row-number {
  width: 42px;
  min-width: 42px;
  max-width: 42px;
  background: #f7f7f7;
}
.data-grid tr:hover .row-number {
  background: #eaf4ff;
}
.menu-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  text-align: left;
  font-size: 11px;
  white-space: nowrap;
}
.menu-item:hover {
  background-color: #f3f2f1;
}
</style>
