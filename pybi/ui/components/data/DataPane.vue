<template>
  <div class="data-pane flex h-full min-h-0 w-72 shrink-0 flex-col border-r border-pbi-pane-border bg-pbi-pane text-pbi-text">
    <div class="flex h-9 shrink-0 items-center justify-between border-b border-pbi-pane-border px-2">
      <div class="flex items-center gap-1.5 text-pbi-md font-semibold">
        <span>🗂</span><span>DATI</span>
        <span class="rounded bg-slate-100 px-1 py-0.5 text-[9px] font-normal text-pbi-text-muted">{{ store.tables.length }}</span>
      </div>
      <button class="pbi-btn pbi-btn-ghost" :title="collapsed ? 'Espandi pannello dati' : 'Comprimi pannello dati'" @click="collapsed = !collapsed">
        {{ collapsed ? '›' : '‹' }}
      </button>
    </div>

    <div v-if="!collapsed" class="flex min-h-0 flex-1 flex-col">
      <div class="shrink-0 border-b border-pbi-pane-border p-1.5">
        <div class="relative">
          <input
            v-model="store.searchFilter"
            type="search"
            placeholder="Cerca tabelle e campi…"
            class="w-full rounded border border-pbi-pane-border bg-white py-1 pl-6 pr-6 text-pbi-xs outline-none focus:border-pbi-accent"
          />
          <span class="pointer-events-none absolute left-1.5 top-1 text-[11px] text-pbi-text-muted">🔍</span>
          <button v-if="store.searchFilter" class="absolute right-1 top-0.5 text-[11px] text-pbi-text-muted hover:text-pbi-text" @click="store.searchFilter = ''">✕</button>
        </div>
        <div class="mt-1 flex items-center gap-1 text-[9px]">
          <button class="pbi-btn pbi-btn-ghost" @click="expandAll">Espandi tutto</button>
          <button class="pbi-btn pbi-btn-ghost" @click="collapseAll">Comprimi tutto</button>
          <button class="ml-auto pbi-btn pbi-btn-ghost" title="Aggiorna tabelle" @click="refresh">⟳</button>
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto p-1">
        <div v-if="!store.tables.length" class="flex flex-col items-center gap-1 px-3 py-6 text-center text-pbi-xs text-pbi-text-muted">
          <span class="text-2xl opacity-40">🗃</span>
          <span>Nessuna tabella disponibile. Carica un dataset nella vista Dati.</span>
        </div>

        <div v-for="table in filteredTables" :key="table.name" class="mb-0.5">
          <div
            class="group flex cursor-pointer items-center gap-1 rounded px-1 py-1 text-[11px] font-semibold hover:bg-slate-100"
            @click="toggleTable(table.name)"
            @contextmenu.prevent.stop="openTableMenu(table, $event)"
          >
            <span class="w-2.5 text-[9px] text-pbi-text-muted">{{ isExpanded(table.name) ? '▾' : '▸' }}</span>
            <span class="text-[11px]">{{ table.type === 'semantic' ? '🧩' : '📄' }}</span>
            <span class="min-w-0 flex-1 truncate" :title="table.name">{{ table.name }}</span>
            <span class="shrink-0 text-[9px] font-normal text-pbi-text-muted">{{ visibleColumns(table).length }}</span>
            <button class="hidden shrink-0 rounded px-0.5 text-[11px] text-pbi-text-muted hover:bg-white group-hover:block" @click.stop="openTableMenu(table, $event)">⋯</button>
          </div>

          <div v-if="isExpanded(table.name)" class="ml-2 border-l border-pbi-pane-border pl-1">
            <div v-if="visibleColumns(table).length" class="mb-0.5 text-[8px] font-semibold uppercase tracking-wide text-pbi-text-muted">Campi</div>
            <div
              v-for="column in visibleColumns(table)"
              :key="`${table.name}.${column.name}`"
              class="data-field flex cursor-grab items-center gap-1 rounded px-1 py-0.5 text-[10px] hover:bg-blue-50"
              draggable="true"
              :title="`${column.name} · ${column.data_type || ''}`"
              @dragstart="onDragStart($event, column, table)"
              @click="addToSelected(column, table)"
              @dblclick.stop="addVisual(column, table)"
              @contextmenu.prevent.stop="openFieldMenu(column, table, $event)"
            >
              <span class="w-3 shrink-0 text-center text-[9px] text-pbi-accent">{{ fieldIcon(column) }}</span>
              <span class="min-w-0 flex-1 truncate" :class="{ 'italic text-pbi-text-muted': column.is_hidden }">{{ column.name }}</span>
              <span v-if="column.is_calculated" class="shrink-0 rounded bg-purple-100 px-1 text-[8px] text-purple-700">fx</span>
              <span v-else-if="column.is_key" class="shrink-0 text-[8px]" title="Chiave">🔑</span>
            </div>

            <template v-if="visibleMeasures(table).length">
              <div class="mb-0.5 mt-1 text-[8px] font-semibold uppercase tracking-wide text-pbi-text-muted">Misure</div>
              <div
                v-for="measure in visibleMeasures(table)"
                :key="`${table.name}.m.${measure.name}`"
                class="data-field flex cursor-grab items-center gap-1 rounded px-1 py-0.5 text-[10px] hover:bg-purple-50"
                draggable="true"
                :title="measure.expression || measure.name"
                @dragstart="onDragStart($event, measure, table, true)"
                @click="addToSelected(measure, table, true)"
                @dblclick.stop="addVisual(measure, table, true)"
                @contextmenu.prevent.stop="openFieldMenu(measure, table, $event, true)"
              >
                <span class="w-3 shrink-0 text-center text-[9px] text-purple-600">∑</span>
                <span class="min-w-0 flex-1 truncate">{{ measure.label || measure.name }}</span>
              </div>
            </template>

            <button class="add-filter-btn mt-0.5" @click.stop="openMeasureModal(table)">＋ Nuova misura</button>
          </div>
        </div>
      </div>

      <div class="shrink-0 border-t border-pbi-pane-border p-1.5">
        <button class="pbi-btn pbi-btn-primary w-full" @click="openMeasureModal(store.tables[0] || null)">
          ＋ Nuova misura
        </button>
      </div>
    </div>

    <div v-else class="flex flex-1 flex-col items-center gap-3 pt-3">
      <span class="text-lg" title="Dati">🗂</span>
      <span class="text-lg" title="Filtri">🔎</span>
      <span class="text-lg" title="Visualizzazioni">📊</span>
    </div>

    <!-- Field / table context menu -->
    <Teleport to="body">
      <div
        v-if="menu.open"
        ref="menuRef"
        class="fixed z-[120] w-58 rounded border border-pbi-pane-border bg-white py-1 text-pbi-base text-pbi-text shadow-pbi-dropdown"
        :style="{ left: `${menu.x}px`, top: `${menu.y}px` }"
        @click.stop
        @mousedown.stop
      >
        <div class="truncate border-b border-pbi-pane-border px-2 py-1 text-[10px] font-semibold text-pbi-text-muted">
          {{ menu.label }}
        </div>
        <template v-if="menu.kind === 'field'">
          <button class="menu-item" @click="menuAddField"><span>➕</span> Aggiungi al visual selezionato</button>
          <button class="menu-item" @click="menuCreateVisual('column_chart')"><span>📶</span> Crea istogramma</button>
          <button class="menu-item" @click="menuCreateVisual('line_chart')"><span>📈</span> Crea grafico a linee</button>
          <button class="menu-item" @click="menuCreateVisual('table')"><span>📋</span> Crea tabella</button>
          <button class="menu-item" @click="menuCreateVisual('card')"><span>🔢</span> Crea scheda</button>
          <div class="my-1 border-t border-pbi-pane-border"></div>
          <button class="menu-item" @click="renameField"><span>✏️</span> Rinomina</button>
          <button v-if="menu.measure" class="menu-item" @click="deleteMeasure"><span>🗑</span> Elimina misura</button>
          <button v-else class="menu-item" @click="hideField"><span>👁️‍🗨️</span> {{ menu.field.is_hidden ? 'Mostra campo' : 'Nascondi campo' }}</button>
        </template>
        <template v-else>
          <button class="menu-item" @click="menuCreateVisual('table')"><span>📋</span> Mostra tabella nei dati</button>
          <button class="menu-item" @click="menuNewMeasure"><span>∑</span> Nuova misura</button>
          <div class="my-1 border-t border-pbi-pane-border"></div>
          <button class="menu-item" @click="renameTable"><span>✏️</span> Rinomina tabella</button>
          <button class="menu-item"><span>👁️‍🗨️</span> Nascondi tabella</button>
        </template>
      </div>
    </Teleport>

    <!-- Measure modal -->
    <Teleport to="body">
      <div v-if="measureModal.open" class="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 p-4" @mousedown.self="measureModal.open = false">
        <div class="w-full max-w-lg overflow-hidden rounded border border-pbi-pane-border bg-white shadow-pbi-modal">
          <div class="flex items-center justify-between border-b border-pbi-pane-border bg-pbi-header px-3 py-2">
            <div class="flex items-center gap-2">
              <span class="rounded bg-purple-600 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white">Σ</span>
              <span class="text-pbi-md font-semibold">Nuova misura</span>
            </div>
            <button class="pbi-btn pbi-btn-ghost" @click="measureModal.open = false">✕</button>
          </div>
          <div class="space-y-2 p-3 text-pbi-xs">
            <label class="block">
              <span class="mb-0.5 block text-pbi-text-muted">Tabella</span>
              <select v-model="measureModal.table" class="w-full rounded border border-pbi-pane-border px-2 py-1">
                <option v-for="table in store.tables" :key="table.name" :value="table.name">{{ table.name }}</option>
              </select>
            </label>
            <label class="block">
              <span class="mb-0.5 block text-pbi-text-muted">Nome misura</span>
              <input v-model="measureModal.name" type="text" class="w-full rounded border border-pbi-pane-border px-2 py-1" placeholder="es. Totale vendite" />
            </label>
            <label class="block">
              <span class="mb-0.5 block text-pbi-text-muted">Espressione DAX / SQL</span>
              <textarea v-model="measureModal.expression" rows="3" class="w-full rounded border border-pbi-pane-border px-2 py-1 font-mono text-[11px]" placeholder="SUM(amount)"></textarea>
            </label>
            <div class="grid grid-cols-2 gap-2">
              <label class="block">
                <span class="mb-0.5 block text-pbi-text-muted">Formato</span>
                <input v-model="measureModal.format" type="text" class="w-full rounded border border-pbi-pane-border px-2 py-1" placeholder="#,##0.00" />
              </label>
              <label class="block">
                <span class="mb-0.5 block text-pbi-text-muted">Cartella</span>
                <input v-model="measureModal.folder" type="text" class="w-full rounded border border-pbi-pane-border px-2 py-1" placeholder="KPI" />
              </label>
            </div>
            <div v-if="measureModal.error" class="rounded bg-red-50 px-2 py-1 text-[10px] text-red-700">{{ measureModal.error }}</div>
          </div>
          <div class="flex justify-end gap-2 border-t border-pbi-pane-border bg-slate-50 px-3 py-2">
            <button class="pbi-btn pbi-btn-ghost" @click="measureModal.open = false">Annulla</button>
            <button class="pbi-btn pbi-btn-primary" :disabled="measureModal.saving" @click="saveMeasure">
              {{ measureModal.saving ? 'Salvataggio…' : 'Salva misura' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';

export default {
  name: 'DataPane',
  setup() {
const store = useReportStore();
const collapsed = ref(false);
const expanded = reactive({});
const menuRef = ref(null);
const menu = reactive({ open: false, kind: 'field', x: 0, y: 0, table: null, field: null, measure: false, label: '' });
const measureModal = reactive({ open: false, table: '', name: '', expression: '', format: '#,##0.00', folder: '', error: '', saving: false });

const query = computed(() => (store.searchFilter || '').toLowerCase().trim());

const filteredTables = computed(() => {
  if (!query.value) return store.tables;
  return store.tables.filter(table => {
    if ((table.name || '').toLowerCase().includes(query.value)) return true;
    return (table.columns || []).some(column => (column.name || '').toLowerCase().includes(query.value))
      || (table.measures || []).some(measure => `${measure.name} ${measure.label || ''}`.toLowerCase().includes(query.value));
  });
});

function visibleColumns(table) {
  const columns = (table.columns || []).filter(column => !column.is_hidden || query.value);
  if (!query.value) return columns;
  return columns.filter(column => (column.name || '').toLowerCase().includes(query.value));
}

function visibleMeasures(table) {
  const measures = (table.measures || []).filter(measure => !measure.is_hidden || query.value);
  if (!query.value) return measures;
  return measures.filter(measure => `${measure.name} ${measure.label || ''}`.toLowerCase().includes(query.value));
}

function isExpanded(tableName) {
  if (query.value) return true;
  return expanded[tableName] !== undefined ? expanded[tableName] : store.tables.findIndex(table => table.name === tableName) === 0;
}

function toggleTable(tableName) {
  expanded[tableName] = !isExpanded(tableName);
}

function expandAll() {
  store.tables.forEach(table => { expanded[table.name] = true; });
}

function collapseAll() {
  store.tables.forEach(table => { expanded[table.name] = false; });
}

function fieldIcon(field) {
  const dataType = String(field.data_type || '').toLowerCase();
  if (field.is_calculated) return 'ƒ';
  if (dataType.includes('date') || dataType.includes('time')) return '📅';
  if (dataType.includes('bool')) return '◐';
  if (dataType.includes('int') || dataType.includes('number') || dataType.includes('float') || dataType.includes('decimal')) return '#';
  return 'ABC';
}

function fieldPayload(field, table, isMeasure = false) {
  if (isMeasure) {
    return store.fieldFromModel({
      ...field,
      kind: 'measure',
      table: table.name,
      column: field.column || field.column_name || field.name,
      data_type: 'number',
      aggregation: field.agg_func || 'SUM',
      display_name: field.label || field.name,
    }, table.name);
  }
  return store.fieldFromModel(field, table.name);
}

function onDragStart(event, field, table, isMeasure = false) {
  const payload = fieldPayload(field, table, isMeasure);
  event.dataTransfer.effectAllowed = 'copy';
  try {
    event.dataTransfer.setData('application/x-pybi-field', JSON.stringify(payload));
    event.dataTransfer.setData('text/plain', JSON.stringify(payload));
  } catch (error) {
    // Ignore browsers that block custom drag data.
  }
}

function addToSelected(field, table, isMeasure = false) {
  const visual = store.selectedVisual;
  if (!visual) {
    addVisual(field, table, isMeasure);
    return;
  }
  const payload = fieldPayload(field, table, isMeasure);
  let bucket = 'y_axis';
  if (['table', 'matrix'].includes(visual.type)) bucket = visual.type === 'matrix' ? 'values' : 'values';
  else if (['card', 'kpi', 'gauge', 'multi_row_card', 'slicer'].includes(visual.type)) bucket = 'values';
  else if (!(visual.data_buckets?.x_axis && (Array.isArray(visual.data_buckets.x_axis) ? visual.data_buckets.x_axis.length : visual.data_buckets.x_axis))) bucket = 'x_axis';
  if (payload.kind === 'measure' && bucket === 'x_axis') bucket = 'y_axis';
  store.addFieldToBucket(visual.id, bucket, payload);
}

function addVisual(field, table, isMeasure = false) {
  const payload = fieldPayload(field, table, isMeasure);
  const type = payload.kind === 'measure' ? 'card' : 'table';
  store.addVisual(type, { field: payload });
}

function openTableMenu(table, event) {
  const x = Math.min(window.innerWidth - 240, Math.max(4, event.clientX));
  const y = Math.min(window.innerHeight - 240, Math.max(4, event.clientY));
  Object.assign(menu, { open: true, kind: 'table', x, y, table, field: null, measure: false, label: table.name });
}

function openFieldMenu(field, table, event, isMeasure = false) {
  const x = Math.min(window.innerWidth - 240, Math.max(4, event.clientX));
  const y = Math.min(window.innerHeight - 280, Math.max(4, event.clientY));
  Object.assign(menu, {
    open: true,
    kind: 'field',
    x,
    y,
    table,
    field,
    measure: isMeasure,
    label: isMeasure ? field.label || field.name : field.name,
  });
}

function closeMenu(event) {
  if (menuRef.value && !menuRef.value.contains(event.target)) menu.open = false;
}

function menuAddField() {
  addToSelected(menu.field, menu.table, menu.measure);
  menu.open = false;
}

function menuCreateVisual(type) {
  if (menu.kind === 'table') {
    store.setActiveDataTable(menu.table.name);
    store.setActiveView('data');
    store.activePanel = 'data';
    menu.open = false;
    return;
  }
  const payload = fieldPayload(menu.field, menu.table, menu.measure);
  store.addVisual(type, { field: payload });
  menu.open = false;
}

async function renameField() {
  const field = menu.field;
  const current = menu.measure ? field.name : field.name;
  const value = window.prompt('Nuovo nome', current);
  if (value && value.trim() && value.trim() !== current) {
    try {
      if (menu.measure) await store.renameMeasure(menu.table.name, field.name, value.trim());
      else await store.renameColumn(menu.table.name, field.name, value.trim());
    } catch (error) {
      store.notify(`Rinomina non riuscita: ${error.message}`, 'error');
    }
  }
  menu.open = false;
}

async function hideField() {
  try {
    if (menu.measure) await store.hideMeasure(menu.table.name, menu.field.name, !menu.field.is_hidden);
    else await store.hideColumn(menu.table.name, menu.field.name, !menu.field.is_hidden);
  } catch (error) {
    store.notify(`Operazione non riuscita: ${error.message}`, 'error');
  }
  menu.open = false;
}

async function deleteMeasure() {
  if (!window.confirm(`Eliminare la misura "${menu.field.name}"?`)) return;
  try {
    await store.deleteMeasure(menu.table.name, menu.field.name);
  } catch (error) {
    store.notify(`Eliminazione non riuscita: ${error.message}`, 'error');
  }
  menu.open = false;
}

async function renameTable() {
  const value = window.prompt('Nuovo nome tabella', menu.table.name);
  if (value && value.trim() && value.trim() !== menu.table.name) {
    try {
      await store.renameTable(menu.table.name, value.trim());
    } catch (error) {
      store.notify(`Rinomina non riuscita: ${error.message}`, 'error');
    }
  }
  menu.open = false;
}

function menuNewMeasure() {
  openMeasureModal(menu.table);
  menu.open = false;
}

function openMeasureModal(table) {
  measureModal.open = true;
  measureModal.table = table?.name || store.tables[0]?.name || '';
  measureModal.name = '';
  measureModal.expression = '';
  measureModal.format = '#,##0.00';
  measureModal.folder = '';
  measureModal.error = '';
  measureModal.saving = false;
}

async function saveMeasure() {
  measureModal.error = '';
  if (!measureModal.name.trim() || !measureModal.expression.trim()) {
    measureModal.error = 'Nome ed espressione sono obbligatori.';
    return;
  }
  measureModal.saving = true;
  try {
    await store.saveMeasure({
      name: measureModal.name.trim(),
      table_name: measureModal.table,
      expression: measureModal.expression.trim(),
      format_string: measureModal.format || null,
      display_folder: measureModal.folder || null,
    });
    measureModal.open = false;
  } catch (error) {
    measureModal.error = error.message;
  } finally {
    measureModal.saving = false;
  }
}

async function refresh() {
  await store.fetchTables();
}

onMounted(() => document.addEventListener('mousedown', closeMenu));
onBeforeUnmount(() => document.removeEventListener('mousedown', closeMenu));

    return {
      store,
      collapsed,
      expanded,
      menuRef,
      menu,
      measureModal,
      filteredTables,
      visibleColumns,
      visibleMeasures,
      isExpanded,
      toggleTable,
      expandAll,
      collapseAll,
      fieldIcon,
      fieldPayload,
      onDragStart,
      addToSelected,
      addVisual,
      openTableMenu,
      openFieldMenu,
      menuAddField,
      menuCreateVisual,
      renameField,
      hideField,
      deleteMeasure,
      renameTable,
      menuNewMeasure,
      openMeasureModal,
      saveMeasure,
      refresh,
    };
  },
};
</script>

<style scoped>
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
.data-field:hover {
  outline: 1px solid rgba(17, 141, 255, 0.35);
}
</style>
