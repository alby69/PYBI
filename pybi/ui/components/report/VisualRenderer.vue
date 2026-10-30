<template>
  <div class="visual-renderer flex h-full min-h-0 w-full flex-col overflow-hidden text-pbi-sm text-pbi-text">
    <div v-if="loading" class="flex flex-1 items-center justify-center text-pbi-text-muted">
      <div class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-pbi-accent border-t-transparent"></div>
      Caricamento dati…
    </div>

    <div v-else-if="error" class="flex flex-1 flex-col items-center justify-center gap-1 p-3 text-center text-red-600">
      <span class="text-lg">⚠</span>
      <span class="text-pbi-xs">{{ error }}</span>
    </div>

    <div v-else-if="!hasData && !['text', 'shape', 'image'].includes(type)" class="flex flex-1 flex-col items-center justify-center gap-1 p-3 text-center text-pbi-text-muted">
      <span class="text-2xl opacity-40">📊</span>
      <span class="text-pbi-xs">Aggiungi campi nei secchielli dati</span>
    </div>

    <template v-else>
      <!-- Card / KPI -->
      <div v-if="['card', 'kpi', 'multi_row_card'].includes(type)" class="flex flex-1 flex-col items-center justify-center gap-1 overflow-hidden p-3">
        <div v-for="item in cardValues" :key="item.label" class="flex w-full items-baseline justify-between gap-2">
          <span class="truncate text-pbi-xs text-pbi-text-muted">{{ item.label }}</span>
          <span class="truncate text-pbi-kpi font-bold text-pbi-accent" :style="{ fontSize: cardFontSize }">{{ item.value }}</span>
        </div>
      </div>

      <!-- Gauge -->
      <div v-else-if="type === 'gauge'" class="flex flex-1 flex-col items-center justify-center gap-2 p-4">
        <span class="text-3xl font-bold text-pbi-accent">{{ cardValues[0]?.value || '—' }}</span>
        <div class="h-3 w-full overflow-hidden rounded-full bg-slate-200">
          <div class="h-full rounded-full bg-pbi-accent transition-all" :style="{ width: gaugePercent + '%' }"></div>
        </div>
        <span class="text-pbi-xs text-pbi-text-muted">{{ gaugePercent.toFixed(1) }}% dell'obiettivo</span>
      </div>

      <!-- Slicer -->
      <div v-else-if="type === 'slicer'" class="flex flex-1 flex-col overflow-hidden p-2">
        <div class="mb-1 flex items-center justify-between text-pbi-xs font-semibold text-pbi-text-muted">
          <span>Seleziona</span>
          <span>{{ selectedSlicerValues.length }} / {{ slicerValues.length }}</span>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto rounded border border-pbi-pane-border bg-white p-1">
          <label v-for="value in slicerValues" :key="String(value)" class="flex cursor-pointer items-center gap-1.5 rounded px-1 py-0.5 hover:bg-blue-50">
            <input v-model="selectedSlicerValues" type="checkbox" :value="value" class="h-3 w-3 accent-blue-600" />
            <span class="truncate">{{ value }}</span>
          </label>
        </div>
      </div>

      <!-- Table / Matrix -->
      <div v-else-if="type === 'table' || type === 'matrix'" class="flex flex-1 flex-col overflow-hidden">
        <div class="min-h-0 flex-1 overflow-auto">
          <table class="w-full border-collapse text-left text-pbi-xs">
            <thead class="sticky top-0 z-10">
              <tr class="bg-pbi-header text-pbi-text">
                <th v-for="column in tableColumns" :key="column" class="whitespace-nowrap border-b border-r border-pbi-pane-border px-2 py-1 font-semibold">
                  {{ column }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in tableRows" :key="index" :class="index % 2 ? 'bg-slate-50' : 'bg-white'">
                <td v-for="column in tableColumns" :key="column" class="whitespace-nowrap border-b border-r border-slate-100 px-2 py-0.5">
                  {{ formatCell(row[column]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Pie / Donut -->
      <div v-else-if="type === 'pie_chart' || type === 'donut_chart'" class="flex flex-1 items-center justify-center gap-3 overflow-hidden p-2">
        <div class="relative h-full max-h-[180px] w-1/2 min-w-[80px] max-w-[180px]">
          <div class="absolute inset-0 rounded-full" :style="{ background: pieGradient }"></div>
          <div v-if="type === 'donut_chart'" class="absolute inset-[26%] rounded-full bg-white"></div>
        </div>
        <div class="flex min-w-0 flex-1 flex-col gap-0.5 overflow-y-auto">
          <div v-for="(item, index) in pieItems" :key="item.label" class="flex items-center gap-1.5 truncate">
            <span class="h-2 w-2 shrink-0 rounded-sm" :style="{ backgroundColor: colors[index % colors.length] }"></span>
            <span class="truncate" :title="item.label">{{ item.label }}</span>
            <span class="ml-auto shrink-0 text-pbi-text-muted">{{ item.percent.toFixed(1) }}%</span>
          </div>
        </div>
      </div>

      <!-- Treemap -->
      <div v-else-if="type === 'treemap'" class="flex flex-1 flex-wrap gap-0.5 overflow-hidden p-1">
        <div
          v-for="(item, index) in treemapItems"
          :key="item.label"
          class="flex min-h-[24px] min-w-[48px] flex-col justify-center overflow-hidden rounded px-1.5 py-1 text-white"
          :style="{ flexGrow: Math.max(1, item.value), flexBasis: '22%', backgroundColor: colors[index % colors.length] }"
          :title="`${item.label}: ${formatNumber(item.value)}`"
        >
          <span class="truncate text-[10px] font-semibold">{{ item.label }}</span>
          <span class="truncate text-[9px] opacity-90">{{ formatNumber(item.value) }}</span>
        </div>
      </div>

      <!-- Line / Area / Scatter -->
      <div v-else-if="['line_chart', 'area_chart', 'combo_chart', 'scatter_chart'].includes(type)" class="relative flex flex-1 flex-col overflow-hidden p-2">
        <svg class="h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
          <g v-if="gridlinesVisible">
            <line v-for="tick in 5" :key="`h-${tick}`" x1="0" :y1="tick * 20" x2="100" :y2="tick * 20" stroke="#e1dfdd" stroke-width="0.4" />
          </g>
          <template v-for="(series, index) in lineSeries" :key="series.name">
            <polygon
              v-if="type === 'area_chart'"
              :points="`0,100 ${series.points} 100,100`"
              :fill="colors[index % colors.length]"
              fill-opacity="0.18"
              stroke="none"
            />
            <polyline
              :points="series.points"
              fill="none"
              :stroke="colors[index % colors.length]"
              :stroke-width="type === 'scatter_chart' ? 0 : 1.8"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            <circle
              v-for="(point, pointIndex) in series.rawPoints"
              :key="`${series.name}-${pointIndex}`"
              :cx="point.x"
              :cy="point.y"
              :r="type === 'scatter_chart' ? 2.2 : 1.2"
              :fill="colors[index % colors.length]"
            />
          </template>
        </svg>
        <div v-if="categories.length" class="flex shrink-0 justify-between gap-1 overflow-hidden text-[9px] text-pbi-text-muted">
          <span v-for="category in categories.slice(0, 8)" :key="category" class="truncate">{{ category }}</span>
        </div>
        <div class="mt-1 flex flex-wrap gap-2">
          <span v-for="(series, index) in lineSeries" :key="`legend-${series.name}`" class="flex items-center gap-1 text-[9px]">
            <span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: colors[index % colors.length] }"></span>
            {{ series.name }}
          </span>
        </div>
      </div>

      <!-- Bar / Column / Stacked -->
      <div v-else-if="isBarLike" class="flex flex-1 flex-col overflow-hidden p-2">
        <div
          v-if="type === 'bar_chart' || type === 'stacked_bar_chart'"
          class="flex min-h-0 flex-1 flex-col justify-center gap-1 overflow-y-auto"
        >
          <div v-for="(category, catIndex) in categories" :key="category" class="flex items-center gap-1.5">
            <span class="w-20 shrink-0 truncate text-right text-[9px] text-pbi-text-muted" :title="category">{{ category }}</span>
            <div class="flex min-w-0 flex-1 flex-col gap-0.5">
              <div v-for="(series, sIndex) in chartSeries" :key="series.name" class="flex items-center gap-1">
                <div
                  class="h-3 rounded-sm transition-all"
                  :style="{ width: barWidth(series.values[catIndex], series.name) + '%', backgroundColor: colors[sIndex % colors.length] }"
                ></div>
                <span v-if="dataLabelsVisible" class="text-[8px] text-pbi-text-muted">{{ formatNumber(series.values[catIndex]) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="relative flex min-h-0 flex-1 items-end gap-1 overflow-x-auto border-b border-pbi-pane-border pb-1">
          <div v-for="(category, catIndex) in categories" :key="category" class="flex h-full min-w-[24px] flex-1 flex-col items-center justify-end gap-0.5">
            <div class="flex w-full flex-1 items-end justify-center gap-0.5">
              <div
                v-for="(series, sIndex) in chartSeries"
                :key="series.name"
                class="max-w-[28px] flex-1 rounded-t-sm transition-all"
                :style="{ height: barHeight(series.values[catIndex], series.name) + '%', backgroundColor: colors[sIndex % colors.length] }"
                :title="`${series.name}: ${formatNumber(series.values[catIndex])}`"
              ></div>
            </div>
            <span class="w-full truncate text-center text-[8px] text-pbi-text-muted" :title="category">{{ category }}</span>
            <span v-if="dataLabelsVisible" class="text-[8px] font-semibold">{{ formatNumber(chartSeries[0]?.values[catIndex]) }}</span>
          </div>
        </div>
        <div v-if="chartSeries.length > 1 && legendVisible" class="mt-1 flex flex-wrap justify-center gap-2">
          <span v-for="(series, index) in chartSeries" :key="`bar-legend-${series.name}`" class="flex items-center gap-1 text-[9px]">
            <span class="h-1.5 w-1.5 rounded-sm" :style="{ backgroundColor: colors[index % colors.length] }"></span>
            {{ series.name }}
          </span>
        </div>
      </div>

      <!-- Text / Shape / Image -->
      <div v-else-if="type === 'text'" class="flex flex-1 items-center justify-center whitespace-pre-wrap p-3 text-center">
        {{ visual.properties?.text || visual.title }}
      </div>
      <div v-else-if="type === 'shape'" class="flex flex-1 items-center justify-center p-2">
        <div class="h-full w-full rounded" :style="{ backgroundColor: visual.properties?.fill || colors[0] }"></div>
      </div>
      <div v-else-if="type === 'image'" class="flex flex-1 items-center justify-center overflow-hidden p-2">
        <img v-if="visual.properties?.imageUrl" :src="visual.properties.imageUrl" class="max-h-full max-w-full object-contain" alt="" />
        <span v-else class="text-pbi-xs text-pbi-text-muted">Configura un URL immagine</span>
      </div>

      <!-- Fallback table -->
      <div v-else class="flex flex-1 flex-col overflow-auto p-2">
        <table class="w-full text-left text-pbi-xs">
          <thead>
            <tr>
              <th v-for="column in tableColumns" :key="column" class="border-b border-pbi-pane-border px-1 py-1">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in tableRows" :key="index">
              <td v-for="column in tableColumns" :key="column" class="border-b border-slate-100 px-1 py-0.5">{{ formatCell(row[column]) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script>
import { computed, ref, watch } from 'vue';
import { useReportStore } from 'pybi-report-store';
import { useThemeStore } from 'pybi-theme-store';

export default {
  name: 'VisualRenderer',
  props: {
    visual: { type: Object, required: true },
    data: { type: Object, default: null },
    compact: { type: Boolean, default: false },
  },
  setup(props) {
const store = useReportStore();
const themeStore = useThemeStore();
const selectedSlicerValues = ref([]);

const type = computed(() => String(props.visual.type || 'bar_chart').toLowerCase());
const payload = computed(() => props.data || store.visualData[props.visual.id] || {});
const rows = computed(() => payload.value.rows || []);
const columns = computed(() => payload.value.columns || []);
const loading = computed(() => !props.data && !!store.visualLoading[props.visual.id]);
const error = computed(() => payload.value.error || '');
const hasData = computed(() => rows.value.length > 0);

const properties = computed(() => props.visual.properties || {});
const colors = computed(() => {
  const custom = properties.value.dataColors || [];
  return custom.length ? custom : themeStore.dataColors;
});
const dataLabelsVisible = computed(() => !!properties.value.dataLabels?.show);
const legendVisible = computed(() => properties.value.legend?.show !== false);
const gridlinesVisible = computed(() => properties.value.gridlines?.show !== false);
const isBarLike = computed(() => ['bar_chart', 'column_chart', 'stacked_bar_chart', 'stacked_column', 'stacked_column_100'].includes(type.value));

const numericColumns = computed(() => columns.value.filter(column => rows.value.some(row => typeof row[column] === 'number')));
const valueColumn = computed(() => {
  if (columns.value.includes('value')) return 'value';
  return numericColumns.value[0] || columns.value[columns.value.length - 1] || null;
});
const categoryColumn = computed(() => {
  if (columns.value.includes('category')) return 'category';
  const nonNumeric = columns.value.find(column => !numericColumns.value.includes(column));
  return nonNumeric || columns.value[0] || null;
});
const seriesColumn = computed(() => (columns.value.includes('series') ? 'series' : null));

const categories = computed(() => {
  const column = categoryColumn.value;
  if (!column) return [];
  const seen = new Set();
  const values = [];
  rows.value.forEach(row => {
    const value = row[column];
    const label = value === null || value === undefined ? '—' : String(value);
    if (!seen.has(label)) {
      seen.add(label);
      values.push(label);
    }
  });
  return values;
});

const chartSeries = computed(() => {
  const category = categoryColumn.value;
  const value = valueColumn.value;
  if (!category || !value) return [];
  const seriesNames = seriesColumn.value
    ? [...new Set(rows.value.map(row => String(row[seriesColumn.value] ?? 'Serie')))]
    : ['Valore'];

  return seriesNames.map(name => {
    const values = categories.value.map(categoryValue => {
      let total = 0;
      rows.value.forEach(row => {
        const rowCategory = String(row[category] ?? '—');
        const rowSeries = seriesColumn.value ? String(row[seriesColumn.value] ?? 'Serie') : 'Valore';
        if (rowCategory === categoryValue && rowSeries === name) {
          const number = Number(row[value]);
          total += Number.isFinite(number) ? number : 0;
        }
      });
      return total;
    });
    return { name, values };
  });
});

const maxValue = computed(() => {
  let max = 0;
  chartSeries.value.forEach(series => {
    series.values.forEach(value => { max = Math.max(max, Math.abs(Number(value) || 0)); });
  });
  return max || 1;
});

const categoryTotals = computed(() => categories.value.map((_, index) => (
  chartSeries.value.reduce((total, series) => total + Math.abs(series.values[index] || 0), 0) || 1
)));

function barWidth(value, _seriesName) {
  return Math.max(0, Math.min(100, (Math.abs(Number(value) || 0) / maxValue.value) * 100));
}

function barHeight(value, _seriesName) {
  if (type.value === 'stacked_column_100') {
    return Math.max(0, Math.min(100, (Math.abs(Number(value) || 0) / maxValue.value) * 100));
  }
  return Math.max(0, Math.min(100, (Math.abs(Number(value) || 0) / maxValue.value) * 100));
}

const lineSeries = computed(() => {
  const seriesList = chartSeries.value;
  if (!seriesList.length) return [];
  const count = Math.max(1, categories.value.length - 1);
  return seriesList.map(series => {
    const rawPoints = series.values.map((value, index) => ({
      x: categories.value.length === 1 ? 50 : (index / count) * 100,
      y: 100 - Math.max(0, Math.min(100, (Math.abs(Number(value) || 0) / maxValue.value) * 92)) - 4,
    }));
    return {
      name: series.name,
      rawPoints,
      points: rawPoints.map(point => `${point.x},${point.y}`).join(' '),
    };
  });
});

const pieItems = computed(() => {
  const firstSeries = chartSeries.value[0];
  if (!firstSeries) return [];
  const total = firstSeries.values.reduce((sum, value) => sum + Math.abs(Number(value) || 0), 0) || 1;
  return categories.value.map((label, index) => ({
    label,
    value: firstSeries.values[index] || 0,
    percent: (Math.abs(firstSeries.values[index] || 0) / total) * 100,
  }));
});

const pieGradient = computed(() => {
  if (!pieItems.value.length) return '#e1dfdd';
  let accumulated = 0;
  const stops = pieItems.value.map((item, index) => {
    const start = accumulated;
    accumulated += item.percent;
    return `${colors.value[index % colors.value.length]} ${start}% ${accumulated}%`;
  });
  return `conic-gradient(${stops.join(', ')})`;
});

const treemapItems = computed(() => pieItems.value.map(item => ({ label: item.label, value: Math.abs(item.value) || 0 })));
const cardValues = computed(() => {
  if (!rows.value.length) return [];
  const first = rows.value[0];
  if (valueColumn.value && valueColumn.value in first) {
    return [{ label: properties.value.yAxis?.title || '', value: formatNumber(first[valueColumn.value]) }];
  }
  return columns.value.slice(0, 3).map(column => ({ label: column, value: formatCell(first[column]) }));
});
const cardFontSize = computed(() => `${Math.max(18, Math.min(40, Number(properties.value.titleFontSize || 14) * 2.2))}px`);
const gaugePercent = computed(() => {
  const value = Number(rows.value[0]?.[valueColumn.value] || 0);
  const max = Number(properties.value.gaugeMax || 100) || 100;
  return Math.max(0, Math.min(100, (value / max) * 100));
});

const slicerValues = computed(() => {
  const column = categoryColumn.value || columns.value[0];
  if (!column) return [];
  return [...new Set(rows.value.map(row => row[column]).filter(value => value !== null && value !== undefined))];
});

const tableColumns = computed(() => {
  if (columns.value.length) return columns.value;
  return rows.value.length ? Object.keys(rows.value[0]) : [];
});
const tableRows = computed(() => rows.value.slice(0, 200));

function formatNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return value === null || value === undefined ? '—' : String(value);
  const labels = properties.value.dataLabels || {};
  const decimals = Number(labels.decimals || 0);
  let display = number;
  let suffix = '';
  if (labels.units === 'thousands') { display = number / 1000; suffix = 'K'; }
  else if (labels.units === 'millions') { display = number / 1000000; suffix = 'M'; }
  else if (labels.units === 'billions') { display = number / 1000000000; suffix = 'B'; }
  return `${display.toLocaleString(undefined, { maximumFractionDigits: decimals, minimumFractionDigits: decimals })}${suffix}`;
}

function formatCell(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number') return formatNumber(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

watch(() => props.visual.id, () => { selectedSlicerValues.value = []; });

    return {
      store,
      themeStore,
      selectedSlicerValues,
      type,
      payload,
      rows,
      columns,
      loading,
      error,
      hasData,
      properties,
      colors,
      dataLabelsVisible,
      legendVisible,
      gridlinesVisible,
      isBarLike,
      numericColumns,
      valueColumn,
      categoryColumn,
      seriesColumn,
      categories,
      chartSeries,
      maxValue,
      categoryTotals,
      barWidth,
      barHeight,
      lineSeries,
      pieItems,
      pieGradient,
      treemapItems,
      cardValues,
      cardFontSize,
      gaugePercent,
      slicerValues,
      tableColumns,
      tableRows,
      formatNumber,
      formatCell,
    };
  },
};
</script>
