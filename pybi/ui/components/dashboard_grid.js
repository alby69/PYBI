import { GridLayout, GridItem } from 'https://cdn.jsdelivr.net/npm/grid-layout-plus@1.1.1/dist/grid-layout-plus.mjs';

export default {
    template: `
        <div class="dashboard-grid-container w-full h-full min-h-[500px]">
            <GridLayout
                v-model:layout="localLayout"
                :col-num="colNum"
                :row-height="rowHeight"
                :is-draggable="isDraggable"
                :is-resizable="isResizable"
                :vertical-compact="true"
                :use-css-transforms="true"
                class="w-full bg-slate-50 border rounded p-2"
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
                    class="bg-white border rounded shadow-sm p-3 flex flex-col justify-between overflow-hidden"
                    @moved="onItemMoved"
                    @resized="onItemResized"
                >
                    <div class="font-semibold text-sm border-b pb-1 mb-2 flex items-center justify-between text-gray-800">
                        <span>{{ item.title || 'Widget ' + item.i }}</span>
                        <span class="flex items-center gap-1">
                            <span class="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600 uppercase">{{ item.type || 'card' }}</span>
                            <button
                                type="button"
                                class="edit-widget-btn text-xs px-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 cursor-pointer"
                                title="Edit widget"
                                @mousedown.stop
                                @click.stop="$emit('edit_widget', { widget: item })">✏️</button>
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
        }
    },
    data() {
        return {
            localLayout: [],
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
        }
    },
    methods: {
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
            const vals = item.vals || [];
            if (!rows.length && !cols.length) return null;

            const agg = item.aggregator_name || 'Sum';

            const rowKeysSet = new Set();
            const colKeysSet = new Set();

            const getTupleKey = (row, fields) => fields.map(f => row[f] === undefined || row[f] === null ? '' : String(row[f]));

            item.data.forEach(row => {
                rowKeysSet.add(JSON.stringify(getTupleKey(row, rows)));
                colKeysSet.add(JSON.stringify(getTupleKey(row, cols)));
            });

            const rowKeys = Array.from(rowKeysSet).map(s => JSON.parse(s));
            const colKeys = Array.from(colKeysSet).map(s => JSON.parse(s));

            const cellMap = {};
            item.data.forEach(row => {
                const rKeyStr = JSON.stringify(getTupleKey(row, rows));
                const cKeyStr = JSON.stringify(getTupleKey(row, cols));

                if (!cellMap[rKeyStr]) cellMap[rKeyStr] = {};
                if (!cellMap[rKeyStr][cKeyStr]) cellMap[rKeyStr][cKeyStr] = [];

                if (vals.length) {
                    vals.forEach(vCol => {
                        const val = parseFloat(row[vCol]);
                        if (!isNaN(val)) cellMap[rKeyStr][cKeyStr].push(val);
                    });
                } else {
                    cellMap[rKeyStr][cKeyStr].push(1);
                }
            });

            const calcAgg = (values) => {
                if (!values || !values.length) return null;
                if (agg === 'Count') return values.length;
                if (agg === 'Sum') return values.reduce((a, b) => a + b, 0);
                if (agg === 'Average') return values.reduce((a, b) => a + b, 0) / values.length;
                if (agg === 'Min') return Math.min(...values);
                if (agg === 'Max') return Math.max(...values);
                return values.reduce((a, b) => a + b, 0);
            };

            const matrixRows = [];
            const colAllValues = colKeys.map(() => []);
            const grandAllValues = [];

            rowKeys.forEach(rKey => {
                const rKeyStr = JSON.stringify(rKey);
                const rowAllValues = [];
                const cells = colKeys.map((cKey, cIdx) => {
                    const cKeyStr = JSON.stringify(cKey);
                    const values = cellMap[rKeyStr] ? cellMap[rKeyStr][cKeyStr] || [] : [];
                    const aggregated = calcAgg(values);

                    if (values.length) {
                        rowAllValues.push(...values);
                        colAllValues[cIdx].push(...values);
                        grandAllValues.push(...values);
                    }
                    return aggregated;
                });

                const rowTotal = calcAgg(rowAllValues);
                matrixRows.push({
                    rowKey: rKey,
                    cells,
                    rowTotal
                });
            });

            const colTotals = colAllValues.map(vals => calcAgg(vals));
            const grandTotal = calcAgg(grandAllValues);

            return {
                colKeys,
                rows: matrixRows,
                colTotals,
                grandTotal
            };
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
