<template>
  <div class="formatting-pane flex h-full min-h-0 w-full flex-col bg-pbi-pane text-pbi-text">
    <!-- Page formatting (no visual selected) -->
    <div v-if="!visual" class="min-h-0 flex-1 overflow-y-auto p-2">
      <div class="mb-2 flex items-center gap-1.5 text-pbi-md font-semibold">
        <span>🎨</span><span>Formato pagina</span>
      </div>
      <div class="format-section">
        <div class="format-section-title">Tema del report</div>
        <div class="p-2">
          <select :value="themeStore.theme" class="w-full rounded border border-pbi-pane-border bg-white px-1 py-1 text-pbi-xs" @change="changeTheme">
            <option v-for="theme in themeStore.availableThemes" :key="theme.key" :value="theme.key">{{ theme.name }}</option>
          </select>
          <div class="mt-1 flex gap-0.5">
            <span v-for="color in themeStore.dataColors" :key="color" class="h-4 flex-1 rounded-sm" :style="{ backgroundColor: color }"></span>
          </div>
        </div>
      </div>

      <div class="format-section">
        <div class="format-section-title">Dimensioni pagina</div>
        <div class="space-y-1 p-2">
          <label class="format-row">
            <span>Preset</span>
            <select :value="pagePreset" class="format-control" @change="applyPreset($event.target.value)">
              <option value="16:9">16:9 (1280 x 720)</option>
              <option value="4:3">4:3 (960 x 720)</option>
              <option value="tooltip">Tooltip (320 x 240)</option>
              <option value="custom">Personalizzata</option>
            </select>
          </label>
          <label class="format-row">
            <span>Larghezza</span>
            <input :value="store.activePage?.width" type="number" min="200" max="7680" class="format-control" @change="updatePage({ width: Number($event.target.value) })" />
          </label>
          <label class="format-row">
            <span>Altezza</span>
            <input :value="store.activePage?.height" type="number" min="200" max="4320" class="format-control" @change="updatePage({ height: Number($event.target.value) })" />
          </label>
        </div>
      </div>

      <div class="format-section">
        <div class="format-section-title">Sfondo pagina</div>
        <div class="space-y-1 p-2">
          <label class="format-row">
            <span>Colore</span>
            <input :value="store.activePage?.background || '#ffffff'" type="color" class="format-color" @input="updatePage({ background: $event.target.value })" />
          </label>
          <label class="format-row">
            <span>Wallpaper URL</span>
            <input :value="store.activePage?.wallpaper || ''" type="text" placeholder="https://…" class="format-control" @change="updatePage({ wallpaper: $event.target.value })" />
          </label>
        </div>
      </div>

      <div class="format-section">
        <div class="format-section-title">Informazioni pagina</div>
        <div class="space-y-1 p-2 text-[10px] text-pbi-text-muted">
          <div class="flex justify-between"><span>Nome</span><span class="font-semibold text-pbi-text">{{ store.activePage?.name }}</span></div>
          <div class="flex justify-between"><span>Tipo</span><span class="font-semibold text-pbi-text">{{ store.activePage?.page_type }}</span></div>
          <div class="flex justify-between"><span>Visual</span><span class="font-semibold text-pbi-text">{{ store.activePage?.visuals?.length || 0 }}</span></div>
          <div class="flex justify-between"><span>Filtri pagina</span><span class="font-semibold text-pbi-text">{{ store.activePage?.page_filters?.length || 0 }}</span></div>
        </div>
      </div>
    </div>

    <!-- Visual formatting -->
    <template v-else>
      <div class="flex shrink-0 border-b border-pbi-pane-border text-[10px] font-semibold">
        <button class="flex-1 py-1.5" :class="tab === 'visual' ? 'border-b-2 border-pbi-accent text-pbi-accent' : 'text-pbi-text-muted hover:bg-slate-50'" @click="tab = 'visual'">
          Elemento visivo
        </button>
        <button class="flex-1 py-1.5" :class="tab === 'general' ? 'border-b-2 border-pbi-accent text-pbi-accent' : 'text-pbi-text-muted hover:bg-slate-50'" @click="tab = 'general'">
          Generale
        </button>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <template v-if="tab === 'visual'">
          <details class="format-section" open>
            <summary class="format-section-title">🎨 Colori dati</summary>
            <div class="p-2">
              <div class="mb-1 flex items-center justify-between">
                <span class="text-[10px] text-pbi-text-muted">Serie / categorie</span>
                <button class="fx-btn" title="Formattazione condizionale" @click="openFx('dataColors')">fx</button>
              </div>
              <div class="space-y-1">
                <div v-for="(color, index) in dataColors" :key="index" class="flex items-center gap-1">
                  <input :value="color" type="color" class="format-color" @input="setColor(index, $event.target.value)" />
                  <span class="flex-1 truncate text-[10px] text-pbi-text-muted">Serie {{ index + 1 }}</span>
                  <button class="text-[10px] text-pbi-text-muted hover:text-red-600" @click="removeColor(index)">✕</button>
                </div>
              </div>
              <div class="mt-1 flex gap-1">
                <button class="pbi-btn pbi-btn-ghost text-[10px]" @click="addColor">＋ Colore</button>
                <button class="pbi-btn pbi-btn-ghost text-[10px]" @click="applyPalette">Tema</button>
              </div>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">🏷 Etichette dati</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="labels.show" class="h-3 w-3 accent-blue-600" @change="patch('dataLabels', { show: $event.target.checked })" /></label>
              <label class="format-row"><span>Posizione</span>
                <select :value="labels.position" class="format-control" @change="patch('dataLabels', { position: $event.target.value })">
                  <option value="auto">Auto</option><option value="inside">Interno</option><option value="outside">Esterno</option><option value="top">In alto</option>
                </select>
              </label>
              <label class="format-row"><span>Unità</span>
                <select :value="labels.units" class="format-control" @change="patch('dataLabels', { units: $event.target.value })">
                  <option value="none">Nessuna</option><option value="thousands">Migliaia</option><option value="millions">Milioni</option><option value="billions">Miliardi</option>
                </select>
              </label>
              <label class="format-row"><span>Decimali</span><input :value="labels.decimals" type="number" min="0" max="8" class="format-control" @change="patch('dataLabels', { decimals: Number($event.target.value) })" /></label>
              <label class="format-row"><span>Colore</span><input :value="labels.color" type="color" class="format-color" @input="patch('dataLabels', { color: $event.target.value })" /></label>
              <label class="format-row"><span>Font</span><input :value="labels.fontSize" type="number" min="6" max="40" class="format-control" @change="patch('dataLabels', { fontSize: Number($event.target.value) })" /></label>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">🗂 Legenda</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="legend.show" class="h-3 w-3 accent-blue-600" @change="patch('legend', { show: $event.target.checked })" /></label>
              <label class="format-row"><span>Posizione</span>
                <select :value="legend.position" class="format-control" @change="patch('legend', { position: $event.target.value })">
                  <option value="top">In alto</option><option value="bottom">In basso</option><option value="left">A sinistra</option><option value="right">A destra</option>
                  <option value="top-left">In alto a sinistra</option><option value="top-right">In alto a destra</option>
                  <option value="bottom-left">In basso a sinistra</option><option value="bottom-right">In basso a destra</option>
                </select>
              </label>
              <label class="format-row"><span>Titolo</span><input :value="legend.title" type="text" class="format-control" @change="patch('legend', { title: $event.target.value })" /></label>
              <label class="format-row"><span>Colore</span><input :value="legend.color" type="color" class="format-color" @input="patch('legend', { color: $event.target.value })" /></label>
              <label class="format-row"><span>Font</span><input :value="legend.fontSize" type="number" min="6" max="30" class="format-control" @change="patch('legend', { fontSize: Number($event.target.value) })" /></label>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">↔ Asse X</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="xAxis.show" class="h-3 w-3 accent-blue-600" @change="patch('xAxis', { show: $event.target.checked })" /></label>
              <label class="format-row"><span>Titolo</span><input :value="xAxis.title" type="text" class="format-control" @change="patch('xAxis', { title: $event.target.value })" /></label>
              <label class="format-row"><span>Colore</span><input :value="xAxis.color" type="color" class="format-color" @input="patch('xAxis', { color: $event.target.value })" /></label>
              <label class="format-row"><span>Font</span><input :value="xAxis.fontSize" type="number" min="6" max="30" class="format-control" @change="patch('xAxis', { fontSize: Number($event.target.value) })" /></label>
              <label class="format-row"><span>Scala log</span><input type="checkbox" :checked="xAxis.logScale" class="h-3 w-3 accent-blue-600" @change="patch('xAxis', { logScale: $event.target.checked })" /></label>
              <label class="format-row"><span>Intervallo</span><input :value="xAxis.interval ?? ''" type="number" min="0" class="format-control" @change="patch('xAxis', { interval: $event.target.value === '' ? null : Number($event.target.value) })" /></label>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">↕ Asse Y</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="yAxis.show" class="h-3 w-3 accent-blue-600" @change="patch('yAxis', { show: $event.target.checked })" /></label>
              <label class="format-row"><span>Titolo</span><input :value="yAxis.title" type="text" class="format-control" @change="patch('yAxis', { title: $event.target.value })" /></label>
              <label class="format-row"><span>Colore</span><input :value="yAxis.color" type="color" class="format-color" @input="patch('yAxis', { color: $event.target.value })" /></label>
              <label class="format-row"><span>Font</span><input :value="yAxis.fontSize" type="number" min="6" max="30" class="format-control" @change="patch('yAxis', { fontSize: Number($event.target.value) })" /></label>
              <label class="format-row"><span>Scala log</span><input type="checkbox" :checked="yAxis.logScale" class="h-3 w-3 accent-blue-600" @change="patch('yAxis', { logScale: $event.target.checked })" /></label>
              <label class="format-row"><span>Intervallo</span><input :value="yAxis.interval ?? ''" type="number" min="0" class="format-control" @change="patch('yAxis', { interval: $event.target.value === '' ? null : Number($event.target.value) })" /></label>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">📏 Griglia</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="gridlines.show" class="h-3 w-3 accent-blue-600" @change="patch('gridlines', { show: $event.target.checked })" /></label>
              <label class="format-row"><span>Orizzontali</span><input type="checkbox" :checked="gridlines.horizontal" class="h-3 w-3 accent-blue-600" @change="patch('gridlines', { horizontal: $event.target.checked })" /></label>
              <label class="format-row"><span>Verticali</span><input type="checkbox" :checked="gridlines.vertical" class="h-3 w-3 accent-blue-600" @change="patch('gridlines', { vertical: $event.target.checked })" /></label>
              <label class="format-row"><span>Colore</span><input :value="gridlines.color" type="color" class="format-color" @input="patch('gridlines', { color: $event.target.value })" /></label>
              <label class="format-row"><span>Stile</span>
                <select :value="gridlines.stroke" class="format-control" @change="patch('gridlines', { stroke: $event.target.value })">
                  <option value="solid">Continua</option><option value="dashed">Tratteggiata</option><option value="dotted">Puntinata</option>
                </select>
              </label>
              <label class="format-row"><span>Spessore</span><input :value="gridlines.width" type="number" step="0.5" min="0.5" max="6" class="format-control" @change="patch('gridlines', { width: Number($event.target.value) })" /></label>
            </div>
          </details>
        </template>

        <template v-else>
          <details class="format-section" open>
            <summary class="format-section-title">🔤 Titolo</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="props.titleVisible !== false" class="h-3 w-3 accent-blue-600" @change="set('titleVisible', $event.target.checked)" /></label>
              <label class="format-row"><span>Testo</span><input :value="props.title" type="text" class="format-control" @change="set('title', $event.target.value)" /></label>
              <label class="format-row"><span>Font</span><input :value="props.titleFontSize" type="number" min="6" max="48" class="format-control" @change="set('titleFontSize', Number($event.target.value))" /></label>
              <label class="format-row"><span>Colore</span><input :value="props.titleColor" type="color" class="format-color" @input="set('titleColor', $event.target.value)" /></label>
              <label class="format-row"><span>Allineamento</span>
                <select :value="props.titleAlign" class="format-control" @change="set('titleAlign', $event.target.value)">
                  <option value="left">Sinistra</option><option value="center">Centro</option><option value="right">Destra</option>
                </select>
              </label>
              <label class="format-row"><span>Sfondo titolo</span><input :value="props.titleBackground || '#ffffff'" type="color" class="format-color" @input="set('titleBackground', $event.target.value)" /></label>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">🖼 Sfondo</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Colore</span><input :value="props.background || '#ffffff'" type="color" class="format-color" @input="set('background', $event.target.value)" /></label>
              <label class="format-row"><span>Trasparenza</span><input :value="props.backgroundTransparency || 0" type="range" min="0" max="100" class="flex-1" @input="set('backgroundTransparency', Number($event.target.value))" /></label>
              <div class="text-right text-[9px] text-pbi-text-muted">{{ props.backgroundTransparency || 0 }}%</div>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">🔲 Bordo</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="border.show" class="h-3 w-3 accent-blue-600" @change="patch('border', { show: $event.target.checked })" /></label>
              <label class="format-row"><span>Colore</span><input :value="border.color" type="color" class="format-color" @input="patch('border', { color: $event.target.value })" /></label>
              <label class="format-row"><span>Raggio</span><input :value="border.radius" type="number" min="0" max="40" class="format-control" @change="patch('border', { radius: Number($event.target.value) })" /></label>
              <label class="format-row"><span>Spessore</span><input :value="border.width" type="number" min="1" max="12" class="format-control" @change="patch('border', { width: Number($event.target.value) })" /></label>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">🌓 Ombra</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="shadow.show" class="h-3 w-3 accent-blue-600" @change="patch('shadow', { show: $event.target.checked })" /></label>
              <label class="format-row"><span>Colore</span><input :value="shadow.color" type="color" class="format-color" @input="patch('shadow', { color: $event.target.value })" /></label>
              <label class="format-row"><span>Sfocatura</span><input :value="shadow.blur" type="number" min="0" max="60" class="format-control" @change="patch('shadow', { blur: Number($event.target.value) })" /></label>
              <label class="format-row"><span>Distanza</span><input :value="shadow.distance" type="number" min="0" max="30" class="format-control" @change="patch('shadow', { distance: Number($event.target.value) })" /></label>
              <label class="format-row"><span>Angolo</span><input :value="shadow.angle" type="number" min="0" max="360" class="format-control" @change="patch('shadow', { angle: Number($event.target.value) })" /></label>
              <label class="format-row"><span>Trasparenza</span><input :value="shadow.transparency" type="range" min="0" max="100" class="flex-1" @input="patch('shadow', { transparency: Number($event.target.value) })" /></label>
            </div>
          </details>

          <details class="format-section">
            <summary class="format-section-title">⚙ Intestazione visual</summary>
            <div class="space-y-1 p-2">
              <label class="format-row"><span>Mostra</span><input type="checkbox" :checked="header.show !== false" class="h-3 w-3 accent-blue-600" @change="patch('header', { show: $event.target.checked })" /></label>
              <label v-for="icon in ['focus', 'filters', 'menu']" :key="icon" class="format-row">
                <span>{{ icon === 'focus' ? '🔍 Focus' : icon === 'filters' ? '🧹 Filtri' : '⋯ Menu' }}</span>
                <input type="checkbox" :checked="(header.icons || []).includes(icon)" class="h-3 w-3 accent-blue-600" @change="toggleHeaderIcon(icon, $event.target.checked)" />
              </label>
            </div>
          </details>
        </template>
      </div>
    </template>

    <!-- Conditional formatting modal -->
    <Teleport to="body">
      <div v-if="fx.open" class="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 p-4" @mousedown.self="fx.open = false">
        <div class="w-full max-w-xl overflow-hidden rounded border border-pbi-pane-border bg-white shadow-pbi-modal">
          <div class="flex items-center justify-between border-b border-pbi-pane-border bg-pbi-header px-3 py-2">
            <div class="flex items-center gap-2">
              <span class="rounded bg-blue-600 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white">fx</span>
              <span class="text-pbi-md font-semibold">Formattazione condizionale</span>
            </div>
            <button class="pbi-btn pbi-btn-ghost" @click="fx.open = false">✕</button>
          </div>
          <div class="max-h-[70vh] space-y-3 overflow-y-auto p-3 text-pbi-xs">
            <label class="format-row">
              <span>Applica a</span>
              <select v-model="fx.target" class="format-control">
                <option value="dataColors">Colori dati</option>
                <option value="background">Sfondo</option>
                <option value="fontColor">Colore testo</option>
              </select>
            </label>
            <label class="format-row">
              <span>Campo base</span>
              <select v-model="fx.field" class="format-control">
                <option value="">Seleziona campo…</option>
                <option v-for="field in fxFields" :key="field.value" :value="field.value">{{ field.label }}</option>
              </select>
            </label>
            <div class="grid grid-cols-2 gap-0.5 rounded bg-slate-100 p-0.5 text-[10px] font-semibold">
              <button class="rounded py-1" :class="fx.mode === 'gradient' ? 'bg-white text-pbi-accent shadow-sm' : 'text-pbi-text-muted'" @click="fx.mode = 'gradient'">Scala di colori</button>
              <button class="rounded py-1" :class="fx.mode === 'rules' ? 'bg-white text-pbi-accent shadow-sm' : 'text-pbi-text-muted'" @click="fx.mode = 'rules'">Regole</button>
            </div>

            <div v-if="fx.mode === 'gradient'" class="space-y-2 rounded border border-pbi-pane-border p-2">
              <div class="grid grid-cols-2 gap-2">
                <label class="format-row"><span>Minimo</span><input v-model="fx.minColor" type="color" class="format-color" /></label>
                <label class="format-row"><span>Massimo</span><input v-model="fx.maxColor" type="color" class="format-color" /></label>
              </div>
              <div class="h-5 rounded" :style="{ background: `linear-gradient(to right, ${fx.minColor}, ${fx.maxColor})` }"></div>
            </div>

            <div v-else class="space-y-1 rounded border border-pbi-pane-border p-2">
              <div v-for="(rule, index) in fx.rules" :key="index" class="flex items-center gap-1">
                <select v-model="rule.operator" class="w-24 rounded border border-pbi-pane-border px-1 py-0.5 text-[10px]">
                  <option value="gte">≥</option><option value="gt">&gt;</option><option value="lte">≤</option><option value="lt">&lt;</option><option value="eq">=</option><option value="neq">≠</option>
                </select>
                <input v-model="rule.value" type="text" class="min-w-0 flex-1 rounded border border-pbi-pane-border px-1 py-0.5 text-[10px]" placeholder="Valore" />
                <input v-model="rule.color" type="color" class="format-color" />
                <button class="text-red-600" @click="fx.rules.splice(index, 1)">✕</button>
              </div>
              <button class="add-filter-btn" @click="fx.rules.push({ operator: 'gte', value: 0, color: '#107c41' })">＋ Regola</button>
            </div>
          </div>
          <div class="flex justify-end gap-2 border-t border-pbi-pane-border bg-slate-50 px-3 py-2">
            <button class="pbi-btn pbi-btn-ghost" @click="fx.open = false">Annulla</button>
            <button class="pbi-btn pbi-btn-primary" @click="applyFx">Applica</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { computed, reactive, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';
import { useThemeStore } from 'pybi-theme-store';

export default {
  name: 'FormattingPane',
  setup() {
const store = useReportStore();
const themeStore = useThemeStore();
const tab = ref('visual');

const fx = reactive({
  open: false,
  target: 'dataColors',
  mode: 'gradient',
  field: '',
  minColor: '#f8696b',
  maxColor: '#63be7b',
  rules: [{ operator: 'gte', value: 0, color: '#107c41' }],
});

const visual = computed(() => store.selectedVisual);
const props = computed(() => visual.value?.properties || {});
const dataColors = computed(() => props.value.dataColors || themeStore.dataColors);
const labels = computed(() => props.value.dataLabels || {});
const legend = computed(() => props.value.legend || {});
const xAxis = computed(() => props.value.xAxis || {});
const yAxis = computed(() => props.value.yAxis || {});
const gridlines = computed(() => props.value.gridlines || {});
const border = computed(() => props.value.border || {});
const shadow = computed(() => props.value.shadow || {});
const header = computed(() => props.value.header || {});
const pagePreset = computed(() => {
  const page = store.activePage;
  if (!page) return '16:9';
  if (page.width === 1280 && page.height === 720) return '16:9';
  if (page.width === 960 && page.height === 720) return '4:3';
  if (page.width === 320 && page.height === 240) return 'tooltip';
  return 'custom';
});

const fxFields = computed(() => {
  const result = [];
  const visualFields = visual.value?.data_buckets || {};
  Object.values(visualFields).forEach(value => {
    const list = Array.isArray(value) ? value : value ? [value] : [];
    list.forEach(field => {
      const column = typeof field === 'string' ? field : field.column || field.name;
      if (!column || result.some(item => item.column === column)) return;
      result.push({
        column,
        table: typeof field === 'string' ? '' : field.table || '',
        value: typeof field === 'string' ? column : `${field.table || ''}|${column}`,
        label: typeof field === 'string' ? column : `${field.table ? `${field.table}.` : ''}${field.display_name || field.name || column}`,
      });
    });
  });
  if (!result.length) {
    (store.tables || []).forEach(table => {
      (table.columns || []).slice(0, 20).forEach(column => {
        result.push({ column: column.name, table: table.name, value: `${table.name}|${column.name}`, label: `${table.name}.${column.name}` });
      });
    });
  }
  return result;
});

function set(key, value) {
  if (!visual.value) return;
  store.updateVisualProperties(visual.value.id, { [key]: value });
}

function patch(key, patchValue) {
  if (!visual.value) return;
  store.updateVisualProperties(visual.value.id, { [key]: patchValue });
}

function setColor(index, color) {
  if (!visual.value) return;
  const colors = [...dataColors.value];
  colors[index] = color;
  store.updateVisualProperties(visual.value.id, { dataColors: colors });
}

function addColor() {
  if (!visual.value) return;
  const colors = [...dataColors.value, '#118DFF'];
  store.updateVisualProperties(visual.value.id, { dataColors: colors });
}

function removeColor(index) {
  if (!visual.value) return;
  const colors = dataColors.value.filter((_, idx) => idx !== index);
  store.updateVisualProperties(visual.value.id, { dataColors: colors });
}

function applyPalette() {
  if (!visual.value) return;
  store.updateVisualProperties(visual.value.id, { dataColors: [...themeStore.dataColors] });
}

function toggleHeaderIcon(icon, checked) {
  if (!visual.value) return;
  const current = [...(header.value.icons || [])];
  const next = checked ? [...new Set([...current, icon])] : current.filter(item => item !== icon);
  patch('header', { ...header.value, icons: next });
}

function updatePage(patchValue) {
  if (!store.activePage) return;
  if (patchValue.width !== undefined) patchValue.width = Math.max(200, Math.min(7680, patchValue.width));
  if (patchValue.height !== undefined) patchValue.height = Math.max(200, Math.min(4320, patchValue.height));
  store.updatePageSettings(store.activePage.id, patchValue);
}

function applyPreset(value) {
  if (!store.activePage) return;
  if (value === 'custom') return;
  store.setPageSize(store.activePage.id, value);
}

function changeTheme(event) {
  const key = event.target.value;
  themeStore.applyTheme(key);
  store.layout.theme = themeStore.currentTheme.layoutTheme;
  store.markDirty();
}

function openFx(target = 'dataColors') {
  fx.target = target;
  fx.open = true;
}

function applyFx() {
  if (!visual.value) {
    fx.open = false;
    return;
  }
  const selectedField = fxFields.value.find(field => field.value === fx.field) || null;
  const config = {
    target: fx.target,
    mode: fx.mode,
    field: selectedField,
    minColor: fx.minColor,
    maxColor: fx.maxColor,
    rules: fx.rules.map(rule => ({ ...rule })),
  };
  const patchValue = { conditionalFormatting: config };
  if (fx.mode === 'gradient') {
    if (fx.target === 'dataColors') patchValue.dataColors = [fx.minColor, fx.maxColor];
    if (fx.target === 'background') patchValue.background = fx.minColor;
    if (fx.target === 'fontColor') patchValue.titleColor = fx.minColor;
  } else if (fx.rules.length) {
    if (fx.target === 'dataColors') patchValue.dataColors = fx.rules.map(rule => rule.color);
    if (fx.target === 'background') patchValue.background = fx.rules[0].color;
    if (fx.target === 'fontColor') patchValue.titleColor = fx.rules[0].color;
  }
  store.updateVisualProperties(visual.value.id, patchValue);
  fx.open = false;
}

    return {
      store,
      themeStore,
      tab,
      fx,
      visual,
      props,
      dataColors,
      labels,
      legend,
      xAxis,
      yAxis,
      gridlines,
      border,
      shadow,
      header,
      pagePreset,
      fxFields,
      set,
      patch,
      setColor,
      addColor,
      removeColor,
      applyPalette,
      toggleHeaderIcon,
      updatePage,
      applyPreset,
      changeTheme,
      openFx,
      applyFx,
    };
  },
};
</script>

<style scoped>
.format-section {
  border-bottom: 1px solid #e1dfdd;
}
.format-section-title {
  display: block;
  cursor: pointer;
  padding: 5px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #252423;
  background: #fafafa;
}
.format-section-title:hover {
  background: #f3f2f1;
}
.format-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 10px;
  color: #605e5c;
}
.format-control {
  min-width: 0;
  max-width: 130px;
  flex: 1;
  border: 1px solid #d2d0ce;
  border-radius: 2px;
  padding: 1px 4px;
  font-size: 10px;
  background: #ffffff;
  color: #252423;
}
.format-color {
  width: 30px;
  height: 18px;
  padding: 0;
  border: 1px solid #d2d0ce;
  border-radius: 2px;
  background: #ffffff;
}
.fx-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 16px;
  border: 1px solid #d2d0ce;
  border-radius: 2px;
  font-family: monospace;
  font-size: 9px;
  font-weight: bold;
  font-style: italic;
  color: #0078d4;
}
.fx-btn:hover {
  background: #eff6fc;
}
</style>
