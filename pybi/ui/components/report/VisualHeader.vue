<template>
  <div
    class="visual-header group/header absolute left-0 right-0 top-0 z-30 flex h-7 items-center gap-1 border-b border-transparent bg-white/95 px-1.5 text-pbi-sm backdrop-blur transition-all"
    :class="[
      selected || hovered ? 'border-pbi-pane-border opacity-100' : 'opacity-0',
      selected ? 'bg-blue-50/95' : ''
    ]"
    @mousedown.stop
    @dblclick.stop="startTitleEdit"
  >
    <input
      v-if="editingTitle"
      ref="titleInput"
      v-model="titleDraft"
      class="min-w-0 flex-1 rounded border border-pbi-accent px-1 py-0.5 text-pbi-sm font-semibold outline-none"
      @keydown.enter.prevent="commitTitle"
      @keydown.esc.prevent="cancelTitle"
      @blur="commitTitle"
      @mousedown.stop
    />
    <div v-else class="min-w-0 flex-1 truncate font-semibold text-pbi-text" :title="visual.title">
      {{ visual.title || store.visualLabel(visual.type) }}
    </div>

    <div class="flex shrink-0 items-center gap-0.5">
      <button
        class="visual-header-btn"
        title="Focus mode"
        @click.stop="$emit('focus', visual.id)"
      >🔍</button>

      <div class="relative">
        <button
          class="visual-header-btn"
          :class="{ 'bg-blue-100 text-blue-700': appliedFilters.length }"
          title="Filtri applicati"
          @mouseenter="showFilters = true"
          @mouseleave="showFilters = false"
          @click.stop="showFilters = !showFilters"
        >🧹</button>
        <div
          v-if="showFilters"
          class="absolute right-0 top-7 z-50 w-72 rounded border border-pbi-pane-border bg-white p-2 text-pbi-xs text-pbi-text shadow-pbi-dropdown"
          @mouseenter="showFilters = true"
          @mouseleave="showFilters = false"
        >
          <div class="mb-1 flex items-center justify-between border-b border-pbi-pane-border pb-1 font-semibold">
            <span>Filtri applicati</span>
            <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px]">{{ appliedFilters.length }}</span>
          </div>
          <div v-if="!appliedFilters.length" class="italic text-pbi-text-muted">Nessun filtro attivo su questo visual.</div>
          <div v-for="filter in appliedFilters" :key="filter.key" class="mb-1 rounded bg-slate-50 px-1.5 py-1">
            <div class="flex items-center justify-between gap-2">
              <span class="font-semibold">{{ filter.title }}</span>
              <span class="rounded bg-white px-1 text-[9px] uppercase text-pbi-text-muted">{{ filter.scope }}</span>
            </div>
            <div class="truncate text-pbi-text-muted">{{ filter.description }}</div>
          </div>
        </div>
      </div>

      <div class="relative">
        <button class="visual-header-btn" title="Altre opzioni" @click.stop="toggleMenu">⋯</button>
        <div
          v-if="menuOpen"
          ref="menuRef"
          class="absolute right-0 top-7 z-50 w-56 rounded border border-pbi-pane-border bg-white py-1 text-pbi-base text-pbi-text shadow-pbi-dropdown"
          @mousedown.stop
        >
          <div class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-pbi-text-muted">Esporta dati</div>
          <button class="visual-menu-item" @click="exportData('csv')"><span>📄</span> Esporta CSV</button>
          <button class="visual-menu-item" @click="exportData('xlsx')"><span>📊</span> Esporta XLSX</button>
          <div class="my-1 border-t border-pbi-pane-border"></div>
          <button class="visual-menu-item" @click="seeData"><span>🔎</span> Mostra come tabella</button>
          <div class="relative">
            <button class="visual-menu-item w-full" @click.stop="sortOpen = !sortOpen">
              <span>↕</span> Ordina per
              <span class="ml-auto text-[9px]">{{ sortOpen ? '▲' : '▼' }}</span>
            </button>
            <div v-if="sortOpen" class="border-y border-pbi-pane-border bg-slate-50 py-1">
              <button
                v-for="field in sortableFields"
                :key="field.column"
                class="visual-menu-item pl-5"
                @click="applySort(field, 'ASC')"
              >
                <span class="text-[10px]">A-Z</span> {{ field.display_name || field.column }}
              </button>
              <button
                v-for="field in sortableFields"
                :key="`${field.column}-desc`"
                class="visual-menu-item pl-5"
                @click="applySort(field, 'DESC')"
              >
                <span class="text-[10px]">Z-A</span> {{ field.display_name || field.column }}
              </button>
              <div v-if="!sortableFields.length" class="px-3 py-1 italic text-pbi-text-muted">Nessun campo ordinabile</div>
            </div>
          </div>
          <div class="my-1 border-t border-pbi-pane-border"></div>
          <button class="visual-menu-item" @click="focusVisual"><span>🔍</span> Focus mode</button>
          <button class="visual-menu-item" @click="duplicateVisual"><span>⧉</span> Duplica visual</button>
          <button class="visual-menu-item" @click="bringToFront"><span>⬆</span> Porta in primo piano</button>
          <button class="visual-menu-item" @click="sendToBack"><span>⬇</span> Porta in fondo</button>
          <div class="my-1 border-t border-pbi-pane-border"></div>
          <button class="visual-menu-item text-red-600" @click="removeVisual"><span>🗑</span> Rimuovi / Elimina</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';

