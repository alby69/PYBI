<template>
  <div class="main-shell flex h-full min-h-0 w-full flex-col overflow-hidden bg-[var(--pbi-bg-canvas)] text-pbi-text">
    <!-- Power BI style ribbon -->
    <header class="flex h-11 shrink-0 items-center gap-2 border-b border-pbi-pane-border bg-pbi-ribbon px-2 text-pbi-xs shadow-sm">
      <div class="flex min-w-0 items-center gap-2">
        <span class="flex h-6 w-6 items-center justify-center rounded bg-pbi-accent text-[13px] font-black text-white">P</span>
        <div class="min-w-0">
          <div class="truncate text-[11px] font-bold leading-tight">Report View</div>
          <div class="truncate text-[9px] leading-tight text-pbi-text-muted">{{ store.projectId }} · {{ store.activePage?.name || 'Nessuna pagina' }}</div>
        </div>
      </div>

      <span class="mx-1 h-6 w-px bg-pbi-pane-border"></span>

      <div class="flex items-center rounded border border-pbi-pane-border bg-white p-0.5">
        <button
          class="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-semibold"
          :class="store.activeView === 'report' ? 'bg-pbi-accent text-white shadow-sm' : 'text-pbi-text-muted hover:bg-slate-100'"
          @click="store.setActiveView('report')"
        >
          <span>📊</span><span>Report</span>
        </button>
        <button
          class="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-semibold"
          :class="store.activeView === 'data' ? 'bg-pbi-accent text-white shadow-sm' : 'text-pbi-text-muted hover:bg-slate-100'"
          @click="openDataView"
        >
          <span>🧮</span><span>Dati</span>
        </button>
      </div>

      <span class="mx-1 h-6 w-px bg-pbi-pane-border"></span>

      <div class="flex items-center gap-0.5">
        <button class="ribbon-btn" title="Salva report (Ctrl+S)" :disabled="store.isSaving" @click="save">
          <span>💾</span><span class="hidden xl:inline">{{ store.isSaving ? 'Salvataggio…' : 'Salva' }}</span>
        </button>
        <button class="ribbon-btn" title="Aggiorna tutti i visual" @click="refreshAll">
          <span>⟳</span><span class="hidden xl:inline">Aggiorna</span>
        </button>
        <button class="ribbon-btn" title="Aggiungi un visual" @click="addVisual">
          <span>➕</span><span class="hidden xl:inline">Visual</span>
        </button>
        <span class="mx-0.5 h-5 w-px bg-pbi-pane-border"></span>
        <button class="ribbon-btn" :class="{ 'bg-blue-100 text-pbi-accent': store.panelOpen.filters }" title="Mostra/nascondi filtri" @click="store.togglePanel('filters')">
          <span>🔎</span><span class="hidden 2xl:inline">Filtri</span>
        </button>
        <button class="ribbon-btn" :class="{ 'bg-blue-100 text-pbi-accent': store.panelOpen.data }" title="Mostra/nascondi campi dati" @click="store.togglePanel('data')">
          <span>🗂</span><span class="hidden 2xl:inline">Campi</span>
        </button>
        <button class="ribbon-btn" :class="{ 'bg-blue-100 text-pbi-accent': store.panelOpen.visuals }" title="Mostra/nascondi visualizzazioni" @click="store.togglePanel('visuals')">
          <span>📊</span><span class="hidden 2xl:inline">Visual</span>
        </button>
        <button class="ribbon-btn" title="Modalità focus" :disabled="!store.selectedVisual" @click="focusSelected">
          <span>⛶</span><span class="hidden 2xl:inline">Focus</span>
        </button>
      </div>

      <div class="ml-auto flex items-center gap-2">
        <div class="hidden items-center gap-1 text-[9px] text-pbi-text-muted sm:flex">
          <span
            class="h-1.5 w-1.5 rounded-full"
            :class="store.isDirty ? 'bg-amber-500' : store.isSaving ? 'bg-blue-500 animate-pulse' : 'bg-emerald-500'"
          ></span>
          <span>{{ saveStatus }}</span>
        </div>

        <select
          :value="themeStore.theme"
          class="rounded border border-pbi-pane-border bg-white px-1.5 py-1 text-[10px]"
          title="Tema del report"
          @change="changeTheme"
        >
          <option v-for="theme in themeStore.availableThemes" :key="theme.key" :value="theme.key">{{ theme.name }}</option>
        </select>

        <button class="ribbon-btn" title="Torna alla Home" @click="goHome">
          <span>🏠</span>
        </button>
      </div>
    </header>

    <div v-if="store.layoutLoading" class="flex flex-1 items-center justify-center gap-2 text-pbi-md text-pbi-text-muted">
      <span class="h-4 w-4 animate-spin rounded-full border-2 border-pbi-accent border-t-transparent"></span>
      Caricamento report…
    </div>

    <template v-else>
      <!-- Report View -->
      <div v-if="store.activeView === 'report'" class="flex min-h-0 flex-1 overflow-hidden">
        <div v-if="store.panelOpen.filters" class="h-full shrink-0">
          <nicegui-FiltersPane />
        </div>
        <div v-if="store.panelOpen.data" class="h-full shrink-0">
          <nicegui-DataPane />
        </div>

        <div class="min-w-0 flex-1">
          <nicegui-ReportCanvas :project-id="store.projectId" class="h-full w-full" />
        </div>

        <div v-if="store.panelOpen.visuals" class="h-full shrink-0">
          <nicegui-VisualizationsPane />
        </div>
      </div>

      <!-- Data View -->
      <div v-else class="flex min-h-0 flex-1 overflow-hidden">
        <nicegui-DataPane class="h-full" />
        <nicegui-DataTableView class="h-full min-w-0 flex-1" />
      </div>
    </template>

    <footer class="flex h-6 shrink-0 items-center gap-3 border-t border-pbi-pane-border bg-pbi-ribbon px-2 text-[9px] text-pbi-text-muted">
      <span class="font-semibold text-pbi-text">{{ store.activeView === 'report' ? 'Report' : 'Dati' }}</span>
      <span v-if="store.activeView === 'report'">{{ store.pageCount }} pagine · {{ visualCount }} visual</span>
      <span v-else>{{ store.tables.length }} tabelle · {{ store.activeDataTable || '—' }}</span>
      <span class="ml-auto">Zoom {{ Math.round(store.zoom * 100) }}%</span>
      <span>{{ saveStatus }}</span>
    </footer>

    <div v-if="store.messages.length" class="pointer-events-none fixed bottom-12 right-3 z-[180] flex w-72 flex-col gap-1">
      <div
        v-for="message in recentMessages"
        :key="message.id"
        class="pointer-events-auto rounded border px-2 py-1.5 text-[10px] shadow-pbi-card"
        :class="messageClass(message.level)"
      >
        <span class="mr-1">{{ messageIcon(message.level) }}</span>{{ message.message }}
      </div>
    </div>
  </div>
