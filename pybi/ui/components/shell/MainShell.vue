<template>
  <div class="main-shell flex h-full min-h-0 w-full flex-col overflow-hidden bg-[var(--pbi-bg-canvas)] text-pbi-text">
    <!-- Power BI style ribbon -->
    <header class="flex h-11 shrink-0 items-center gap-2 border-b border-pbi-pane-border bg-pbi-ribbon px-2 text-pbi-xs shadow-sm">
      <div class="flex min-w-0 items-center gap-2">
        <span class="flex h-6 w-6 items-center justify-center rounded bg-pbi-accent text-[13px] font-black text-white">P</span>
        <div class="min-w-0">
          <div class="truncate text-[11px] font-bold leading-tight">{{ localeStore.t('shell.reportView') }}</div>
          <div class="truncate text-[9px] leading-tight text-pbi-text-muted">{{ store.projectId }} · {{ store.activePage?.name || localeStore.t('shell.nonePage') }}</div>
        </div>
      </div>

      <span class="mx-1 h-6 w-px bg-pbi-pane-border"></span>

      <div class="flex items-center rounded border border-pbi-pane-border bg-white p-0.5">
        <button
          class="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-semibold"
          :class="store.activeView === 'report' ? 'bg-pbi-accent text-white shadow-sm' : 'text-pbi-text-muted hover:bg-slate-100'"
          @click="store.setActiveView('report')"
        >
          <span>📊</span><span>{{ localeStore.t('shell.report') }}</span>
        </button>
        <button
          class="flex items-center gap-1 rounded px-2 py-1 text-[10px] font-semibold"
          :class="store.activeView === 'data' ? 'bg-pbi-accent text-white shadow-sm' : 'text-pbi-text-muted hover:bg-slate-100'"
          @click="openDataView"
        >
          <span>🧮</span><span>{{ localeStore.t('shell.dataView') }}</span>
        </button>
      </div>

      <span class="mx-1 h-6 w-px bg-pbi-pane-border"></span>

      <div class="flex items-center gap-0.5">
        <button class="ribbon-btn" :title="localeStore.t('shell.save')" :disabled="store.isSaving" @click="save">
          <span>💾</span><span class="hidden xl:inline">{{ localeStore.t(store.isSaving ? 'shell.saving' : 'shell.save') }}</span>
        </button>
        <button class="ribbon-btn" :title="localeStore.t('shell.refresh')" @click="refreshAll">
          <span>⟳</span><span class="hidden xl:inline">{{ localeStore.t('shell.refresh') }}</span>
        </button>
        <button class="ribbon-btn" :title="localeStore.t('shell.addVisual')" @click="addVisual">
          <span>➕</span><span class="hidden xl:inline">{{ localeStore.t('shell.visualizations') }}</span>
        </button>
        <span class="mx-0.5 h-5 w-px bg-pbi-pane-border"></span>
        <button class="ribbon-btn" :class="{ 'bg-blue-100 text-pbi-accent': store.panelOpen.filters }" :title="localeStore.t('shell.filters')" @click="store.togglePanel('filters')">
          <span>🔎</span><span class="hidden 2xl:inline">{{ localeStore.t('shell.filters') }}</span>
        </button>
        <button class="ribbon-btn" :class="{ 'bg-blue-100 text-pbi-accent': store.panelOpen.data }" :title="localeStore.t('shell.fields')" @click="store.togglePanel('data')">
          <span>🗂</span><span class="hidden 2xl:inline">{{ localeStore.t('shell.fields') }}</span>
        </button>
        <button class="ribbon-btn" :class="{ 'bg-blue-100 text-pbi-accent': store.panelOpen.visuals }" :title="localeStore.t('shell.visualizations')" @click="store.togglePanel('visuals')">
          <span>📊</span><span class="hidden 2xl:inline">{{ localeStore.t('shell.visualizations') }}</span>
        </button>
        <button class="ribbon-btn" :class="{ 'bg-blue-100 text-pbi-accent': store.panelStacked }" title="Impila o affianca i pannelli laterali" @click="store.setPanelStacked(!store.panelStacked)">
          <span>☷</span><span class="hidden 2xl:inline">{{ store.panelStacked ? 'Affianca' : 'Impila' }}</span>
        </button>
        <button class="ribbon-btn" :title="localeStore.t('shell.focus')" :disabled="!store.selectedVisual" @click="focusSelected">
          <span>⛶</span><span class="hidden 2xl:inline">{{ localeStore.t('shell.focus') }}</span>
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
          :title="localeStore.t('shell.theme')"
          @change="changeTheme"
        >
          <option v-for="theme in themeStore.availableThemes" :key="theme.key" :value="theme.key">{{ theme.name }}</option>
        </select>

        <button class="ribbon-btn" :title="localeStore.t('shell.home')" @click="goHome">
          <span>🏠</span>
        </button>
      </div>
    </header>

    <div v-if="store.layoutLoading" class="flex flex-1 items-center justify-center gap-2 text-pbi-md text-pbi-text-muted">
      <span class="h-4 w-4 animate-spin rounded-full border-2 border-pbi-accent border-t-transparent"></span>
      {{ localeStore.t('shell.loading') }}
    </div>

    <template v-else>
      <!-- Report View -->
      <div v-if="store.activeView === 'report'" class="report-workspace flex min-h-0 flex-1 flex-col overflow-hidden">
        <div class="flex min-h-0 flex-1 overflow-hidden">
          <aside
            v-if="leftPanels.length"
            class="dock-side"
            :class="{ 'dock-stacked': store.panelStacked }"
            :style="sideDockStyle('left')"
            @dragover.prevent
            @drop.prevent="dropPanel('left', $event)"
          >
            <template v-for="(panel, index) in leftPanels" :key="panel">
              <div class="dock-pane" :style="paneStyle(panel, 'left')">
                <component :is="panelComponents[panel]" class="h-full w-full" />
              </div>
              <div v-if="index < leftPanels.length - 1" class="dock-sash" :class="store.panelStacked ? 'dock-sash-row' : 'dock-sash-column'" @pointerdown.prevent="startDockResize($event, 'left', index)"></div>
            </template>
          </aside>

          <main class="min-w-0 min-h-0 flex-1" @dragover.prevent @drop.prevent="dropPanel('right', $event)">
            <nicegui-ReportCanvas :project-id="store.projectId" class="h-full w-full" />
          </main>

          <aside
            v-if="rightPanels.length"
            class="dock-side"
            :class="{ 'dock-stacked': store.panelStacked }"
            :style="sideDockStyle('right')"
            @dragover.prevent
            @drop.prevent="dropPanel('right', $event)"
          >
            <template v-for="(panel, index) in rightPanels" :key="panel">
              <div class="dock-pane" :style="paneStyle(panel, 'right')">
                <component :is="panelComponents[panel]" class="h-full w-full" />
              </div>
              <div v-if="index < rightPanels.length - 1" class="dock-sash" :class="store.panelStacked ? 'dock-sash-row' : 'dock-sash-column'" @pointerdown.prevent="startDockResize($event, 'right', index)"></div>
            </template>
          </aside>
        </div>

        <template v-if="bottomPanels.length">
          <div class="bottom-dock-sash" title="Trascina per ridimensionare i pannelli inferiori" @pointerdown.prevent="startBottomResize"></div>
          <aside
            class="dock-bottom"
            :style="{ height: `${store.panelBottomHeight}px` }"
            @dragover.prevent
            @drop.prevent="dropPanel('bottom', $event)"
          >
            <template v-for="(panel, index) in bottomPanels" :key="panel">
              <div class="dock-pane" :style="paneStyle(panel, 'bottom')">
                <component :is="panelComponents[panel]" class="h-full w-full" />
              </div>
              <div v-if="index < bottomPanels.length - 1" class="dock-sash dock-sash-column" @pointerdown.prevent="startDockResize($event, 'bottom', index)"></div>
            </template>
          </aside>
        </template>
      </div>

      <!-- Data View -->
      <div v-else class="flex min-h-0 flex-1 overflow-hidden">
        <nicegui-DataPane class="h-full w-72 shrink-0" />
        <nicegui-DataTableView class="h-full min-w-0 flex-1" />
      </div>
    </template>

    <footer class="flex h-6 shrink-0 items-center gap-3 border-t border-pbi-pane-border bg-pbi-ribbon px-2 text-[9px] text-pbi-text-muted">
      <span class="font-semibold text-pbi-text">{{ localeStore.t(store.activeView === 'report' ? 'shell.report' : 'shell.dataView') }}</span>
      <span v-if="store.activeView === 'report'">{{ store.pageCount }} {{ localeStore.t('shell.pages') }} · {{ visualCount }} {{ localeStore.t('shell.visuals') }}</span>
      <span v-else>{{ store.tables.length }} {{ localeStore.t('shell.tables') }} · {{ store.activeDataTable || '—' }}</span>
      <span class="ml-auto">{{ localeStore.t('shell.zoom') }} {{ Math.round(store.zoom * 100) }}%</span>
      <span>{{ saveStatus }}</span>
      <nicegui-LanguageSelector />
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
import { computed, onBeforeUnmount, onMounted, watch } from 'vue';
import { useReportStore } from 'pybi-report-store';
import { useThemeStore } from 'pybi-theme-store';
import { useLocaleStore } from 'pybi-locale-store';

