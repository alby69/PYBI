<template>
  <div class="visualizations-pane flex h-full min-h-0 w-72 flex-col border-l border-pbi-pane-border bg-pbi-pane text-pbi-text">
    <div class="flex h-9 shrink-0 items-center justify-between border-b border-pbi-pane-border px-2">
      <div class="flex items-center gap-1.5 text-pbi-md font-semibold">
        <span>📊</span><span>VISUALIZZAZIONI</span>
      </div>
      <button class="pbi-btn pbi-btn-ghost" title="Comprimi pannello" @click="store.togglePanel('visuals')">✕</button>
    </div>

    <template v-if="store.panelOpen.visuals">
      <div class="shrink-0 border-b border-pbi-pane-border p-1.5">
        <div class="mb-1 flex items-center justify-between">
          <span class="text-[9px] font-semibold uppercase tracking-wide text-pbi-text-muted">Tipo di visual</span>
          <span class="truncate text-[9px] text-pbi-text-muted">{{ currentLabel }}</span>
        </div>
        <div class="grid grid-cols-8 gap-0.5">
          <button
            v-for="option in visualTypes"
            :key="option.type"
            class="flex h-6 items-center justify-center rounded border text-[13px] transition-colors"
            :class="currentType === option.type ? 'border-pbi-accent bg-blue-50 ring-1 ring-pbi-accent' : 'border-transparent hover:border-pbi-pane-border hover:bg-slate-100'"
            :title="option.label"
            @click="setType(option.type)"
          >
            {{ option.icon }}
          </button>
        </div>
      </div>

      <div class="flex shrink-0 border-b border-pbi-pane-border text-[10px] font-semibold">
        <button class="flex-1 py-1.5" :class="tab === 'fields' ? 'border-b-2 border-pbi-accent text-pbi-accent' : 'text-pbi-text-muted hover:bg-slate-50'" @click="tab = 'fields'">
          📋 Campi / Dati
        </button>
        <button class="flex-1 py-1.5" :class="tab === 'format' ? 'border-b-2 border-pbi-accent text-pbi-accent' : 'text-pbi-text-muted hover:bg-slate-50'" @click="tab = 'format'">
          🎨 Formato
        </button>
      </div>

      <div v-if="tab === 'fields'" class="min-h-0 flex-1 overflow-y-auto p-1.5">
        <div v-if="!store.selectedVisual" class="flex h-full flex-col items-center justify-center gap-2 px-4 text-center text-pbi-text-muted">
          <span class="text-3xl opacity-40">🖱️</span>
          <span class="text-pbi-xs">Seleziona un visual sul canvas oppure scegli un tipo qui sopra per crearne uno nuovo.</span>
        </div>

        <template v-else>
          <div class="mb-1.5 rounded bg-slate-50 px-1.5 py-1">
            <div class="truncate text-[11px] font-semibold" :title="store.selectedVisual.title">{{ store.selectedVisual.title }}</div>
            <div class="text-[9px] text-pbi-text-muted">{{ currentLabel }}</div>
          </div>

          <div v-for="bucket in buckets" :key="bucket.key" class="mb-1.5">
            <div class="mb-0.5 flex items-center justify-between text-[9px] font-semibold uppercase tracking-wide text-pbi-text-muted">
              <span>{{ bucket.label }}</span>
              <span v-if="bucket.multiple" class="rounded bg-slate-100 px-1 text-[8px] normal-case">più campi</span>
            </div>
            <div
              class="bucket-drop-zone min-h-[30px] rounded border border-dashed border-pbi-pane-border bg-white p-0.5 transition-colors"
              :class="{ 'border-pbi-accent bg-blue-50/50': dragOverBucket === bucket.key }"
              @dragover.prevent="onDragOver(bucket.key, $event)"
              @dragleave="dragOverBucket = null"
              @drop.prevent="onDrop(bucket.key, $event)"
            >
              <div
                v-for="(field, index) in fieldsFor(bucket.key)"
                :key="`${bucket.key}-${index}-${field.column || field}`"
                class="field-chip mb-0.5 flex cursor-grab items-center gap-1 rounded border border-pbi-pane-border bg-slate-50 px-1 py-0.5 text-[10px] last:mb-0"
                draggable="true"
                @dragstart="onChipDragStart(bucket.key, index, field, $event)"
                @contextmenu.prevent.stop="openFieldMenu(bucket.key, index, field, $event)"
                @click.stop="openFieldMenu(bucket.key, index, field, $event)"
              >
                <span class="shrink-0 text-[9px] text-pbi-accent">{{ fieldIcon(field) }}</span>
                <span class="min-w-0 flex-1 truncate" :title="fieldLabel(field)">{{ fieldLabel(field) }}</span>
                <span v-if="fieldAggregation(field)" class="shrink-0 rounded bg-white px-1 text-[8px] text-pbi-text-muted">{{ fieldAggregation(field) }}</span>
                <button class="shrink-0 rounded px-0.5 text-[10px] text-pbi-text-muted hover:bg-red-100 hover:text-red-600" title="Rimuovi campo" @click.stop="removeField(bucket.key, index)">×</button>
              </div>
              <div v-if="!fieldsFor(bucket.key).length" class="px-1 py-1 text-[9px] italic text-pbi-text-muted">
                Trascina un campo qui
              </div>
            </div>
          </div>

          <div class="mt-2 rounded border border-pbi-pane-border bg-slate-50 p-1.5 text-[9px] text-pbi-text-muted">
            <div class="mb-0.5 font-semibold text-pbi-text">Suggerimento</div>
            Trascina i campi dal pannello Dati oppure trascina direttamente sul canvas per creare un visual.
          </div>
        </template>
      </div>

      <div v-else class="min-h-0 flex-1 overflow-y-auto">
        <nicegui-FormattingPane />
      </div>
    </template>

    <div v-else class="flex flex-1 items-start justify-center pt-3">
      <span class="text-lg" title="Visualizzazioni">📊</span>
    </div>

    <!-- Field context menu -->
    <div
      v-if="fieldMenu.open"
      ref="fieldMenuRef"
      class="fixed z-[110] w-56 rounded border border-pbi-pane-border bg-white py-1 text-pbi-base text-pbi-text shadow-pbi-dropdown"
      :style="{ left: `${fieldMenu.x}px`, top: `${fieldMenu.y}px` }"
      @click.stop
      @mousedown.stop
    >
      <div class="border-b border-pbi-pane-border px-2 py-1 text-[10px] font-semibold uppercase text-pbi-text-muted">Aggregazione</div>
      <button v-for="agg in aggregations" :key="agg.value" class="menu-item" @click="setAggregation(agg.value)">
        <span class="w-3 text-pbi-accent">{{ fieldAggregation(fieldMenu.field) === agg.value ? '✓' : '' }}</span>
        {{ agg.label }}
      </button>
      <div class="border-y border-pbi-pane-border px-2 py-1 text-[10px] font-semibold uppercase text-pbi-text-muted">Mostra valore come</div>
      <button v-for="option in showAsOptions" :key="option.value" class="menu-item" @click="setShowAs(option.value)">
        <span class="w-3 text-pbi-accent">{{ (fieldMenu.field?.show_as || 'none') === option.value ? '✓' : '' }}</span>
        {{ option.label }}
      </button>
      <div class="my-1 border-t border-pbi-pane-border"></div>
      <button class="menu-item" @click="renameField"><span>✏️</span> Rinomina per questo visual</button>
      <button class="menu-item" @click="duplicateField"><span>⧉</span> Duplica campo</button>
      <div class="my-1 border-t border-pbi-pane-border"></div>
      <button class="menu-item text-red-600" @click="removeField(fieldMenu.bucket, fieldMenu.index)"><span>🗑</span> Rimuovi campo</button>
    </div>
  </div>
