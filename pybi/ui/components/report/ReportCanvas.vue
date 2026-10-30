<template>
  <div class="report-canvas-root relative flex h-full min-h-0 w-full flex-col overflow-hidden bg-[var(--pbi-bg-canvas)]">
    <!-- Canvas command strip -->
    <div class="flex h-8 shrink-0 items-center gap-2 border-b border-pbi-pane-border bg-white/90 px-2 text-pbi-xs text-pbi-text">
      <span class="font-semibold">{{ store.activePage?.name || 'Pagina' }}</span>
      <span class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-pbi-text-muted">{{ store.pageSizeLabel }}</span>
      <span v-if="store.activePage?.is_hidden" class="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-800">👁️‍🗨️ Nascosta</span>

      <div class="relative">
        <button class="pbi-btn pbi-btn-ghost" @click="addMenuOpen = !addMenuOpen">➕ Aggiungi visual</button>
        <div
          v-if="addMenuOpen"
          class="absolute left-0 top-7 z-50 grid w-64 grid-cols-2 gap-1 rounded border border-pbi-pane-border bg-white p-2 shadow-pbi-dropdown"
        >
          <button
            v-for="option in visualOptions"
            :key="option.type"
            class="flex items-center gap-1.5 rounded px-2 py-1 text-left text-pbi-xs hover:bg-blue-50"
            @click="addVisual(option.type)"
          >
            <span>{{ option.icon }}</span><span class="truncate">{{ option.label }}</span>
          </button>
        </div>
      </div>

      <span class="mx-1 h-4 w-px bg-pbi-pane-border"></span>

      <label class="flex items-center gap-1">
        <input v-model="store.snapToGrid" type="checkbox" class="h-3 w-3 accent-blue-600" />
        Snap
      </label>
      <select v-model.number="store.gridSize" class="rounded border border-pbi-pane-border bg-white px-1 py-0.5 text-[10px]">
        <option :value="4">Griglia 4px</option>
        <option :value="8">Griglia 8px</option>
        <option :value="10">Griglia 10px</option>
        <option :value="20">Griglia 20px</option>
      </select>
      <label class="flex items-center gap-1">
        <input v-model="store.showSmartGuides" type="checkbox" class="h-3 w-3 accent-blue-600" />
        Guide smart
      </label>

      <div class="ml-auto flex items-center gap-1">
        <button class="pbi-btn pbi-btn-ghost" title="Aggiorna dati" @click="store.fetchAllVisualData()">⟳</button>
        <button class="pbi-btn pbi-btn-ghost" title="Zoom indietro" @click="store.zoomOut()">−</button>
        <span class="w-10 text-center font-mono">{{ Math.round(store.zoom * 100) }}%</span>
        <button class="pbi-btn pbi-btn-ghost" title="Zoom avanti" @click="store.zoomIn()">＋</button>
        <button class="pbi-btn pbi-btn-ghost" title="Adatta" @click="fitToView">⤢</button>
      </div>
    </div>

    <!-- Scrollable canvas viewport -->
    <div ref="viewportRef" class="report-canvas-viewport relative flex-1 overflow-auto" @mousedown.self="clearSelectionFromBackground">
      <div
        class="canvas-stage relative mx-auto my-4"
        :style="{ width: `${pageWidth * store.zoom}px`, height: `${pageHeight * store.zoom}px` }"
      >
        <div
          ref="pageRef"
          class="canvas-page absolute left-0 top-0 origin-top-left overflow-hidden shadow-pbi-card"
          :style="pageStyle"
          @mousedown.self="startLasso"
          @dragover.prevent
          @drop.prevent="onCanvasDrop"
        >
          <div class="canvas-grid pointer-events-none absolute inset-0" :style="gridStyle"></div>

          <div
            v-for="visual in pageVisuals"
            :key="visual.id"
            class="visual-wrapper group absolute"
            :class="{ 'visual-selected': isSelected(visual.id) }"
            :style="visualStyle(visual)"
            @mousedown.stop="startMove($event, visual)"
            @mouseenter="hoveredId = visual.id"
            @mouseleave="hoveredId = null"
            @contextmenu.prevent="selectAndContext(visual, $event)"
          >
            <nicegui-VisualHeader
              v-if="visual.properties?.header?.show !== false"
              :visual="visual"
              :selected="isSelected(visual.id)"
              :hovered="hoveredId === visual.id"
              @focus="focusVisual"
              @see-data="showSeeData"
              @delete="onDeleteVisual"
              @export="onExportVisual"
            />
            <div class="visual-content h-full w-full overflow-hidden" :style="{ paddingTop: visual.properties?.header?.show === false ? '0px' : '28px' }">
              <nicegui-VisualRenderer :visual="visual" />
            </div>

            <!-- Single-selection resize handles -->
            <template v-if="isSelected(visual.id) && store.selectedVisualIds.length === 1">
              <span
                v-for="handle in handles"
                :key="handle.direction"
                class="resize-handle"
                :class="`handle-${handle.direction}`"
                @mousedown.stop.prevent="startResize($event, handle.direction)"
              ></span>
            </template>
          </div>

          <!-- Multi-selection group box and handles -->
          <div
            v-if="selectionBounds && store.selectedVisualIds.length > 1"
            class="group-selection absolute border border-dashed border-pbi-accent bg-blue-500/5"
            :style="selectionBoundsStyle"
          >
            <span
              v-for="handle in handles"
              :key="`group-${handle.direction}`"
              class="resize-handle"
              :class="`handle-${handle.direction}`"
              @mousedown.stop.prevent="startGroupResize($event, handle.direction)"
            ></span>
          </div>

          <!-- Smart alignment guides -->
          <div
            v-for="(guide, index) in store.guides"
            :key="`guide-${index}`"
            class="smart-guide"
            :style="guideStyle(guide)"
          ></div>

          <!-- Lasso selection rectangle -->
          <div
            v-if="lasso.visible"
            class="lasso-box absolute border border-pbi-accent bg-blue-500/10"
            :style="{ left: `${lasso.x}px`, top: `${lasso.y}px`, width: `${lasso.w}px`, height: `${lasso.h}px` }"
          ></div>

          <div v-if="!pageVisuals.length" class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 text-pbi-text-muted">
            <span class="text-5xl opacity-30">📊</span>
            <span class="text-pbi-md font-semibold">Canvas vuoto</span>
            <span class="text-pbi-xs">Trascina campi dal pannello Dati o usa “Aggiungi visual”.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- See Data drawer -->
    <div v-if="store.seeDataVisual" class="see-data-panel flex h-[42%] shrink-0 flex-col border-t-2 border-pbi-accent bg-white shadow-pbi-modal">
      <div class="flex items-center justify-between border-b border-pbi-pane-border bg-pbi-header px-2 py-1">
        <div class="flex items-center gap-2 text-pbi-xs font-semibold">
          <span>🔎 Dati sottostanti:</span>
          <span class="text-pbi-accent">{{ store.seeDataVisual.title }}</span>
          <span class="rounded bg-white px-1.5 py-0.5 font-mono text-[10px]">{{ seeDataRows.length }} righe</span>
          <span v-if="store.visualData[store.seeDataVisual.id]?.generated_sql" class="max-w-[420px] truncate font-mono text-[9px] text-pbi-text-muted" :title="store.visualData[store.seeDataVisual.id].generated_sql">
            {{ store.visualData[store.seeDataVisual.id].generated_sql }}
          </span>
        </div>
        <button class="pbi-btn pbi-btn-ghost" @click="store.seeDataVisualId = null">✕ Chiudi</button>
      </div>
      <div class="min-h-0 flex-1 overflow-auto">
        <table class="w-full border-collapse text-left font-mono text-pbi-xs">
          <thead class="sticky top-0 z-10 bg-slate-200">
            <tr>
              <th class="border-b border-r border-pbi-pane-border px-2 py-1 text-center text-[10px]">#</th>
              <th v-for="column in seeDataColumns" :key="column" class="border-b border-r border-pbi-pane-border px-2 py-1 font-semibold">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in seeDataRows" :key="index" :class="index % 2 ? 'bg-slate-50' : 'bg-white'">
              <td class="border-b border-r border-slate-100 px-2 py-0.5 text-center text-[10px] text-pbi-text-muted">{{ index + 1 }}</td>
              <td v-for="column in seeDataColumns" :key="column" class="border-b border-r border-slate-100 px-2 py-0.5">
                {{ row[column] === null || row[column] === undefined ? '' : row[column] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Focus mode overlay -->
    <div v-if="store.focusedVisual" class="absolute inset-0 z-50 flex flex-col bg-black/45 p-4 backdrop-blur-sm">
      <div class="mx-auto flex h-full w-full max-w-[96%] flex-col overflow-hidden rounded bg-white shadow-pbi-modal">
        <div class="flex items-center justify-between border-b border-pbi-pane-border bg-pbi-header px-3 py-1.5">
          <div class="flex items-center gap-2">
            <span class="text-pbi-lg font-semibold">{{ store.focusedVisual.title }}</span>
            <span class="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold text-blue-800">Focus mode</span>
          </div>
          <div class="flex items-center gap-1">
            <button class="pbi-btn pbi-btn-ghost" @click="store.exportVisualData(store.focusedVisual, 'xlsx')">📊 XLSX</button>
            <button class="pbi-btn pbi-btn-ghost" @click="store.exportVisualData(store.focusedVisual, 'csv')">📄 CSV</button>
            <button class="pbi-btn pbi-btn-ghost" @click="store.setFocusedVisual(null)">✕ Chiudi</button>
          </div>
        </div>
        <div class="min-h-0 flex-1 p-4">
          <nicegui-VisualRenderer :visual="store.focusedVisual" />
        </div>
      </div>
    </div>

    <nicegui-PageTabBar />
  </div>
</template>

<script>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';

export default {
  name: 'ReportCanvas',
  props: {
    projectId: { type: String, default: 'default' },
  },
  setup(props) {
const store = useReportStore();
const viewportRef = ref(null);
const pageRef = ref(null);
const hoveredId = ref(null);
const addMenuOpen = ref(false);
const lasso = reactive({ startX: 0, startY: 0, x: 0, y: 0, w: 0, h: 0, visible: false });
const clipboardVisuals = ref([]);

const dragState = reactive({
  active: false,
  mode: '',
  startX: 0,
  startY: 0,
  direction: '',
  bounds: null,
  positions: {},
  relative: {},
  visualId: null,
});

const handles = [
  { direction: 'nw' },
  { direction: 'n' },
  { direction: 'ne' },
  { direction: 'e' },
  { direction: 'se' },
  { direction: 's' },
  { direction: 'sw' },
  { direction: 'w' },
];

const visualOptions = [
  { type: 'bar_chart', label: 'Barre', icon: '📊' },
  { type: 'column_chart', label: 'Colonne', icon: '📶' },
  { type: 'line_chart', label: 'Linee', icon: '📈' },
  { type: 'area_chart', label: 'Area', icon: '📉' },
  { type: 'pie_chart', label: 'Torta', icon: '🥧' },
  { type: 'donut_chart', label: 'Anello', icon: '🍩' },
  { type: 'treemap', label: 'Treemap', icon: '🟦' },
  { type: 'table', label: 'Tabella', icon: '📋' },
  { type: 'matrix', label: 'Matrice', icon: '🧮' },
  { type: 'card', label: 'Scheda', icon: '🔢' },
  { type: 'kpi', label: 'KPI', icon: '🎯' },
  { type: 'gauge', label: 'Indicatore', icon: '⏱' },
  { type: 'slicer', label: 'Slicer', icon: '🎛' },
  { type: 'scatter_chart', label: 'Dispersione', icon: '⚬' },
];

const pageVisuals = computed(() => store.activePage?.visuals || []);
const pageWidth = computed(() => store.activePage?.width || 1280);
const pageHeight = computed(() => store.activePage?.height || 720);

const pageStyle = computed(() => ({
  width: `${pageWidth.value}px`,
  height: `${pageHeight.value}px`,
  transform: `scale(${store.zoom})`,
  backgroundColor: store.activePage?.background || 'var(--pbi-bg-visual, #ffffff)',
  backgroundImage: store.activePage?.wallpaper ? `url(${store.activePage.wallpaper})` : 'none',
  backgroundSize: 'cover',
}));

const gridStyle = computed(() => {
  const size = Math.max(4, Number(store.gridSize) || 8);
  return {
    backgroundImage:
      'linear-gradient(to right, rgba(0,0,0,0.045) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.045) 1px, transparent 1px)',
    backgroundSize: `${size}px ${size}px`,
    display: store.snapToGrid ? 'block' : 'none',
  };
});

const selectionBounds = computed(() => {
  const visuals = store.selectedVisuals;
  if (visuals.length < 2) return null;
  const left = Math.min(...visuals.map(visual => visual.position.x));
  const top = Math.min(...visuals.map(visual => visual.position.y));
  const right = Math.max(...visuals.map(visual => visual.position.x + visual.position.width));
  const bottom = Math.max(...visuals.map(visual => visual.position.y + visual.position.height));
  return { x: left, y: top, width: right - left, height: bottom - top };
});

const selectionBoundsStyle = computed(() => {
  if (!selectionBounds.value) return {};
  return {
    left: `${selectionBounds.value.x}px`,
    top: `${selectionBounds.value.y}px`,
    width: `${selectionBounds.value.width}px`,
    height: `${selectionBounds.value.height}px`,
  };
});

const seeDataColumns = computed(() => store.visualData[store.seeDataVisual?.id]?.columns || []);
const seeDataRows = computed(() => (store.visualData[store.seeDataVisual?.id]?.rows || []).slice(0, 500));

function isSelected(visualId) {
  return store.selectedVisualIds.includes(visualId);
}

function colorWithAlpha(color, transparency = 0) {
  if (!color || typeof color !== 'string') return color;
  const percent = Math.max(0, Math.min(100, Number(transparency) || 0));
  if (percent === 0) return color;
  const match = color.replace('#', '').match(/^([0-9a-f]{6})$/i);
  if (!match) return color;
  const value = match[1];
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${(100 - percent) / 100})`;
}

function visualStyle(visual) {
  const properties = visual.properties || {};
  const border = properties.border || {};
  const shadow = properties.shadow || {};
  const background = colorWithAlpha(properties.background || '#ffffff', properties.backgroundTransparency || 0);
  return {
    left: `${visual.position.x}px`,
    top: `${visual.position.y}px`,
    width: `${visual.position.width}px`,
    height: `${visual.position.height}px`,
    zIndex: visual.position.z_index || 1,
    background,
    borderRadius: `${border.show ? border.radius ?? 4 : 4}px`,
    border: border.show ? `${border.width || 1}px solid ${border.color || '#d2d0ce'}` : '1px solid transparent',
    boxShadow: shadow.show
      ? `${shadow.distance || 2}px ${shadow.distance || 2}px ${shadow.blur || 8}px rgba(0,0,0,${(100 - (shadow.transparency ?? 80)) / 100})`
      : 'var(--pbi-shadow-visual, 0 1.6px 3.6px rgba(0,0,0,.13))',
  };
}

function guideStyle(guide) {
  if (guide.axis === 'x') {
    return { left: `${guide.position}px`, top: '0px', width: '1px', height: '100%' };
  }
  return { left: '0px', top: `${guide.position}px`, width: '100%', height: '1px' };
}

function snap(value) {
  if (!store.snapToGrid) return Math.round(value);
  const grid = Math.max(1, Number(store.gridSize) || 8);
  return Math.round(value / grid) * grid;
}

function toPagePoint(event) {
  const rect = pageRef.value?.getBoundingClientRect();
  if (!rect) return { x: 0, y: 0 };
  return {
    x: (event.clientX - rect.left) / store.zoom,
    y: (event.clientY - rect.top) / store.zoom,
  };
}

function clearSelectionFromBackground(event) {
  if (event.target === event.currentTarget) store.clearSelection();
}

function selectAndContext(visual, event) {
  store.selectVisual(visual.id);
  event.preventDefault();
}

function onSelect(visual, event) {
  store.selectVisual(visual.id, event.shiftKey || event.ctrlKey || event.metaKey);
}

function addVisual(type) {
  addMenuOpen.value = false;
  store.addVisual(type);
}

function fitToView() {
  const viewport = viewportRef.value;
  if (!viewport) return;
  const availableWidth = viewport.clientWidth - 48;
  const availableHeight = viewport.clientHeight - 48;
  const scale = Math.min(availableWidth / pageWidth.value, availableHeight / pageHeight.value);
  store.setZoom(Math.max(0.2, Math.min(2, scale)));
}

// ---------------------------------------------------------------------------
// Lasso selection
// ---------------------------------------------------------------------------
function startLasso(event) {
  if (event.button !== 0) return;
  const point = toPagePoint(event);
  lasso.startX = point.x;
  lasso.startY = point.y;
  lasso.x = point.x;
  lasso.y = point.y;
  lasso.w = 0;
  lasso.h = 0;
  lasso.visible = true;
  const additive = event.shiftKey || event.ctrlKey || event.metaKey;
  if (!additive) store.clearSelection();
  document.addEventListener('mousemove', onLassoMove);
  document.addEventListener('mouseup', onLassoUp);
}

function onLassoMove(event) {
  const point = toPagePoint(event);
  lasso.x = Math.min(lasso.startX, point.x);
  lasso.y = Math.min(lasso.startY, point.y);
  lasso.w = Math.abs(point.x - lasso.startX);
  lasso.h = Math.abs(point.y - lasso.startY);
}

function onLassoUp() {
  document.removeEventListener('mousemove', onLassoMove);
  document.removeEventListener('mouseup', onLassoUp);
  if (lasso.w > 4 || lasso.h > 4) {
    const matching = pageVisuals.value.filter(visual => {
      const position = visual.position;
      return (
        position.x < lasso.x + lasso.w &&
        position.x + position.width > lasso.x &&
        position.y < lasso.y + lasso.h &&
        position.y + position.height > lasso.y
      );
    });
    store.clearSelection();
    matching.forEach((visual, index) => store.selectVisual(visual.id, index > 0));
  }
  lasso.visible = false;
}

// ---------------------------------------------------------------------------
// Move (single and multi selection) with snapping + smart guides
// ---------------------------------------------------------------------------
function selectedFor(visual) {
  return store.selectedVisualIds.includes(visual.id) ? [...store.selectedVisualIds] : [visual.id];
}

function boundsFor(ids) {
  const visuals = ids.map(id => store.getVisual(id)).filter(Boolean);
  if (!visuals.length) return null;
  const x = Math.min(...visuals.map(item => item.position.x));
  const y = Math.min(...visuals.map(item => item.position.y));
  const right = Math.max(...visuals.map(item => item.position.x + item.position.width));
  const bottom = Math.max(...visuals.map(item => item.position.y + item.position.height));
  return { x, y, width: right - x, height: bottom - y };
}

function startMove(event, visual) {
  if (event.button !== 0) return;
  if (!store.selectedVisualIds.includes(visual.id)) {
    store.selectVisual(visual.id, event.shiftKey || event.ctrlKey || event.metaKey);
  } else if (event.shiftKey || event.ctrlKey || event.metaKey) {
    store.selectVisual(visual.id, true);
    return;
  }
  const ids = selectedFor(visual);
  const positions = {};
  ids.forEach(id => {
    const item = store.getVisual(id);
    if (item) positions[id] = { x: item.position.x, y: item.position.y, width: item.position.width, height: item.position.height };
  });
  dragState.active = true;
  dragState.mode = 'move';
  dragState.startX = event.clientX;
  dragState.startY = event.clientY;
  dragState.positions = positions;
  dragState.bounds = boundsFor(ids);
  dragState.visualId = visual.id;
  document.body.style.cursor = 'move';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', stopDrag);
}

function onMove(event) {
  if (!dragState.active || !['move', 'resize', 'group-resize'].includes(dragState.mode)) return;
  const dx = (event.clientX - dragState.startX) / store.zoom;
  const dy = (event.clientY - dragState.startY) / store.zoom;
  if (dragState.mode === 'move') {
    let nextX = dragState.bounds.x + dx;
    let nextY = dragState.bounds.y + dy;
    if (event.shiftKey) {
      if (Math.abs(dx) > Math.abs(dy)) nextY = dragState.bounds.y;
      else nextX = dragState.bounds.x;
    }
    nextX = snap(nextX);
    nextY = snap(nextY);
    nextX = Math.max(0, Math.min(pageWidth.value - dragState.bounds.width, nextX));
    nextY = Math.max(0, Math.min(pageHeight.value - dragState.bounds.height, nextY));

    const guideResult = smartGuides({ ...dragState.bounds, x: nextX, y: nextY }, dragState.bounds);
    nextX += guideResult.dx;
    nextY += guideResult.dy;
    nextX = Math.max(0, Math.min(pageWidth.value - dragState.bounds.width, nextX));
    nextY = Math.max(0, Math.min(pageHeight.value - dragState.bounds.height, nextY));

    const deltaX = nextX - dragState.bounds.x;
    const deltaY = nextY - dragState.bounds.y;
    Object.entries(dragState.positions).forEach(([id, start]) => {
      store.updateVisualPosition(id, {
        x: Math.round(start.x + deltaX),
        y: Math.round(start.y + deltaY),
      });
    });
    store.guides = guideResult.guides;
  } else if (dragState.mode === 'resize') {
    const start = dragState.positions[dragState.visualId];
    if (!start) return;
    const result = resizeRect(start, dragState.direction, dx, dy);
    store.updateVisualPosition(dragState.visualId, result);
  } else if (dragState.mode === 'group-resize') {
    const startBounds = dragState.bounds;
    const resized = resizeRect(startBounds, dragState.direction, dx, dy, 120, 80);
    const scaleX = resized.width / Math.max(1, startBounds.width);
    const scaleY = resized.height / Math.max(1, startBounds.height);
    Object.entries(dragState.relative).forEach(([id, relative]) => {
      store.updateVisualPosition(id, {
        x: Math.round(resized.x + relative.x * resized.width),
        y: Math.round(resized.y + relative.y * resized.height),
        width: Math.max(60, Math.round(relative.width * startBounds.width * scaleX)),
        height: Math.max(48, Math.round(relative.height * startBounds.height * scaleY)),
      });
    });
  }
}

function resizeRect(start, direction, dx, dy, minWidth = 80, minHeight = 60) {
  let x = start.x;
  let y = start.y;
  let width = start.width;
  let height = start.height;
  if (direction.includes('e')) width = start.width + dx;
  if (direction.includes('s')) height = start.height + dy;
  if (direction.includes('w')) {
    width = start.width - dx;
    x = start.x + dx;
  }
  if (direction.includes('n')) {
    height = start.height - dy;
    y = start.y + dy;
  }
  if (width < minWidth) {
    if (direction.includes('w')) x -= minWidth - width;
    width = minWidth;
  }
  if (height < minHeight) {
    if (direction.includes('n')) y -= minHeight - height;
    height = minHeight;
  }
  x = Math.max(0, Math.min(pageWidth.value - width, x));
  y = Math.max(0, Math.min(pageHeight.value - height, y));
  width = snap(width);
  height = snap(height);
  return {
    x: Math.round(x),
    y: Math.round(y),
    width: Math.max(minWidth, Math.round(width)),
    height: Math.max(minHeight, Math.round(height)),
  };
}

function smartGuides(bounds, originalBounds) {
  const others = pageVisuals.value.filter(visual => !store.selectedVisualIds.includes(visual.id));
  const threshold = Math.max(2, 5 / store.zoom);
  const xCandidates = [0, pageWidth.value / 2, pageWidth.value];
  const yCandidates = [0, pageHeight.value / 2, pageHeight.value];
  others.forEach(visual => {
    xCandidates.push(visual.position.x, visual.position.x + visual.position.width / 2, visual.position.x + visual.position.width);
    yCandidates.push(visual.position.y, visual.position.y + visual.position.height / 2, visual.position.y + visual.position.height);
  });

  const movingX = [bounds.x, bounds.x + bounds.width / 2, bounds.x + bounds.width];
  const movingY = [bounds.y, bounds.y + bounds.height / 2, bounds.y + bounds.height];
  let bestX = null;
  let bestY = null;
  xCandidates.forEach(candidate => {
    movingX.forEach(point => {
      const diff = candidate - point;
      if (Math.abs(diff) <= threshold && (!bestX || Math.abs(diff) < Math.abs(bestX.diff))) {
        bestX = { diff, candidate };
      }
    });
  });
  yCandidates.forEach(candidate => {
    movingY.forEach(point => {
      const diff = candidate - point;
      if (Math.abs(diff) <= threshold && (!bestY || Math.abs(diff) < Math.abs(bestY.diff))) {
        bestY = { diff, candidate };
      }
    });
  });

  const guides = [];
  if (bestX) guides.push({ axis: 'x', position: bestX.candidate });
  if (bestY) guides.push({ axis: 'y', position: bestY.candidate });
  return {
    dx: store.showSmartGuides && bestX ? bestX.diff : 0,
    dy: store.showSmartGuides && bestY ? bestY.diff : 0,
    guides: store.showSmartGuides ? guides : [],
  };
}

function startResize(event, direction) {
  const visual = store.selectedVisual;
  if (!visual) return;
  dragState.active = true;
  dragState.mode = 'resize';
  dragState.direction = direction;
  dragState.visualId = visual.id;
  dragState.startX = event.clientX;
  dragState.startY = event.clientY;
  dragState.positions = {
    [visual.id]: {
      x: visual.position.x,
      y: visual.position.y,
      width: visual.position.width,
      height: visual.position.height,
    },
  };
  document.body.style.cursor = `${direction}-resize`;
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', stopDrag);
}

function startGroupResize(event, direction) {
  if (!selectionBounds.value) return;
  dragState.active = true;
  dragState.mode = 'group-resize';
  dragState.direction = direction;
  dragState.startX = event.clientX;
  dragState.startY = event.clientY;
  dragState.bounds = { ...selectionBounds.value };
  dragState.relative = {};
  store.selectedVisuals.forEach(visual => {
    dragState.relative[visual.id] = {
      x: (visual.position.x - dragState.bounds.x) / dragState.bounds.width,
      y: (visual.position.y - dragState.bounds.y) / dragState.bounds.height,
      width: visual.position.width / dragState.bounds.width,
      height: visual.position.height / dragState.bounds.height,
    };
  });
  document.body.style.cursor = `${direction}-resize`;
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', stopDrag);
}

function stopDrag() {
  document.removeEventListener('mousemove', onMove);
  document.removeEventListener('mouseup', stopDrag);
  document.body.style.cursor = '';
  dragState.active = false;
  dragState.mode = '';
  dragState.positions = {};
  dragState.relative = {};
  store.guides = [];
}

// ---------------------------------------------------------------------------
// Visual actions / drop
// ---------------------------------------------------------------------------
function focusVisual(visualId) {
  store.setFocusedVisual(visualId);
}

function showSeeData(visualId) {
  store.setSeeDataVisual(store.seeDataVisualId === visualId ? null : visualId);
}

function onDeleteVisual(visualId) {
  store.removeVisual(visualId);
}

function onExportVisual({ id, format }) {
  store.exportVisualData(id, format);
}

function onCanvasDrop(event) {
  addMenuOpen.value = false;
  let raw = null;
  try {
    raw = event.dataTransfer.getData('application/x-pybi-field') || event.dataTransfer.getData('text/plain');
  } catch (error) {
    raw = null;
  }
  if (!raw) return;
  let field;
  try {
    field = JSON.parse(raw);
  } catch (error) {
    return;
  }
  if (!field || !field.column) return;
  const point = toPagePoint(event);
  const type = field.kind === 'measure' ? 'card' : 'column_chart';
  store.addVisual(type, {
    field,
    x: Math.max(0, Math.min(pageWidth.value - 320, snap(point.x))),
    y: Math.max(0, Math.min(pageHeight.value - 200, snap(point.y))),
  });
}

// ---------------------------------------------------------------------------
// Keyboard shortcuts
// ---------------------------------------------------------------------------
function isEditableTarget(target) {
  return !!(
    target &&
    (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)
  );
}

function onKeyDown(event) {
  if (isEditableTarget(event.target)) return;
  const mod = event.ctrlKey || event.metaKey;
  const key = event.key.toLowerCase();

  if (mod && key === 's') {
    event.preventDefault();
    store.saveLayout();
    return;
  }
  if (mod && key === 'a') {
    event.preventDefault();
    store.selectAllVisuals();
    return;
  }
  if (mod && key === 'd') {
    event.preventDefault();
    if (store.primarySelectedId) store.duplicateVisual(store.primarySelectedId);
    return;
  }
  if (mod && key === 'c') {
    clipboardVisuals.value = store.selectedVisuals.map(visual => JSON.parse(JSON.stringify(visual)));
    return;
  }
  if (mod && key === 'v') {
    event.preventDefault();
    clipboardVisuals.value.forEach((visual, index) => {
      const copy = JSON.parse(JSON.stringify(visual));
      copy.id = `vis_${Math.random().toString(36).slice(2, 10)}`;
      copy.position.x = Math.min(pageWidth.value - 80, copy.position.x + 24 * (index + 1));
      copy.position.y = Math.min(pageHeight.value - 80, copy.position.y + 24 * (index + 1));
      store.activePage.visuals.push(copy);
      store.selectVisual(copy.id);
    });
    if (clipboardVisuals.value.length) store.markDirty();
    return;
  }
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (store.selectedVisualIds.length) {
      event.preventDefault();
      store.removeSelectedVisuals();
    }
    return;
  }
  if (event.key === 'Escape') {
    store.setFocusedVisual(null);
    store.seeDataVisualId = null;
    store.clearSelection();
    return;
  }
  if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key) && store.selectedVisualIds.length) {
    event.preventDefault();
    const step = event.shiftKey ? 1 : Math.max(1, Number(store.gridSize) || 8);
    const delta = {
      ArrowLeft: { x: -step, y: 0 },
      ArrowRight: { x: step, y: 0 },
      ArrowUp: { x: 0, y: -step },
      ArrowDown: { x: 0, y: step },
    }[event.key];
    store.selectedVisuals.forEach(visual => {
      store.updateVisualPosition(visual.id, {
        x: Math.max(0, Math.min(pageWidth.value - visual.position.width, visual.position.x + delta.x)),
        y: Math.max(0, Math.min(pageHeight.value - visual.position.height, visual.position.y + delta.y)),
      });
    });
  }
}

function onGlobalMouseDown(event) {
  if (!addMenuOpen.value) return;
  if (!event.target.closest('.canvas-command-bar, .relative')) addMenuOpen.value = false;
}

onMounted(async () => {
  if (props.projectId && store.projectId !== props.projectId) store.projectId = props.projectId;
  if (!store.layout.pages?.length) await store.fetchLayout(props.projectId);
  window.addEventListener('keydown', onKeyDown);
  document.addEventListener('mousedown', onGlobalMouseDown);
  nextTick(() => fitToView());
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown);
  document.removeEventListener('mousedown', onGlobalMouseDown);
  document.removeEventListener('mousemove', onMove);
  document.removeEventListener('mouseup', stopDrag);
  document.removeEventListener('mousemove', onLassoMove);
  document.removeEventListener('mouseup', onLassoUp);
});

    return {
      store,
      viewportRef,
      pageRef,
      hoveredId,
      addMenuOpen,
      lasso,
      clipboardVisuals,
      dragState,
      handles,
      visualOptions,
      pageVisuals,
      pageWidth,
      pageHeight,
      pageStyle,
      gridStyle,
      selectionBounds,
      selectionBoundsStyle,
      seeDataColumns,
      seeDataRows,
      isSelected,
      visualStyle,
      guideStyle,
      clearSelectionFromBackground,
      selectAndContext,
      onSelect,
      addVisual,
      fitToView,
      startLasso,
      startMove,
      startResize,
      startGroupResize,
      focusVisual,
      showSeeData,
      onDeleteVisual,
      onExportVisual,
      onCanvasDrop,
      onKeyDown,
      onGlobalMouseDown,
    };
  },
};
</script>

<style scoped>
.canvas-page {
  background-color: var(--pbi-bg-visual, #ffffff);
}
.visual-wrapper {
  cursor: default;
  transition: outline-color 0.1s ease;
  outline: 1px solid transparent;
}
.visual-wrapper:hover {
  outline-color: rgba(17, 141, 255, 0.55);
}
.visual-wrapper.visual-selected {
  outline: 2px solid #118dff;
  outline-offset: 0;
}
.visual-content {
  box-sizing: border-box;
}
.resize-handle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: #ffffff;
  border: 1px solid #118dff;
  border-radius: 1px;
  z-index: 40;
}
.handle-nw { left: -4px; top: -4px; cursor: nwse-resize; }
.handle-n { left: calc(50% - 4px); top: -4px; cursor: ns-resize; }
.handle-ne { right: -4px; top: -4px; cursor: nesw-resize; }
.handle-e { right: -4px; top: calc(50% - 4px); cursor: ew-resize; }
.handle-se { right: -4px; bottom: -4px; cursor: nwse-resize; }
.handle-s { left: calc(50% - 4px); bottom: -4px; cursor: ns-resize; }
.handle-sw { left: -4px; bottom: -4px; cursor: nesw-resize; }
.handle-w { left: -4px; top: calc(50% - 4px); cursor: ew-resize; }
.smart-guide {
  position: absolute;
  z-index: 45;
  background: #d13438;
  pointer-events: none;
}
.lasso-box {
  z-index: 44;
  pointer-events: none;
}
.group-selection {
  z-index: 35;
  pointer-events: none;
}
.group-selection .resize-handle {
  pointer-events: auto;
}
</style>
