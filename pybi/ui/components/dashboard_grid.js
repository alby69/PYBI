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
                                        <tr v-for="(row, ri) in item.rows || []" :key="ri">
                                            <td v-for="(cell, ci) in row" :key="ci" class="p-1 border">{{ cell === null || cell === undefined ? '—' : cell }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                                <div v-if="item.truncated" class="text-[9px] text-gray-400 text-right mt-1">
                                    showing first {{ (item.rows || []).length }} of {{ item.row_count }} rows
                                </div>
                            </template>
                            <div v-else-if="item.data_error" class="text-amber-600 italic">{{ item.data_error }}</div>
                            <div v-else class="text-gray-500 italic">No data source bound yet</div>
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
        }
    }
};