export default {
  name: 'VisualHeader',
  props: {
    visual: { type: Object, required: true },
    selected: { type: Boolean, default: false },
    hovered: { type: Boolean, default: false },
  },
  emits: ['focus', 'see-data', 'delete', 'export', 'sort'],
  setup(props, { emit }) {
const store = useReportStore();
const menuOpen = ref(false);
const sortOpen = ref(false);
const showFilters = ref(false);
const editingTitle = ref(false);
const titleDraft = ref('');
const titleInput = ref(null);
const menuRef = ref(null);

const sortableFields = computed(() => {
  const buckets = props.visual.data_buckets || {};
  const fields = [];
  Object.values(buckets).forEach(value => {
    const list = Array.isArray(value) ? value : value ? [value] : [];
    list.forEach(field => {
      const column = typeof field === 'string' ? field : field.column || field.name;
      if (column && !fields.some(item => item.column === column)) {
        fields.push(typeof field === 'string' ? { column, display_name: column } : field);
      }
    });
  });
  return fields;
});

const appliedFilters = computed(() => {
  const result = [];
  const addFilters = (filters, scope) => {
    (filters || []).forEach((filter, index) => {
      result.push({
        key: `${scope}-${filter.id || index}`,
        scope,
        title: filter.title || fieldLabel(filter.field) || `Filtro ${index + 1}`,
        description: describeFilter(filter),
      });
    });
  };
  addFilters(props.visual.filters || [], 'Visual');
  addFilters(store.activePage?.page_filters || [], 'Pagina');
  addFilters(store.layout.report_filters || [], 'Report');
  addFilters(store.crossFilters || [], 'Incrociato');
  return result;
});

function fieldLabel(field) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  return field.display_name || field.label || field.name || field.column || '';
}

function describeFilter(filter) {
  if (!filter) return '';
  const mode = String(filter.mode || filter.type || 'basic').toLowerCase();
  if (mode === 'advanced') {
    const conditions = (filter.conditions || [])
      .filter(condition => condition.value !== '' && condition.value !== null && condition.value !== undefined)
      .map(condition => `${condition.operator || '='} ${condition.value}`);
    return conditions.join(` ${filter.logic || 'AND'} `) || 'Nessuna condizione';
  }
  if (mode === 'topn') {
    return `Top ${filter.top_n || 5} per ${fieldLabel(filter.by) || 'valore'}`;
  }
  const values = filter.values || filter.value || [];
  if (Array.isArray(values)) return values.length ? values.join(', ') : 'Tutti';
  return String(values || 'Tutti');
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
  if (!menuOpen.value) sortOpen.value = false;
}

function closeMenu(event) {
  if (menuRef.value && !menuRef.value.contains(event.target)) {
    menuOpen.value = false;
    sortOpen.value = false;
  }
}

function focusVisual() {
  menuOpen.value = false;
  emit('focus', props.visual.id);
  store.setFocusedVisual(props.visual.id);
}

function seeData() {
  menuOpen.value = false;
  emit('see-data', props.visual.id);
  store.setSeeDataVisual(props.visual.id);
}

function exportData(format) {
  menuOpen.value = false;
  emit('export', { id: props.visual.id, format });
  store.exportVisualData(props.visual, format);
}

function applySort(field, direction) {
  menuOpen.value = false;
  store.setSort(props.visual.id, field.column, direction);
  emit('sort', { id: props.visual.id, by: field.column, direction });
}

function duplicateVisual() {
  menuOpen.value = false;
  store.duplicateVisual(props.visual.id);
}

function bringToFront() {
  menuOpen.value = false;
  store.bringToFront(props.visual.id);
}

function sendToBack() {
  menuOpen.value = false;
  store.sendToBack(props.visual.id);
}

function removeVisual() {
  menuOpen.value = false;
  emit('delete', props.visual.id);
  store.removeVisual(props.visual.id);
}

function startTitleEdit() {
  titleDraft.value = props.visual.title || '';
  editingTitle.value = true;
  nextTick(() => titleInput.value?.focus());
}

function commitTitle() {
  if (!editingTitle.value) return;
  const title = titleDraft.value.trim();
  if (title) {
    props.visual.title = title;
    store.updateVisualProperties(props.visual.id, { title });
  }
  editingTitle.value = false;
}

function cancelTitle() {
  editingTitle.value = false;
}

onMounted(() => document.addEventListener('mousedown', closeMenu));
onBeforeUnmount(() => document.removeEventListener('mousedown', closeMenu));

    return {
      store,
      menuOpen,
      sortOpen,
      showFilters,
      editingTitle,
      titleDraft,
      titleInput,
      menuRef,
      sortableFields,
      appliedFilters,
      fieldLabel,
      toggleMenu,
      focusVisual,
      seeData,
      exportData,
      applySort,
      duplicateVisual,
      bringToFront,
      sendToBack,
      removeVisual,
      startTitleEdit,
      commitTitle,
      cancelTitle,
    };
  },
};
</script>

<style scoped>
.visual-header-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 2px;
  font-size: 12px;
  line-height: 1;
  color: #605e5c;
  transition: background-color 0.15s ease;
}
.visual-header-btn:hover {
  background-color: #e1dfdd;
  color: #252423;
}
.visual-menu-item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 4px 8px;
  text-align: left;
  font-size: 11px;
  white-space: nowrap;
}
.visual-menu-item:hover {
  background-color: #f3f2f1;
}
</style>