export default {
  name: 'MainShell',
  props: {
    projectId: { type: String, default: 'default' },
  },
  setup(props) {
const store = useReportStore();
const themeStore = useThemeStore();
const localeStore = useLocaleStore();

const visualCount = computed(() => store.activePage?.visuals?.length || 0);
const recentMessages = computed(() => store.messages.slice(-4));
const panelComponents = {
  filters: 'nicegui-FiltersPane',
  data: 'nicegui-DataPane',
  visuals: 'nicegui-VisualizationsPane',
};
const panelIds = ['filters', 'data', 'visuals'];
const leftPanels = computed(() => panelIds.filter(panel => store.panelOpen[panel] && store.panelDock[panel] === 'left'));
const rightPanels = computed(() => panelIds.filter(panel => store.panelOpen[panel] && store.panelDock[panel] === 'right'));
const bottomPanels = computed(() => panelIds.filter(panel => store.panelOpen[panel] && store.panelDock[panel] === 'bottom'));
const saveStatus = computed(() => {
  if (store.isSaving) return localeStore.t('shell.saving');
  if (store.isDirty) return localeStore.t('shell.unsaved');
  if (store.lastSavedAt) {
    const locale = localeStore.currentLocale === 'it' ? 'it-IT' : 'en-GB';
    return localeStore.t('shell.saved', { time: new Date(store.lastSavedAt).toLocaleTimeString(locale) });
  }
  return localeStore.t('shell.ready');
});

function paneSize(panel, dimension) {
  return store.panelSizes[panel]?.[dimension] || 288;
}

function paneStyle(panel, dock) {
  if (dock !== 'bottom' && store.panelStacked) {
    const height = paneSize(panel, 'height');
    return { width: '100%', height: `${height}px`, flex: `1 1 ${height}px`, minHeight: '180px' };
  }
  const width = paneSize(panel, 'width');
  return { width: `${width}px`, flex: `0 1 ${width}px`, minWidth: '180px' };
}

function sideDockStyle(dock) {
  const panels = dock === 'left' ? leftPanels.value : rightPanels.value;
  const width = store.panelStacked
    ? Math.max(...panels.map(panel => paneSize(panel, 'width')))
    : panels.reduce((total, panel) => total + paneSize(panel, 'width'), 0) + Math.max(0, panels.length - 1) * 6;
  return { width: `${width}px`, flex: `0 1 ${width}px`, maxWidth: '42vw' };
}

function dropPanel(dock, event) {
  const panel = event.dataTransfer?.getData('application/x-pybi-pane');
  if (panel) store.setPanelDock(panel, dock);
}

let resizeState = null;
function startDockResize(event, dock, index) {
  const panels = dock === 'left' ? leftPanels.value : dock === 'right' ? rightPanels.value : bottomPanels.value;
  if (!panels[index + 1]) return;
  const stacked = dock !== 'bottom' && store.panelStacked;
  const dimension = stacked ? 'height' : 'width';
  resizeState = {
    dock,
    dimension,
    first: panels[index],
    second: panels[index + 1],
    start: dimension === 'width' ? event.clientX : event.clientY,
    firstSize: paneSize(panels[index], dimension),
    secondSize: paneSize(panels[index + 1], dimension),
  };
  window.addEventListener('pointermove', onDockResize);
  window.addEventListener('pointerup', stopDockResize, { once: true });
}

function onDockResize(event) {
  if (!resizeState) return;
  if (resizeState.mode === 'bottom-height') {
    store.setPanelBottomHeight(Math.min(window.innerHeight * 0.65, Math.max(160, resizeState.startHeight + resizeState.start - event.clientY)));
    return;
  }
  const delta = (resizeState.dimension === 'width' ? event.clientX : event.clientY) - resizeState.start;
  const next = Math.max(180, resizeState.firstSize + delta);
  const adjustedDelta = next - resizeState.firstSize;
  const other = Math.max(180, resizeState.secondSize - adjustedDelta);
  store.setPanelSize(resizeState.first, resizeState.dimension, next);
  store.setPanelSize(resizeState.second, resizeState.dimension, other);
}

function stopDockResize() {
  window.removeEventListener('pointermove', onDockResize);
  resizeState = null;
}

function startBottomResize(event) {
  resizeState = {
    mode: 'bottom-height',
    start: event.clientY,
    startHeight: store.panelBottomHeight,
  };
  window.addEventListener('pointermove', onDockResize);
  window.addEventListener('pointerup', stopDockResize, { once: true });
}

let persistTimeout = null;
watch(
  () => [store.panelDock, store.panelSizes, store.panelStacked, store.panelBottomHeight],
  () => {
    clearTimeout(persistTimeout);
    persistTimeout = setTimeout(() => {
      try {
        window.localStorage.setItem('pybi-report-panel-layout', JSON.stringify({
          panelDock: store.panelDock,
          panelSizes: store.panelSizes,
          panelStacked: store.panelStacked,
          panelBottomHeight: store.panelBottomHeight,
        }));
      } catch (error) {
        store.notify(`Impossibile salvare le preferenze dei pannelli: ${error.message}`, 'warning');
      }
    }, 250);
  },
  { deep: true },
);

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
    store.notify(`${localeStore.t('shell.save')}: ${error.message}`, 'error');
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
    store.notify(localeStore.t('shell.addVisual'), 'info');
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
  store.loadPanelPreferences();
  themeStore.initialize();
  const localeLoad = localeStore.initialize();
  let dataLoad;
  if (store.projectId !== props.projectId || !store.layout.pages?.length) {
    dataLoad = store.fetchLayout(props.projectId);
  } else {
    dataLoad = store.fetchTables();
  }
  await Promise.all([localeLoad, dataLoad]);
  themeStore.applyFromLayout(store.layout.theme);
});

