<template>
  <div class="filters-pane flex h-full min-h-0 w-72 flex-col border-r border-pbi-pane-border bg-pbi-pane text-pbi-text">
    <div class="flex h-9 shrink-0 items-center justify-between border-b border-pbi-pane-border px-2">
      <div class="flex items-center gap-1.5 text-pbi-md font-semibold">
        <span>🔎</span><span>FILTRI</span>
      </div>
      <button class="pbi-btn pbi-btn-ghost" :title="collapsed ? 'Espandi filtri' : 'Comprimi filtri'" @click="collapsed = !collapsed">
        {{ collapsed ? '›' : '‹' }}
      </button>
    </div>

    <div v-if="!collapsed" class="min-h-0 flex-1 overflow-y-auto">
      <!-- Filters on this visual -->
      <section v-if="store.selectedVisual" class="filter-section">
        <button class="filter-section-title" @click="toggleSection('visual')">
          <span>{{ openSections.visual ? '▾' : '▸' }}</span>
          <span>Filtri su questo elemento visivo</span>
          <span class="ml-auto rounded bg-slate-100 px-1 text-[9px]">{{ filtersFor('visual').length }}</span>
        </button>
        <div v-if="openSections.visual" class="p-1.5 pt-0">
          <div class="mb-1 truncate rounded bg-blue-50 px-1.5 py-1 text-[10px] font-semibold text-blue-800">
            {{ store.selectedVisual.title }}
          </div>
          <FilterCard
            v-for="filter in filtersFor('visual')"
            :key="filter.id"
            :filter="filter"
            scope="visual"
            :fields="allFields"
            :options="valueOptions[filter.id] || []"
            :loading="valueLoading[filter.id]"
            :expanded="expanded[filter.id]"
            @toggle-expand="toggleExpanded(filter, 'visual')"
            @update="patch => updateFilter('visual', filter, patch)"
            @remove="store.removeFilter('visual', filter.id, store.primarySelectedId)"
            @reset="store.resetFilter('visual', filter.id, store.primarySelectedId)"
            @lock="store.toggleFilterLock('visual', filter.id, store.primarySelectedId)"
            @hide="store.toggleFilterHidden('visual', filter.id, store.primarySelectedId)"
            @load-options="search => loadOptions(filter, search)"
          />
          <button class="add-filter-btn" @click="addFilter('visual')">＋ Aggiungi filtro</button>
        </div>
      </section>

      <!-- Filters on this page -->
      <section class="filter-section">
        <button class="filter-section-title" @click="toggleSection('page')">
          <span>{{ openSections.page ? '▾' : '▸' }}</span>
          <span>Filtri su questa pagina</span>
          <span class="ml-auto rounded bg-slate-100 px-1 text-[9px]">{{ filtersFor('page').length }}</span>
        </button>
        <div v-if="openSections.page" class="p-1.5 pt-0">
          <FilterCard
            v-for="filter in filtersFor('page')"
            :key="filter.id"
            :filter="filter"
            scope="page"
            :fields="allFields"
            :options="valueOptions[filter.id] || []"
            :loading="valueLoading[filter.id]"
            :expanded="expanded[filter.id]"
            @toggle-expand="toggleExpanded(filter, 'page')"
            @update="patch => updateFilter('page', filter, patch)"
            @remove="store.removeFilter('page', filter.id)"
            @reset="store.resetFilter('page', filter.id)"
            @lock="store.toggleFilterLock('page', filter.id)"
            @hide="store.toggleFilterHidden('page', filter.id)"
            @load-options="search => loadOptions(filter, search)"
          />
          <button class="add-filter-btn" @click="addFilter('page')">＋ Aggiungi filtro</button>
        </div>
      </section>

      <!-- Filters on all pages -->
      <section class="filter-section">
        <button class="filter-section-title" @click="toggleSection('report')">
          <span>{{ openSections.report ? '▾' : '▸' }}</span>
          <span>Filtri su tutte le pagine</span>
          <span class="ml-auto rounded bg-slate-100 px-1 text-[9px]">{{ filtersFor('report').length }}</span>
        </button>
        <div v-if="openSections.report" class="p-1.5 pt-0">
          <FilterCard
            v-for="filter in filtersFor('report')"
            :key="filter.id"
            :filter="filter"
            scope="report"
            :fields="allFields"
            :options="valueOptions[filter.id] || []"
            :loading="valueLoading[filter.id]"
            :expanded="expanded[filter.id]"
            @toggle-expand="toggleExpanded(filter, 'report')"
            @update="patch => updateFilter('report', filter, patch)"
            @remove="store.removeFilter('report', filter.id)"
            @reset="store.resetFilter('report', filter.id)"
            @lock="store.toggleFilterLock('report', filter.id)"
            @hide="store.toggleFilterHidden('report', filter.id)"
            @load-options="search => loadOptions(filter, search)"
          />
          <button class="add-filter-btn" @click="addFilter('report')">＋ Aggiungi filtro</button>
        </div>
      </section>
    </div>

    <div v-else class="flex flex-1 items-start justify-center pt-3">
      <span class="text-lg" title="Filtri">🔎</span>
    </div>
  </div>