</template>

<script>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';

export default {
  name: 'VisualizationsPane',
  setup() {
const store = useReportStore();
const tab = ref('fields');
const dragOverBucket = ref(null);
const fieldMenuRef = ref(null);
const fieldMenu = reactive({ open: false, x: 0, y: 0, bucket: '', index: 0, field: null });

const visualTypes = [
  { type: 'bar_chart', label: 'Istogramma a barre', icon: '📊' },
  { type: 'column_chart', label: 'Istogramma a colonne', icon: '📶' },
  { type: 'stacked_bar_chart', label: 'Barre in pila', icon: '📚' },
  { type: 'stacked_column_100', label: 'Colonne 100% in pila', icon: '🧱' },
  { type: 'line_chart', label: 'Grafico a linee', icon: '📈' },
  { type: 'area_chart', label: 'Grafico ad area', icon: '📉' },
  { type: 'combo_chart', label: 'Linee e colonne', icon: '📈' },
  { type: 'pie_chart', label: 'Grafico a torta', icon: '🥧' },
  { type: 'donut_chart', label: 'Grafico ad anello', icon: '🍩' },
  { type: 'treemap', label: 'Treemap', icon: '🟦' },
  { type: 'scatter_chart', label: 'Dispersione', icon: '⚬' },
  { type: 'table', label: 'Tabella', icon: '📋' },
  { type: 'matrix', label: 'Matrice', icon: '🧮' },
  { type: 'card', label: 'Scheda', icon: '🔢' },
  { type: 'multi_row_card', label: 'Scheda a più righe', icon: '🔢' },
  { type: 'kpi', label: 'KPI', icon: '🎯' },
  { type: 'gauge', label: 'Indicatore', icon: '⏱' },
  { type: 'slicer', label: 'Slicer', icon: '🎛' },
  { type: 'text', label: 'Casella di testo', icon: '🔤' },
  { type: 'shape', label: 'Forma', icon: '⬛' },
  { type: 'image', label: 'Immagine', icon: '🖼' },
];

const aggregations = [
  { value: 'SUM', label: 'Somma' },
  { value: 'AVG', label: 'Media' },
  { value: 'MIN', label: 'Minimo' },
  { value: 'MAX', label: 'Massimo' },
  { value: 'COUNT', label: 'Conteggio' },
  { value: 'COUNT DISTINCT', label: 'Conteggio distinto' },
];

const showAsOptions = [
  { value: 'none', label: 'Nessun calcolo' },
  { value: 'percent_grand_total', label: '% del totale complessivo' },
  { value: 'percent_row_total', label: '% del totale di riga' },
  { value: 'percent_column_total', label: '% del totale di colonna' },
];

const currentType = computed(() => store.selectedVisual?.type || null);
const currentLabel = computed(() => visualTypes.find(option => option.type === currentType.value)?.label || 'Nessun visual selezionato');

const buckets = computed(() => {
  const type = currentType.value || 'bar_chart';
  const common = [
    { key: 'x_axis', label: 'Asse X', multiple: false },
    { key: 'y_axis', label: 'Asse Y', multiple: true },
    { key: 'legend', label: 'Legenda', multiple: false },
  ];
  if (type === 'table') return [{ key: 'values', label: 'Valori / Colonne', multiple: true }];
  if (type === 'matrix') {
    return [
      { key: 'rows', label: 'Righe', multiple: true },
      { key: 'columns', label: 'Colonne', multiple: true },
      { key: 'values', label: 'Valori', multiple: true },
    ];
  }
  if (['card', 'multi_row_card', 'kpi', 'gauge'].includes(type)) return [{ key: 'values', label: 'Valori', multiple: true }];
  if (type === 'slicer') return [{ key: 'values', label: 'Campo', multiple: false }];
  if (type === 'combo_chart') {
    return [
      { key: 'x_axis', label: 'Asse X', multiple: false },
      { key: 'y_axis', label: 'Colonne (Y)', multiple: true },
      { key: 'secondary_y_axis', label: 'Linee (Y secondario)', multiple: true },
      { key: 'legend', label: 'Legenda', multiple: false },
    ];
  }
  return common;
});

function fieldsFor(bucket) {
  const value = store.selectedVisual?.data_buckets?.[bucket];
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function fieldLabel(field) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  return field.display_name || field.label || field.name || field.column || '';
}

function fieldIcon(field) {
  if (typeof field === 'string') return 'ABC';
  if (field.kind === 'measure') return '🧮';
  const dataType = String(field.data_type || '').toLowerCase();
  if (dataType.includes('date') || dataType.includes('time')) return '📅';
  if (dataType.includes('bool')) return 'T/F';
  if (dataType.includes('int') || dataType.includes('number') || dataType.includes('float') || dataType.includes('decimal')) return '∑';
  if (field.is_key) return '🔑';
  return 'ABC';
}

function fieldAggregation(field) {
  if (!field || typeof field === 'string') return '';
  if (field.kind !== 'measure' && !field.aggregation) return '';
  return field.aggregation || 'SUM';
}

function setType(type) {
  if (store.selectedVisual) store.setVisualType(store.selectedVisual.id, type);
  else store.addVisual(type);
  tab.value = 'fields';
}

function onDragOver(bucket, event) {
  dragOverBucket.value = bucket;
  event.dataTransfer.dropEffect = 'move';
}

function parseDragField(event) {
  let raw = null;
  try {
    raw = event.dataTransfer.getData('application/x-pybi-field') || event.dataTransfer.getData('application/x-pybi-bucket-field') || event.dataTransfer.getData('text/plain');
  } catch (error) {
    raw = null;
  }
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

function onDrop(bucket, event) {
  dragOverBucket.value = null;
  const payload = parseDragField(event);
  if (!payload || !store.selectedVisual) return;
  if (payload.__bucket && payload.field) {
    if (payload.__bucket === bucket) {
      store.reorderBucketFields(store.selectedVisual.id, bucket, payload.index, payload.dropIndex ?? fieldsFor(bucket).length);
    } else {
      store.removeFieldFromBucket(store.selectedVisual.id, payload.__bucket, payload.index);
      store.addFieldToBucket(store.selectedVisual.id, bucket, payload.field);
    }
    return;
  }
  store.addFieldToBucket(store.selectedVisual.id, bucket, payload);
}

function onChipDragStart(bucket, index, field, event) {
  const payload = { __bucket: bucket, index, field };
  event.dataTransfer.effectAllowed = 'move';
  try {
    event.dataTransfer.setData('application/x-pybi-bucket-field', JSON.stringify(payload));
    event.dataTransfer.setData('text/plain', JSON.stringify(payload.field));
  } catch (error) {
    // Ignore browsers that block custom drag data.
  }
}

function openFieldMenu(bucket, index, field, event) {
  const width = 224;
  const height = 330;
  fieldMenu.bucket = bucket;
  fieldMenu.index = index;
  fieldMenu.field = field;
  fieldMenu.x = Math.min(window.innerWidth - width - 8, Math.max(4, event.clientX - 180));
  fieldMenu.y = Math.min(window.innerHeight - height - 8, Math.max(4, event.clientY));
  fieldMenu.open = true;
}

function closeFieldMenu(event) {
  if (fieldMenuRef.value && !fieldMenuRef.value.contains(event.target)) fieldMenu.open = false;
}

function setAggregation(value) {
  if (!store.selectedVisual) return;
  store.updateBucketField(store.selectedVisual.id, fieldMenu.bucket, fieldMenu.index, { aggregation: value });
  fieldMenu.open = false;
}

function setShowAs(value) {
  if (!store.selectedVisual) return;
  store.updateBucketField(store.selectedVisual.id, fieldMenu.bucket, fieldMenu.index, { show_as: value });
  fieldMenu.open = false;
}

function renameField() {
  if (!store.selectedVisual || !fieldMenu.field) return;
  const current = fieldLabel(fieldMenu.field);
  const value = typeof window === 'undefined' ? current : window.prompt('Nuovo nome per questo visual', current);
  if (value && value.trim()) {
    store.updateBucketField(store.selectedVisual.id, fieldMenu.bucket, fieldMenu.index, { display_name: value.trim() });
  }
  fieldMenu.open = false;
}

function duplicateField() {
  if (!store.selectedVisual || !fieldMenu.field) return;
  store.addFieldToBucket(store.selectedVisual.id, fieldMenu.bucket, { ...fieldMenu.field });
  fieldMenu.open = false;
}

function removeField(bucket, index) {
  if (!store.selectedVisual) return;
  store.removeFieldFromBucket(store.selectedVisual.id, bucket, index);
  fieldMenu.open = false;
}

onMounted(() => document.addEventListener('mousedown', closeFieldMenu));
onBeforeUnmount(() => document.removeEventListener('mousedown', closeFieldMenu));

    return {
      store,
      tab,
      dragOverBucket,
      fieldMenuRef,
      fieldMenu,
      visualTypes,
      aggregations,
      showAsOptions,
      currentType,
      currentLabel,
      buckets,
      fieldsFor,
      fieldLabel,
      fieldIcon,
      fieldAggregation,
      setType,
      onDragOver,
      onDrop,
      onChipDragStart,
      openFieldMenu,
      setAggregation,
      setShowAs,
      renameField,
      duplicateField,
      removeField,
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
.field-chip:hover {
  border-color: #118dff;
  background-color: #eff6fc;
}
</style>