onBeforeUnmount(() => {
  clearTimeout(persistTimeout);
  window.removeEventListener('pointermove', onDockResize);
  stopDockResize();
});

    return {
      store,
      themeStore,
      localeStore,
      visualCount,
      recentMessages,
      panelComponents,
      leftPanels,
      rightPanels,
      bottomPanels,
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
      paneStyle,
      sideDockStyle,
      dropPanel,
      startDockResize,
      startBottomResize,
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
.dock-side {
  display: flex;
  min-width: 180px;
  max-width: 42vw;
  min-height: 0;
  overflow: hidden;
}
.dock-side.dock-stacked {
  flex-direction: column;
}
.dock-pane {
  display: flex;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.dock-sash,
.bottom-dock-sash {
  flex: 0 0 6px;
  background: #f3f2f1;
  touch-action: none;
}
.dock-sash:hover,
.bottom-dock-sash:hover {
  background: #118dff;
}
.dock-sash-column {
  cursor: col-resize;
}
.dock-sash-row {
  cursor: row-resize;
}
.bottom-dock-sash {
  cursor: row-resize;
}
.dock-bottom {
  display: flex;
  flex: 0 0 auto;
  min-height: 160px;
  max-height: 65vh;
  overflow: auto hidden;
  border-top: 1px solid #d2d0ce;
  background: white;
}
</style>