</template>

<script>
import { computed, defineComponent, reactive, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';

const OPERATORS = [
  { value: 'eq', label: 'È uguale a' },
  { value: 'neq', label: 'Non è uguale a' },
  { value: 'contains', label: 'Contiene' },
  { value: 'not_contains', label: 'Non contiene' },
  { value: 'starts_with', label: 'Inizia con' },
  { value: 'ends_with', label: 'Termina con' },
  { value: 'gt', label: 'Maggiore di' },
  { value: 'gte', label: 'Maggiore o uguale a' },
  { value: 'lt', label: 'Minore di' },
  { value: 'lte', label: 'Minore o uguale a' },
  { value: 'is_null', label: 'È vuoto' },
  { value: 'is_not_null', label: 'Non è vuoto' },
];

export default defineComponent({
  name: 'FiltersPane',
  components: {
    FilterCard: defineComponent({
      name: 'FilterCard',
      props: {
        filter: { type: Object, required: true },
        scope: { type: String, default: 'page' },
        fields: { type: Array, default: () => [] },
        options: { type: Array, default: () => [] },
        loading: { type: Boolean, default: false },
        expanded: { type: Boolean, default: false },
      },
      emits: ['toggle-expand', 'update', 'remove', 'reset', 'lock', 'hide', 'load-options'],
      setup(props, { emit }) {
        const search = ref('');
        const operators = OPERATORS;
        const fieldValue = computed({
          get() {
            const field = props.filter.field;
            if (!field) return '';
            if (typeof field === 'string') return field;
            return `${field.table || ''}|${field.column || field.name || ''}|${field.kind || 'column'}|${field.aggregation || 'SUM'}`;
          },
          set(value) {
            if (!value) {
              emit('update', { field: null, title: '' });
              return;
            }
            const [table, column, kind, aggregation] = String(value).split('|');
            const source = props.fields.find(field => field.table === table && field.column === column) || {};
            emit('update', {
              field: { ...source, table, column, name: column, kind: kind || source.kind || 'column', aggregation: aggregation || 'SUM' },
              title: source.label || column,
            });
            emit('load-options', '');
          },
        });

        const values = computed(() => props.filter.values || props.filter.value || []);
        const selectedValues = computed(() => (Array.isArray(values.value) ? values.value : values.value ? [values.value] : []));
        const mode = computed(() => String(props.filter.mode || props.filter.type || 'basic').toLowerCase().replace('base', 'basic'));
        const conditions = computed(() => props.filter.conditions || [{ operator: 'eq', value: '' }]);
        const filteredOptions = computed(() => {
          const query = search.value.toLowerCase().trim();
          if (!query) return props.options;
          return props.options.filter(option => String(option).toLowerCase().includes(query));
        });
        const title = computed(() => props.filter.title || props.filter.field?.display_name || props.filter.field?.name || props.filter.field?.column || 'Nuovo filtro');

        function setMode(value) {
          emit('update', { mode: value });
        }

        function toggleValue(value) {
          const current = [...selectedValues.value];
          const index = current.findIndex(item => String(item) === String(value));
          if (index >= 0) current.splice(index, 1);
          else current.push(value);
          emit('update', { values: current, value: current });
        }

        function selectAll() {
          emit('update', { values: props.options.slice(), value: props.options.slice() });
        }

        function clearAll() {
          emit('update', { values: [], value: [] });
        }

        function updateCondition(index, patch) {
          const next = conditions.value.map((condition, idx) => (idx === index ? { ...condition, ...patch } : condition));
          emit('update', { conditions: next });
        }

        function addCondition() {
          emit('update', { conditions: [...conditions.value, { operator: 'eq', value: '', value2: '' }] });
        }

        function removeCondition(index) {
          emit('update', { conditions: conditions.value.filter((_, idx) => idx !== index) });
        }

        function updateTopN(patch) {
          emit('update', patch);
        }

        return {
          search,
          operators,
          fieldValue,
          selectedValues,
          mode,
          conditions,
          filteredOptions,
          title,
          setMode,
          toggleValue,
          selectAll,
          clearAll,
          updateCondition,
          addCondition,
          removeCondition,
          updateTopN,
        };
      },
      template: `
        <div class="mb-1 rounded border border-pbi-pane-border bg-white">
          <div class="filter-card-header flex items-center gap-1 px-1.5 py-1">
            <button class="shrink-0 text-[10px]" @click="$emit('toggle-expand')">{{ expanded ? '▾' : '▸' }}</button>
            <div class="min-w-0 flex-1">
              <div class="truncate text-[11px] font-semibold" :title="title">{{ title }}</div>
              <div class="truncate text-[9px] text-pbi-text-muted">
                {{ filter.is_locked ? '🔒 Bloccato' : 'Modificabile' }}
                <span v-if="filter.is_hidden"> · 👁️‍🗨️ Nascosto</span>
              </div>
            </div>
            <button class="filter-icon-btn" title="Blocca / sblocca" @click="$emit('lock')">{{ filter.is_locked ? '🔒' : '🔓' }}</button>
            <button class="filter-icon-btn" title="Nascondi / mostra" @click="$emit('hide')">{{ filter.is_hidden ? '👁️‍🗨️' : '👁️' }}</button>
            <button class="filter-icon-btn" title="Reset filtro" @click="$emit('reset')">🧹</button>
            <button class="filter-icon-btn text-red-600" title="Elimina filtro" @click="$emit('remove')">✕</button>
          </div>

          <div v-if="expanded" class="border-t border-pbi-pane-border p-1.5">
            <select
              :value="fieldValue"
              class="mb-1.5 w-full rounded border border-pbi-pane-border bg-white px-1 py-1 text-[10px]"
              @change="event => fieldValue = event.target.value"
            >
              <option value="">Seleziona un campo…</option>
              <option v-for="field in fields" :key="field.value" :value="field.value">
                {{ field.label }}
              </option>
            </select>

            <div class="mb-1.5 grid grid-cols-3 gap-0.5 rounded bg-slate-100 p-0.5 text-[9px] font-semibold">
              <button class="rounded px-1 py-0.5" :class="mode === 'basic' ? 'bg-white text-pbi-accent shadow-sm' : 'text-pbi-text-muted'" @click="setMode('basic')">Base</button>
              <button class="rounded px-1 py-0.5" :class="mode === 'advanced' ? 'bg-white text-pbi-accent shadow-sm' : 'text-pbi-text-muted'" @click="setMode('advanced')">Avanzato</button>
              <button class="rounded px-1 py-0.5" :class="mode === 'topn' ? 'bg-white text-pbi-accent shadow-sm' : 'text-pbi-text-muted'" @click="setMode('topn')">Top N</button>
            </div>

            <template v-if="mode === 'basic'">
              <div class="mb-1 flex gap-1">
                <input v-model="search" type="text" placeholder="Cerca valori…" class="min-w-0 flex-1 rounded border border-pbi-pane-border px-1 py-0.5 text-[10px]" @input="$emit('load-options', search)" />
                <button class="filter-icon-btn" title="Seleziona tutto" @click="selectAll">☑</button>
                <button class="filter-icon-btn" title="Deseleziona" @click="clearAll">☐</button>
              </div>
              <div class="max-h-40 overflow-y-auto rounded border border-pbi-pane-border bg-white p-1">
                <div v-if="loading" class="p-1 text-[10px] italic text-pbi-text-muted">Caricamento valori…</div>
                <div v-else-if="!filteredOptions.length" class="p-1 text-[10px] italic text-pbi-text-muted">Nessun valore disponibile.</div>
                <label v-for="option in filteredOptions" :key="String(option)" class="flex items-center gap-1 rounded px-0.5 py-0.5 text-[10px] hover:bg-blue-50">
                  <input type="checkbox" class="h-3 w-3 accent-blue-600" :checked="selectedValues.map(String).includes(String(option))" @change="toggleValue(option)" />
                  <span class="truncate">{{ option }}</span>
                </label>
              </div>
            </template>

            <template v-else-if="mode === 'advanced'">
              <div class="mb-1 flex items-center gap-1 text-[9px]">
                <span>Combina con</span>
                <select :value="filter.logic || 'AND'" class="rounded border border-pbi-pane-border px-1 py-0.5" @change="event => $emit('update', { logic: event.target.value })">
                  <option value="AND">AND</option>
                  <option value="OR">OR</option>
                </select>
              </div>
              <div v-for="(condition, index) in conditions" :key="index" class="mb-1 flex items-center gap-1">
                <select :value="condition.operator || 'eq'" class="w-24 shrink-0 rounded border border-pbi-pane-border px-1 py-0.5 text-[9px]" @change="event => updateCondition(index, { operator: event.target.value })">
                  <option v-for="operator in operators" :key="operator.value" :value="operator.value">{{ operator.label }}</option>
                </select>
                <input :value="condition.value" type="text" class="min-w-0 flex-1 rounded border border-pbi-pane-border px-1 py-0.5 text-[10px]" placeholder="Valore" @input="event => updateCondition(index, { value: event.target.value })" />
                <button class="filter-icon-btn text-red-600" @click="removeCondition(index)">✕</button>
              </div>
              <button class="add-filter-btn" @click="addCondition">＋ Condizione</button>
            </template>

            <template v-else>
              <div class="mb-1 grid grid-cols-2 gap-1">
                <label class="text-[9px]">Mostra
                  <select :value="filter.top_direction || 'top'" class="mt-0.5 w-full rounded border border-pbi-pane-border px-1 py-0.5 text-[10px]" @change="event => updateTopN({ top_direction: event.target.value })">
                    <option value="top">Primi</option>
                    <option value="bottom">Ultimi</option>
                  </select>
                </label>
                <label class="text-[9px]">N
                  <input :value="filter.top_n || 5" type="number" min="1" max="1000" class="mt-0.5 w-full rounded border border-pbi-pane-border px-1 py-0.5 text-[10px]" @input="event => updateTopN({ top_n: Number(event.target.value) })" />
                </label>
              </div>
              <label class="block text-[9px]">Per campo / misura
                <select :value="filter.by?.column || ''" class="mt-0.5 w-full rounded border border-pbi-pane-border px-1 py-0.5 text-[10px]" @change="event => { const source = fields.find(field => field.column === event.target.value); updateTopN({ by: source ? { table: source.table, column: source.column, name: source.column, kind: source.kind, aggregation: source.aggregation } : null }); }">
                  <option value="">Valore</option>
                  <option v-for="field in fields" :key="field.value" :value="field.column">{{ field.label }}</option>
                </select>
              </label>
            </template>
          </div>
        </div>
      `,
    }),
  },
  setup() {
    const store = useReportStore();
    const collapsed = ref(false);
    const openSections = reactive({ visual: true, page: true, report: true });
    const expanded = reactive({});
    const valueOptions = reactive({});
    const valueLoading = reactive({});

    const allFields = computed(() => {
      const result = [];
      (store.tables || []).forEach(table => {
        if (table.is_hidden) return;
        (table.columns || []).forEach(column => {
          if (column.is_hidden) return;
          result.push({
            table: table.name,
            column: column.name,
            name: column.name,
            kind: 'column',
            data_type: column.data_type,
            aggregation: 'SUM',
            label: `${table.name}.${column.name}`,
            value: `${table.name}|${column.name}|column|SUM`,
          });
        });
        (table.measures || []).forEach(measure => {
          if (measure.is_hidden) return;
          result.push({
            table: table.name,
            column: measure.name,
            name: measure.name,
            kind: 'measure',
            data_type: 'number',
            aggregation: measure.agg_func || 'SUM',
            expression: measure.expression,
            label: `${table.name}.${measure.name} ∑`,
            value: `${table.name}|${measure.name}|measure|${measure.agg_func || 'SUM'}`,
          });
        });
      });
      return result;
    });

    function filtersFor(scope) {
      return store.getFilterList(scope, store.primarySelectedId);
    }

    function toggleSection(scope) {
      openSections[scope] = !openSections[scope];
    }

    function toggleExpanded(filter, scope) {
      expanded[filter.id] = !expanded[filter.id];
      if (expanded[filter.id] && String(filter.mode || filter.type || 'basic').replace('base', 'basic') === 'basic' && !valueOptions[filter.id]) {
        loadOptions(filter, '');
      }
    }

    async function loadOptions(filter, search = '') {
      const field = filter.field;
      if (!field) {
        valueOptions[filter.id] = [];
        return;
      }
      const table = typeof field === 'string' ? null : field.table;
      const column = typeof field === 'string' ? field : field.column || field.name;
      if (!table || !column) return;
      valueLoading[filter.id] = true;
      valueOptions[filter.id] = await store.fetchDistinctValues(table, column, search || '');
      valueLoading[filter.id] = false;
    }

    function addFilter(scope) {
      const firstField = allFields.value[0];
      const filter = store.addFilter(scope, {
        field: firstField ? {
          table: firstField.table,
          column: firstField.column,
          name: firstField.column,
          kind: firstField.kind,
          data_type: firstField.data_type,
          aggregation: firstField.aggregation,
        } : null,
        title: firstField ? firstField.label : '',
      }, scope === 'visual' ? store.primarySelectedId : null);
      expanded[filter.id] = true;
      if (firstField) loadOptions(filter, '');
    }

    function updateFilter(scope, filter, patch) {
      store.updateFilter(scope, filter.id, patch, scope === 'visual' ? store.primarySelectedId : null);
      if (patch.field) loadOptions({ ...filter, ...patch }, '');
    }

    return {
      store,
      collapsed,
      openSections,
      expanded,
      valueOptions,
      valueLoading,
      allFields,
      filtersFor,
      toggleSection,
      toggleExpanded,
      loadOptions,
      addFilter,
      updateFilter,
    };
  },
});
</script>

<style scoped>
.filter-section {
  border-bottom: 1px solid #e1dfdd;
}
.filter-section-title {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #252423;
  background: #fafafa;
}
.filter-section-title:hover {
  background: #f3f2f1;
}
.add-filter-btn {
  width: 100%;
  border: 1px dashed #d2d0ce;
  border-radius: 2px;
  padding: 3px 6px;
  text-align: left;
  font-size: 10px;
  color: #0078d4;
  margin-top: 4px;
}
.add-filter-btn:hover {
  background: #eff6fc;
  border-color: #0078d4;
}
.filter-card-header {
  background: #fdfdfd;
}
.filter-card-header:hover {
  background: #f7f7f7;
}
.filter-icon-btn {
  display: inline-flex;
  height: 18px;
  width: 18px;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  font-size: 9px;
}
.filter-icon-btn:hover {
  background: #e1dfdd;
}
</style>
