import { GridLayout, GridItem } from 'https://cdn.jsdelivr.net/npm/grid-layout-plus@1.1.1/dist/grid-layout-plus.mjs';

export default {
    template: `
        <div class="dashboard-grid-container relative w-full h-full min-h-[500px]">
            <!-- Canvas Toolbar & Controls Header -->
            <div class="flex items-center justify-between bg-slate-100 border-b px-3 py-1.5 text-xs text-gray-700 font-sans rounded-t">
                <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-800">PYBI Dashboard Canvas</span>
                    <span v-if="localPrintPreview" class="px-2 py-0.5 rounded bg-blue-600 text-white font-semibold text-[10px]">
                        🖨️ Anteprima Stampa A4 Attiva
                    </span>
                </div>
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        @click="localPrintPreview = !localPrintPreview"
                        class="px-2.5 py-1 rounded text-xs font-medium border flex items-center gap-1 transition cursor-pointer"
                        :class="localPrintPreview ? 'bg-blue-600 text-white border-blue-700 shadow-sm' : 'bg-white text-gray-700 hover:bg-gray-50 border-gray-300'"
                        title="Toggle Print Preview Mode (A4 Page Break Overlay)"
                    >
                        🖨️ {{ localPrintPreview ? 'Chiudi Anteprima Stampa' : 'Vista Anteprima Stampa' }}
                    </button>
                </div>
            </div>

            <div class="relative w-full h-full">
                <!-- Smart Guides Overlay -->
                <div v-if="activeGuides.x.length || activeGuides.y.length" class="absolute inset-0 pointer-events-none z-50 overflow-hidden">
                    <div
                        v-for="(gx, idx) in activeGuides.x"
                        :key="'gx-'+idx"
                        class="absolute top-0 bottom-0 border-r-2 border-dashed border-blue-500 shadow-sm"
                        :style="{ left: (gx / colNum * 100) + '%' }"
                    ></div>
                    <div
                        v-for="(gy, idx) in activeGuides.y"
                        :key="'gy-'+idx"
                        class="absolute left-0 right-0 border-b-2 border-dashed border-blue-500 shadow-sm"
                        :style="{ top: (gy * (rowHeight + 10) + 10) + 'px' }"
                    ></div>
                </div>

                <!-- Print Preview Page Break Overlay -->
                <div v-if="localPrintPreview" class="absolute inset-0 pointer-events-none z-40 bg-slate-200/20 overflow-hidden">
                    <div
                        v-for="p in calcPrintPages()"
                        :key="'page-'+p.num"
                        class="absolute left-0 right-0 border-b-2 border-dashed border-red-500 flex justify-between items-center px-4"
                        :style="{ top: p.topPx + 'px' }"
                    >
                        <span class="bg-red-600 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow">
                            Interruzione Pagina PDF #{{ p.num }} (A4)
                        </span>
                        <span class="text-red-600 font-mono text-[10px] bg-white/80 px-1.5 rounded border border-red-300">
                            Quota: {{ p.topPx }}px
                        </span>
                    </div>
                </div>

                <GridLayout
                    v-model:layout="localLayout"
                    :col-num="colNum"
                    :row-height="rowHeight"
                    :is-draggable="isDraggable"
                    :is-resizable="isResizable"
                    :vertical-compact="true"
                    :use-css-transforms="true"
                    class="w-full bg-slate-50 border border-t-0 rounded-b p-2"
                    @layout-updated="onLayoutUpdated"
                >
                    <GridItem
                        v-for="item in localLayout"
                        :key="item.i"
                        :x="item.x"
                        :y="item.y"
                        :w="item.w"
                        :h="item.h"
                        :i="item.i"
                        :is-draggable="isDraggable"
                        :is-resizable="isResizable"
                        class="bg-white border rounded shadow-sm p-3 flex flex-col justify-between overflow-hidden cursor-pointer"
                        @moved="onItemMoved"
                        @resized="onItemResized"
                        @drag="onItemDragging"
                        @resize="onItemResizing"
                        @drag-end="onItemEnd"
                        @resize-end="onItemEnd"
                        @click="onItemClick(item)"
                    >
                        <div class="font-semibold text-sm border-b pb-1 mb-2 flex items-center justify-between text-gray-800">
                            <span>{{ item.title || 'Widget ' + item.i }}</span>
                            <span class="flex items-center gap-1">
                                <span v-if="item.drill_action || item.drillAction" class="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-bold" title="Drill-Through abilitato">
                                    🔍 Drill
                                </span>
                                <span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 uppercase">{{ item.type || 'card' }}</span>
                                <button
                                    type="button"
                                    class="edit-widget-btn text-xs px-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 cursor-pointer"
                                    title="Edit widget"
                                    @mousedown.stop
                                    @click.stop="$emit('edit_widget', { widget: item })">✏️</button>
                                <button
                                    type="button"
                                    class="delete-widget-btn text-xs px-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 cursor-pointer"
                                    title="Elimina questo widget"
                                    @mousedown.stop
                                    @click.stop="$emit('delete_widget', { widget: item })">🗑️</button>
                            </span>
                        </div>

                        <!-- Widget Content Types -->
                        <div class="flex-grow flex items-center justify-center overflow-auto p-1 text-center">
                            <div v-if="item.type === 'kpi'" class="flex flex-col items-center">
                                <span v-if="item.kpi && item.kpi.error" class="text-amber-600 italic text-xs">{{ item.kpi.subtitle }}</span>
                                <template v-else-if="item.kpi">
                                    <span class="text-3xl font-extrabold text-blue-600">{{ item.kpi.value }}</span>
                                    <span class="text-xs text-emerald-600 font-medium">{{ item.kpi.subtitle }}</span>
                                </template>
                                <template v-else>
                                    <span class="text-3xl font-extrabold text-blue-600">{{ item.value || '$124,500' }}</span>
                                    <span class="text-xs text-emerald-600 font-medium">{{ item.subtitle || '▲ +12.5% vs last month' }}</span>
                                </template>
                            </div>

                            <div v-else-if="item.type === 'chart'" class="w-full h-full flex flex-col">
                                <div class="text-xs text-gray-500 mb-1 font-mono truncate">{{ item.chartType || 'Bar Chart' }}</div>
                                <div v-if="item.chart && item.chart.error" class="flex-grow flex items-center text-amber-600 italic text-xs">{{ item.chart.error }}</div>
                                <div v-else-if="item.chart && item.chart.series && item.chart.series.length" class="flex-grow min-h-0">
                                    <div v-if="item.chart.kind === 'pie'" class="w-full h-full flex items-center justify-center gap-2">
                                        <svg viewBox="0 0 42 42" class="h-full max-h-[120px] aspect-square">
                                            <path v-for="(slice, si) in pieSlices(item.chart)" :key="si" :d="slice.d" :fill="chartColors[si % chartColors.length]"></path>
                                        </svg>
                                        <div class="text-[9px] leading-tight max-h-full overflow-hidden">
                                            <div v-for="(slice, si) in pieSlices(item.chart)" :key="si" class="flex items-center gap-1">
                                                <span class="w-2 h-2 inline-block shrink-0" :style="{ background: chartColors[si % chartColors.length] }"></span>
                                                <span>{{ slice.label }}</span>
                                                <span class="text-gray-500">{{ slice.value }}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-else-if="item.chart.kind === 'line'" class="w-full h-full flex flex-col">
                                        <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="w-full flex-grow min-h-0">
                                            <polyline
                                                v-for="(points, si) in linePaths(item.chart)"
                                                :key="si"
                                                :points="points"
                                                fill="none"
                                                :stroke="chartColors[si % chartColors.length]"
                                                stroke-width="2"
                                                vector-effect="non-scaling-stroke"
                                            ></polyline>
                                        </svg>
                                        <div class="flex justify-between text-[8px] text-gray-400 px-1 shrink-0">
                                            <span>{{ item.chart.labels[0] }}</span>
                                            <span>{{ item.chart.labels[item.chart.labels.length - 1] }}</span>
                                        </div>
                                    </div>
                                    <div v-else class="w-full h-full flex items-end gap-[2px]">
                                        <div v-for="(label, li) in item.chart.labels" :key="li" class="flex-1 h-full flex flex-col min-w-0">
                                            <div class="flex-1 min-h-0 flex items-end justify-center gap-[1px]">
                                                <div
                                                    v-for="(s, si) in item.chart.series"
                                                    :key="si"
                                                    class="w-1/2 max-w-[8px]"
                                                    :style="{ height: barHeight(item.chart, s.values[li]) + '%', background: chartColors[si % chartColors.length] }"
                                                ></div>
                                            </div>
                                            <span class="text-[7px] text-gray-400 truncate w-full text-center shrink-0">{{ shortLabel(label) }}</span>
                                        </div>
                                    </div>
                                    <div v-if="item.chart.truncated" class="text-[9px] text-gray-400 text-right mt-1">showing first {{ item.chart.labels.length }} rows</div>
                                </div>
                                <div v-else class="flex-grow flex items-center text-gray-500 italic text-xs">No data source bound yet</div>
                            </div>

                            <div v-else-if="item.type === 'table'" class="w-full h-full overflow-auto text-xs text-left">
                                <template v-if="item.columns && item.columns.length">
                                    <table class="w-full border-collapse">
                                        <thead>
                                            <tr class="bg-gray-100 text-gray-700">
                                                <th v-for="col in item.columns" :key="col" class="p-1 border text-left">{{ col }}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="(row, ri) in item.rows_data || []" :key="ri">
                                                <td v-for="(cell, ci) in row" :key="ci" class="p-1 border">{{ cell === null || cell === undefined ? '—' : cell }}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                    <div v-if="item.truncated" class="text-[9px] text-gray-400 text-right mt-1">
                                        showing first {{ (item.rows_data || []).length }} of {{ item.row_count }} rows
                                    </div>
                                </template>
                                <div v-else-if="item.data_error" class="text-amber-600 italic">{{ item.data_error }}</div>
                                <div v-else class="text-gray-500 italic">No data source bound yet</div>
                            </div>

                            <!-- Tablix Widget -->
                            <div v-else-if="item.type === 'tablix' || item.type === 'report_tablix'" class="w-full h-full flex flex-col text-left overflow-auto text-xs">
                                <div class="flex items-center justify-between pb-1 mb-1 border-b text-[10px]">
                                    <div class="flex items-center gap-1 font-semibold text-slate-700">
                                        <span>📊 Tablix:</span>
                                        <span class="font-mono text-blue-600 font-bold">{{ (item.row_groups || item.rowGroups || []).join(' › ') || 'Groups' }}</span>
                                    </div>
                                </div>
                                <div v-if="item.data && item.data.length" class="flex-grow overflow-auto border rounded">
                                    <table class="w-full border-collapse font-mono text-[10px]">
                                        <thead>
                                            <tr class="bg-slate-100 border-b text-slate-800 font-bold">
                                                <th class="p-1 border-r text-left bg-slate-200">{{ (item.row_groups || item.rowGroups || []).join(' / ') || 'Group' }}</th>
                                                <th v-for="col in getTablixMeasures(item)" :key="col" class="p-1 border-r text-right bg-slate-100">{{ col }}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="(row, rIdx) in getTablixRows(item)" :key="rIdx" class="hover:bg-blue-50/50 border-b cursor-pointer" @click="$emit('drill_click', { row, widget: item })">
                                                <td class="p-1 border-r font-semibold text-slate-700 bg-slate-50">{{ row.label }}</td>
                                                <td v-for="col in getTablixMeasures(item)" :key="col" class="p-1 border-r text-right" :style="getTablixStyle(item, row.values[col], col)">
                                                    {{ formatCell(row.values[col]) }}
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                <div v-else-if="item.data_error" class="text-amber-600 italic text-[10px] p-2 bg-amber-50 rounded border border-amber-200">
                                    {{ item.data_error }}
                                </div>
                                <div v-else class="text-amber-700 italic text-[10px] p-2 bg-amber-50 rounded border border-amber-200">
                                    ⚠️ No Tablix Data. Select group and measure fields in configurator.
                                </div>
                            </div>

                            <!-- Pivot Table Widget -->
                            <div v-else-if="item.type === 'pivot'" class="w-full h-full flex flex-col text-left overflow-auto text-xs">
                                <div class="flex items-center justify-between pb-1 mb-1 border-b text-[10px]">
                                    <div class="flex items-center gap-1">
                                        <span class="font-semibold text-gray-600">Agg:</span>
                                        <span class="font-mono bg-gray-100 px-1 rounded text-blue-700 font-bold">{{ item.aggregator_name || 'Sum' }}</span>
                                        <span class="text-gray-400 font-mono ml-1">({{ (item.rows || []).join(', ') || 'Rows' }})</span>
                                    </div>
                                    <button
                                        type="button"
                                        @click.stop="exportPivotCSV(item)"
                                        class="px-1.5 py-0.5 rounded bg-emerald-600 text-white font-medium hover:bg-emerald-700 text-[10px] cursor-pointer"
                                        title="Export CSV"
                                    >📥 CSV</button>
                                </div>

                                <template v-if="getPivotMatrix(item) && getPivotMatrix(item).rows.length">
                                    <div class="flex-grow overflow-auto border rounded">
                                        <table class="w-full border-collapse font-mono text-[10px]">
                                            <thead>
                                                <tr class="bg-gray-100 border-b text-gray-700 font-bold">
                                                    <th class="p-1 border-r bg-gray-200 text-gray-800 sticky top-0 left-0 z-10">
                                                        {{ (item.rows || []).join(' / ') || 'Row Labels' }}
                                                    </th>
                                                    <th
                                                        v-for="colKey in getPivotMatrix(item).colKeys"
                                                        :key="colKey.join('::')"
                                                        class="p-1 border-r text-center bg-gray-100 sticky top-0"
                                                    >
                                                        {{ colKey.join(' - ') || 'Total' }}
                                                    </th>
                                                    <th class="p-1 bg-gray-300 text-gray-900 font-bold text-center sticky top-0 right-0">
                                                        Grand Total
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr
                                                    v-for="(rowItem, rIdx) in getPivotMatrix(item).rows"
                                                    :key="rIdx"
                                                    :class="rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'"
                                                    class="hover:bg-blue-50/50 border-b"
                                                >
                                                    <td class="p-1 border-r font-semibold text-gray-700 bg-gray-50/80 sticky left-0">
                                                        {{ rowItem.rowKey.join(' / ') || 'Total' }}
                                                    </td>
                                                    <td
                                                        v-for="(cellVal, cIdx) in rowItem.cells"
                                                        :key="cIdx"
                                                        class="p-1 border-r text-right"
                                                    >
                                                        {{ formatCell(cellVal) }}
                                                    </td>
                                                    <td class="p-1 font-bold text-right bg-gray-100/80 text-blue-900 sticky right-0">
                                                        {{ formatCell(rowItem.rowTotal) }}
                                                    </td>
                                                </tr>
                                                <tr class="bg-gray-200 font-bold border-t-2 border-gray-400 text-gray-900 sticky bottom-0">
                                                    <td class="p-1 border-r bg-gray-300 sticky left-0">
                                                        Grand Total
                                                    </td>
                                                    <td
                                                        v-for="(colTotal, cIdx) in getPivotMatrix(item).colTotals"
                                                        :key="cIdx"
                                                        class="p-1 border-r text-right bg-gray-200"
                                                    >
                                                        {{ formatCell(colTotal) }}
                                                    </td>
                                                    <td class="p-1 text-right bg-gray-300 font-extrabold text-blue-950 sticky right-0">
                                                        {{ formatCell(getPivotMatrix(item).grandTotal) }}
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </template>
                                <div v-else-if="item.data_error" class="text-amber-600 italic text-[10px] p-2 bg-amber-50 rounded border border-amber-200">
                                    {{ item.data_error }}
                                </div>
                                <div v-else class="text-amber-700 italic text-[10px] p-2 bg-amber-50 rounded border border-amber-200">
                                    ⚠️ No Pivot Data. Select row and value fields in widget configurator.
                                </div>
                            </div>

                            <div v-else class="text-sm text-gray-600">
                                {{ item.content || 'Sample Widget Content' }}
                            </div>
                        </div>

                        <div v-if="isDraggable || isResizable" class="text-[10px] text-gray-400 border-t pt-1 mt-1 text-right font-mono">
                            x:{{ item.x }} y:{{ item.y }} w:{{ item.w }} h:{{ item.h }}
                        </div>
                    </GridItem>
                </GridLayout>
            </div>
        </div>
    `,
    components: {
        GridLayout,
        GridItem
    },
    props: {
        layout: {
            type: Array,
            default: () => []
        },
        colNum: {
            type: Number,
            default: 12
        },
        rowHeight: {
            type: Number,
            default: 60
        },
        isDraggable: {
            type: Boolean,
            default: true
        },
        isResizable: {
            type: Boolean,
            default: true
        },
        printPreview: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            localLayout: [],
            localPrintPreview: false,
            activeGuides: { x: [], y: [] },
            chartColors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        };
    },
    watch: {
        layout: {
            handler(newVal) {
                this.localLayout = JSON.parse(JSON.stringify(newVal || []));
            },
            deep: true,
            immediate: true
        },
        printPreview: {
            handler(val) {
                this.localPrintPreview = !!val;
            },
            immediate: true
        }
    },
    methods: {
        onItemClick(item) {
            if (item.drill_action || item.drillAction) {
                const action = item.drill_action || item.drillAction;
                this.$emit('drill_action', {
                    widget: item,
                    targetReport: action.target_report || action.targetReport || action.target_dashboard,
                    filters: action.filters || action.filter_mapping || {}
                });
            }
        },
        onLayoutUpdated(newLayout) {
            this.$emit('layout_updated', { layout: newLayout });
            this.$emit('change', { layout: newLayout });
        },
        onItemMoved(i, newX, newY) {
            this.$emit('item_moved', { i, x: newX, y: newY, layout: this.localLayout });
        },
        onItemResized(i, newH, newW, newHPx, newWPx) {
            this.$emit('item_resized', { i, h: newH, w: newW, layout: this.localLayout });
        },
        onItemDragging(i, newX, newY) {
            this.computeSmartGuides(i, newX, newY, null, null);
        },
        onItemResizing(i, newH, newW) {
            const item = this.localLayout.find(it => it.i === i);
            if (item) {
                this.computeSmartGuides(i, item.x, item.y, newW, newH);
            }
        },
        onItemEnd() {
            this.activeGuides = { x: [], y: [] };
        },
        computeSmartGuides(itemId, x, y, w, h) {
            const activeItem = this.localLayout.find(it => it.i === itemId);
            const currW = w !== null && w !== undefined ? w : (activeItem ? activeItem.w : 1);
            const currH = h !== null && h !== undefined ? h : (activeItem ? activeItem.h : 1);

            const xPoints = [x, x + currW / 2, x + currW];
            const yPoints = [y, y + currH / 2, y + currH];

            const matchedX = new Set();
            const matchedY = new Set();

            this.localLayout.forEach(other => {
                if (other.i === itemId) return;
                const otherXPoints = [other.x, other.x + other.w / 2, other.x + other.w];
                const otherYPoints = [other.y, other.y + other.h / 2, other.y + other.h];

                xPoints.forEach(pt => {
                    otherXPoints.forEach(opt => {
                        if (Math.abs(pt - opt) < 0.25) {
                            matchedX.add(opt);
                        }
                    });
                });

                yPoints.forEach(pt => {
                    otherYPoints.forEach(opt => {
                        if (Math.abs(pt - opt) < 0.25) {
                            matchedY.add(opt);
                        }
                    });
                });
            });

            this.activeGuides = {
                x: Array.from(matchedX),
                y: Array.from(matchedY)
            };
        },
        calcPrintPages() {
            const pageRows = 12;
            const pagePx = pageRows * (this.rowHeight + 10);
            const maxRow = this.localLayout.reduce((m, item) => Math.max(m, (item.y || 0) + (item.h || 0)), 12);
            const totalPages = Math.max(1, Math.ceil(maxRow / pageRows));
            const pages = [];
            for (let p = 1; p <= totalPages; p++) {
                pages.push({
                    num: p,
                    topPx: p * pagePx
                });
            }
            return pages;
        },
        getTablixMeasures(item) {
            if (item.measures && item.measures.length) {
                return item.measures.map(m => typeof m === 'string' ? m : (m.col || m.title || 'val'));
            }
            if (item.columns && item.columns.length) {
                const groups = item.row_groups || item.rowGroups || [];
                return item.columns.filter(c => !groups.includes(c));
            }
            return ['val'];
        },
        getTablixRows(item) {
            if (!item.data || !item.data.length) return [];
            const groups = item.row_groups || item.rowGroups || [];
            if (!groups.length) return item.data.map(r => ({ label: 'Row', values: r }));

            const measures = this.getTablixMeasures(item);
            const groupedMap = {};
            item.data.forEach(r => {
                const label = groups.map(g => r[g] !== undefined && r[g] !== null ? String(r[g]) : 'N/D').join(' › ');
                if (!groupedMap[label]) {
                    groupedMap[label] = { label, counts: 0, values: {} };
                    measures.forEach(m => groupedMap[label].values[m] = 0);
                }
                groupedMap[label].counts += 1;
                measures.forEach(m => {
                    const num = parseFloat(r[m]);
                    if (!isNaN(num)) groupedMap[label].values[m] += num;
                });
            });
            return Object.values(groupedMap);
        },
        getTablixStyle(item, val, colName) {
            if (val === null || val === undefined || isNaN(val)) return {};
            const rules = item.conditional_formatting || item.conditionalFormatting || [];
            for (const r of rules) {
                if (r.column && r.column !== colName) continue;
                const target = parseFloat(r.value);
                const op = r.operator || r.rule || '>';
                let matched = false;
                if (op === '>' && val > target) matched = true;
                else if (op === '>=' && val >= target) matched = true;
                else if (op === '<' && val < target) matched = true;
                else if (op === '<=' && val <= target) matched = true;
                if (matched && r.style) {
                    return {
                        color: r.style.color || 'inherit',
                        backgroundColor: r.style.backgroundColor || r.style.background || 'transparent'
                    };
                }
            }
            return {};
        },
        barHeight(chart, value) {
            if (typeof value !== 'number' || !isFinite(value) || value < 0) return 0;
            const max = chart.max > 0 ? chart.max : 1;
            return Math.min(100, Math.round((value / max) * 100));
        },
        shortLabel(label) {
            const text = String(label);
            return text.length > 9 ? text.slice(0, 8) + '…' : text;
        },
        pieSlices(chart) {
            const series = chart.series[0];
            if (!series) return [];
            const values = series.values.map(v => (typeof v === 'number' && isFinite(v) && v > 0) ? v : 0);
            const total = values.reduce((a, b) => a + b, 0);
            if (total <= 0) return [];
            const slices = [];
            let acc = 0;
            values.forEach((v, i) => {
                if (v <= 0) return;
                const start = (acc / total) * 360;
                acc += v;
                const end = Math.min((acc / total) * 360, 359.99);
                slices.push({
                    d: this.arcPath(start, end),
                    label: chart.labels[i],
                    value: series.values[i]
                });
            });
            return slices;
        },
        arcPath(start, end) {
            const cx = 21, cy = 21, r = 20;
            const rad = a => (a - 90) * Math.PI / 180;
            const x1 = cx + r * Math.cos(rad(start));
            const y1 = cy + r * Math.sin(rad(start));
            const x2 = cx + r * Math.cos(rad(end));
            const y2 = cy + r * Math.sin(rad(end));
            const large = (end - start) > 180 ? 1 : 0;
            return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
        },
        linePaths(chart) {
            const count = chart.labels.length;
            const step = count > 1 ? 100 / (count - 1) : 0;
            const max = chart.max > 0 ? chart.max : 1;
            return chart.series.map(series => series.values.map((v, i) => {
                const x = count > 1 ? (i * step).toFixed(2) : '50';
                const y = (typeof v === 'number' && isFinite(v)) ? (100 - Math.min(100, (v / max) * 100)).toFixed(2) : '100';
                return `${x},${y}`;
            }).join(' '));
        },
        formatCell(val) {
            if (val === null || val === undefined || isNaN(val)) return '—';
            if (Number.isInteger(val)) return val.toLocaleString();
            return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },
        getPivotMatrix(item) {
            if (item.server_pivot_data && item.server_pivot_data.rows) {
                return item.server_pivot_data;
            }
            if (!item.data || !item.data.length) return null;

            const rows = item.rows || [];
            const cols = item.cols || [];
            const rawVals = item.values || item.vals || [];
            const filters = item.filters || [];
            const filterValues = item.filter_values || item.filterValues || {};
            if (!rows.length && !cols.length) return null;

            // Apply report filters
            let dataToPivot = item.data;
            if (filters.length) {
                dataToPivot = dataToPivot.filter(r => {
                    for (const fCol of filters) {
                        const fVal = filterValues[fCol];
                        if (fVal !== undefined && fVal !== null && fVal !== '') {
                            if (String(r[fCol]) !== String(fVal)) return false;
                        }
                    }
                    return true;
                });
            }

            if (!dataToPivot.length) return null;

            // Normalize valSpecs
            let valSpecs = [];
            if (Array.isArray(rawVals)) {
                valSpecs = rawVals.map(v => {
                    if (typeof v === 'object' && v !== null) {
                        return { field: v.field || v.col || '', agg: v.agg || item.aggregator_name || 'Sum', showAs: v.showAs || 'None' };
                    }
                    return { field: String(v), agg: item.aggregator_name || 'Sum', showAs: 'None' };
                }).filter(v => v.field);
            } else if (typeof rawVals === 'string' && rawVals.trim()) {
                valSpecs = rawVals.split(',').map(s => ({ field: s.trim(), agg: item.aggregator_name || 'Sum', showAs: 'None' }));
            }

            if (!valSpecs.length) {
                valSpecs = [{ field: 'val', agg: item.aggregator_name || 'Sum', showAs: 'None' }];
            }

            const rowKeysSet = new Set();
            const colKeysSet = new Set();

            const getTupleKey = (row, fields) => fields.map(f => row[f] === undefined || row[f] === null ? '' : String(row[f]));

            dataToPivot.forEach(row => {
                rowKeysSet.add(JSON.stringify(getTupleKey(row, rows)));
                colKeysSet.add(JSON.stringify(getTupleKey(row, cols)));
            });

            const rowKeys = Array.from(rowKeysSet).map(s => JSON.parse(s));
            const baseColKeys = Array.from(colKeysSet).map(s => JSON.parse(s));

            const cellMap = {};
            dataToPivot.forEach(row => {
                const rKeyStr = JSON.stringify(getTupleKey(row, rows));
                const cKeyStr = JSON.stringify(getTupleKey(row, cols));

                if (!cellMap[rKeyStr]) cellMap[rKeyStr] = {};
                if (!cellMap[rKeyStr][cKeyStr]) cellMap[rKeyStr][cKeyStr] = valSpecs.map(() => []);

                valSpecs.forEach((spec, vIdx) => {
                    const val = parseFloat(row[spec.field]);
                    if (!isNaN(val)) cellMap[rKeyStr][cKeyStr][vIdx].push(val);
                });
            });

            const calcAgg = (values, aggName) => {
                if (!values || !values.length) return null;
                const agg = aggName || 'Sum';
                if (agg === 'Count') return values.length;
                if (agg === 'Sum') return values.reduce((a, b) => a + b, 0);
                if (agg === 'Average') return values.reduce((a, b) => a + b, 0) / values.length;
                if (agg === 'Min') return Math.min(...values);
                if (agg === 'Max') return Math.max(...values);
                return values.reduce((a, b) => a + b, 0);
            };

            const expandedColKeys = [];
            if (baseColKeys.length && valSpecs.length > 1) {
                baseColKeys.forEach(cKey => {
                    valSpecs.forEach(spec => expandedColKeys.push([...cKey, `${spec.field} (${spec.agg})`]));
                });
            } else if (baseColKeys.length) {
                baseColKeys.forEach(cKey => expandedColKeys.push(cKey));
            } else if (valSpecs.length > 1) {
                valSpecs.forEach(spec => expandedColKeys.push([`${spec.field} (${spec.agg})`]));
            } else {
                expandedColKeys.push([]);
            }

            const matrixRows = [];
            rowKeys.forEach(rKey => {
                const rKeyStr = JSON.stringify(rKey);
                const cells = [];
                const rowAllValues = valSpecs.map(() => []);

                if (baseColKeys.length && valSpecs.length > 1) {
                    baseColKeys.forEach(cKey => {
                        const cKeyStr = JSON.stringify(cKey);
                        valSpecs.forEach((spec, vIdx) => {
                            const values = cellMap[rKeyStr] && cellMap[rKeyStr][cKeyStr] ? cellMap[rKeyStr][cKeyStr][vIdx] : [];
                            const val = calcAgg(values, spec.agg);
                            cells.push(val);
                            if (values.length) rowAllValues[vIdx].push(...values);
                        });
                    });
                } else if (baseColKeys.length) {
                    const spec = valSpecs[0];
                    baseColKeys.forEach(cKey => {
                        const cKeyStr = JSON.stringify(cKey);
                        const values = cellMap[rKeyStr] && cellMap[rKeyStr][cKeyStr] ? cellMap[rKeyStr][cKeyStr][0] : [];
                        const val = calcAgg(values, spec.agg);
                        cells.push(val);
                        if (values.length) rowAllValues[0].push(...values);
                    });
                } else {
                    valSpecs.forEach((spec, vIdx) => {
                        const values = cellMap[rKeyStr] && cellMap[rKeyStr]['[]'] ? cellMap[rKeyStr]['[]'][vIdx] : [];
                        const val = calcAgg(values, spec.agg);
                        cells.push(val);
                        if (values.length) rowAllValues[vIdx].push(...values);
                    });
                }

                const firstValTotal = calcAgg(rowAllValues[0], valSpecs[0].agg);
                matrixRows.push({ rowKey: rKey, cells, rowTotal: firstValTotal });
            });

            const colTotals = expandedColKeys.map((cKey, cIdx) => {
                const colCells = matrixRows.map(r => r.cells[cIdx]).filter(v => v !== null && v !== undefined);
                if (!colCells.length) return null;
                const vIdx = valSpecs.length > 1 ? (cIdx % valSpecs.length) : 0;
                return calcAgg(colCells, valSpecs[vIdx].agg);
            });

            const validColTotals = colTotals.filter(ct => ct !== null && ct !== undefined);
            const grandTotal = validColTotals.length ? validColTotals.reduce((a, b) => a + b, 0) : null;

            return { colKeys: expandedColKeys, rows: matrixRows, colTotals, grandTotal };
        },
        exportPivotCSV(item) {
            const matrix = this.getPivotMatrix(item);
            if (!matrix) return;

            const rows = [];
            const headerRow = [
                (item.rows || []).join(' / ') || 'Row Labels',
                ...matrix.colKeys.map(ck => ck.join(' - ') || 'Total'),
                'Grand Total'
            ];
            rows.push(headerRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));

            matrix.rows.forEach(r => {
                const rowLabel = r.rowKey.length ? r.rowKey.join(' / ') : 'Total';
                const cells = r.cells.map(v => v === null || v === undefined ? '' : v);
                const csvRow = [rowLabel, ...cells, r.rowTotal === null ? '' : r.rowTotal];
                rows.push(csvRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));
            });

            const grandTotalCells = matrix.colTotals.map(v => v === null || v === undefined ? '' : v);
            const grandTotalRow = ['Grand Total', ...grandTotalCells, matrix.grandTotal === null ? '' : matrix.grandTotal];
            rows.push(grandTotalRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));

            const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(rows.join('\n'));
            const link = document.createElement('a');
            link.setAttribute('href', csvContent);
            link.setAttribute('download', 'pivot_table_export.csv');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
};