</template>

<script>
import { computed, onMounted } from 'vue';
import { useReportStore } from 'pybi-report-store';
import { useThemeStore } from 'pybi-theme-store';

export default {
  name: 'MainShell',
  props: {
    projectId: { type: String, default: 'default' },
  },
  setup(props) {
const store = useReportStore();
const themeStore = useThemeStore();

const visualCount = computed(() => store.activePage?.visuals?.length || 0);
const recentMessages = computed(() => store.messages.slice(-4));
const saveStatus = computed(() => {
  if (store.isSaving) return 'Salvataggio…';
  if (store.isDirty) return 'Modifiche non salvate';
  if (store.lastSavedAt) return `Salvato ${new Date(store.lastSavedAt).toLocaleTimeString('it-IT')}`;
  return 'Pronto';
});

function messageClass(level) {
  if (level === 'error') return 'border-red-200 bg-red-50 text-red-800';
  if (level === 'warning') return 'border-amber-200 bg-amber-50 text-amber-900';
  if (level === 'success') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  return 'border-blue-200 bg-blue-50 text-blue-900';
}

function messageIcon(level) {
  if (level === 'error') return '⚠';
  if (level === 'warning') return '⚠';
  if (level === 'success') return '✓';
  return 'ℹ';
}

async function save() {
  try {
    await store.saveLayout();
  } catch (error) {
    store.notify(`Salvataggio non riuscito: ${error.message}`, 'error');
  }
}

function refreshAll() {
  store.fetchTables();
  store.fetchAllVisualData();
  if (store.activeView === 'data') store.fetchTableData({ table: store.activeDataTable });
}

function addVisual() {
  store.setActiveView('report');
  const visual = store.addVisual('bar_chart');
  if (visual) {
    store.notify('Nuovo visual aggiunto al canvas', 'info');
    store.setActivePanel('visuals');
  }
}

function focusSelected() {
  if (store.selectedVisual) store.setFocusedVisual(store.selectedVisual.id);
}

function openDataView() {
  store.setActiveView('data');
  if (!store.activeDataTable && store.tables.length) store.setActiveDataTable(store.tables[0].name);
}

function changeTheme(event) {
  const key = event.target.value;
  themeStore.applyTheme(key);
  store.layout.theme = themeStore.currentTheme.layoutTheme;
  store.markDirty();
}

function goHome() {
  if (typeof window !== 'undefined') window.location.href = '/';
}

onMounted(async () => {
  themeStore.initialize();
  if (store.projectId !== props.projectId || !store.layout.pages?.length) {
    await store.fetchLayout(props.projectId);
  } else {
    await store.fetchTables();
  }
  themeStore.applyFromLayout(store.layout.theme);
});

    return {
      store,
      themeStore,
      visualCount,
      recentMessages,
      saveStatus,
      messageClass,
      messageIcon,
      save,
      refreshAll,
      addVisual,
      focusSelected,
      openDataView,
      changeTheme,
      goHome,
    };
  },
};
</script>

<style scoped>
.ribbon-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 3px;
  padding: 3px 6px;
  font-size: 10px;
  color: #252423;
  white-space: nowrap;
}
.ribbon-btn:hover {
  background: #e1dfdd;
}
.ribbon-btn:disabled {
  opacity: 0.4;
}
</style>
