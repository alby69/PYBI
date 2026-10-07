export default {
    template: `
        <div class="pybi-pivot-container w-full h-full flex flex-col bg-white border rounded shadow-sm p-3 overflow-hidden text-xs text-gray-800">
            <!-- Header Controls Bar (Hidden if readOnly) -->
            <div v-if="!readOnly" class="border-b pb-2 mb-2 flex flex-wrap items-center justify-between gap-2 bg-slate-50 p-2 rounded">
                <div class="flex items-center gap-3 flex-wrap">
                    <div class="flex items-center gap-1">
                        <label class="font-semibold text-gray-700 text-xs">Aggregator:</label>
                        <select
                            v-model="localAggregator"
                            @change="onConfigChange"
                            class="border rounded px-2 py-1 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                            <option value="Sum">Sum</option>
                            <option value="Count">Count</option>
                            <option value="Average">Average</option>
                            <option value="Min">Min</option>
                            <option value="Max">Max</option>
                        </select>
                    </div>
                </div>

                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        @click="exportCSV"
                        class="px-2 py-1 rounded bg-emerald-600 text-white font-medium hover:bg-emerald-700 flex items-center gap-1 cursor-pointer text-xs"
                        title="Export Pivot Table to CSV"
                    >
                        <span>📥 Export CSV</span>
                    </button>
                </div>
            </div>

            <!-- Field Drag & Drop / Selection Zones (Hidden if readOnly) -->
            <div v-if="!readOnly" class="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3 bg-gray-50 p-2 rounded border border-gray-200">
                <!-- Available Fields -->
                <div class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[70px]">
                    <span class="font-bold text-[11px] text-gray-600 mb-1 flex justify-between items-center">
                        <span>Available Fields</span>
                        <span class="text-[9px] text-gray-400">Drag or click +</span>
                    </span>
                    <div class="flex flex-wrap gap-1 items-center">
                        <div
                            v-for="col in availableColumns"
                            :key="col"
                            draggable="true"
                            @dragstart="onDragStart($event, col, 'available')"
                            class="group relative px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-mono text-[10px] cursor-grab flex items-center gap-1 hover:bg-blue-100"
                        >
                            <span>{{ col }}</span>
                            <div class="hidden group-hover:flex items-center gap-0.5 ml-1">
                                <button type="button" @click="addField('rows', col)" class="hover:text-blue-900 font-bold" title="Add to Rows">+R</button>
                                <button type="button" @click="addField('cols', col)" class="hover:text-blue-900 font-bold" title="Add to Columns">+C</button>
                                <button type="button" @click="addField('vals', col)" class="hover:text-blue-900 font-bold" title="Add to Values">+V</button>
                            </div>
                        </div>
                        <span v-if="!availableColumns.length" class="text-[10px] text-gray-400 italic">No unused fields</span>
                    </div>
                </div>

                <!-- Rows Drop Zone -->
                <div
                    @dragover.prevent
                    @drop="onDrop($event, 'rows')"
                    class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[70px]"
                >
                    <span class="font-bold text-[11px] text-gray-600 mb-1">Rows</span>
                    <div class="flex flex-wrap gap-1 items-center flex-grow">
                        <div
                            v-for="(col, idx) in localRows"
                            :key="col"
                            class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono text-[10px] flex items-center gap-1"
                        >
                            <span>{{ col }}</span>
                            <button type="button" @click="removeField('rows', idx)" class="text-emerald-600 hover:text-red-600 font-bold ml-1">×</button>
                        </div>
                        <span v-if="!localRows.length" class="text-[10px] text-gray-400 italic">Drop row fields here</span>
                    </div>
                </div>

                <!-- Columns Drop Zone -->
                <div
                    @dragover.prevent
                    @drop="onDrop($event, 'cols')"
                    class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[70px]"
                >
                    <span class="font-bold text-[11px] text-gray-600 mb-1">Columns</span>
                    <div class="flex flex-wrap gap-1 items-center flex-grow">
                        <div
                            v-for="(col, idx) in localCols"
                            :key="col"
                            class="px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200 font-mono text-[10px] flex items-center gap-1"
                        >
                            <span>{{ col }}</span>
                            <button type="button" @click="removeField('cols', idx)" class="text-purple-600 hover:text-red-600 font-bold ml-1">×</button>
                        </div>
                        <span v-if="!localCols.length" class="text-[10px] text-gray-400 italic">Drop column fields here</span>
                    </div>
                </div>

                <!-- Values Drop Zone -->
                <div
                    @dragover.prevent
                    @drop="onDrop($event, 'vals')"
                    class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[70px]"
                >
                    <span class="font-bold text-[11px] text-gray-600 mb-1">Values ({{ localAggregator }})</span>
                    <div class="flex flex-wrap gap-1 items-center flex-grow">
                        <div
                            v-for="(col, idx) in localVals"
                            :key="col"
                            class="px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-mono text-[10px] flex items-center gap-1"
                        >
                            <span>{{ col }}</span>
                            <button type="button" @click="removeField('vals', idx)" class="text-amber-600 hover:text-red-600 font-bold ml-1">×</button>
                        </div>
                        <span v-if="!localVals.length" class="text-[10px] text-gray-400 italic">Drop metric fields here</span>
                    </div>
                </div>
            </div>

            <!-- Export CSV Button for ReadOnly mode -->
            <div v-if="readOnly" class="flex justify-end mb-2">
                <button
                    type="button"
                    @click="exportCSV"
                    class="px-2 py-1 rounded bg-emerald-600 text-white font-medium hover:bg-emerald-700 flex items-center gap-1 cursor-pointer text-xs"
                >
                    <span>📥 Export CSV</span>
                </button>
            </div>

            <!-- Banner for Empty / Invalid Config -->
            <div v-if="!pivotMatrix || pivotMatrix.rows.length === 0" class="flex-grow flex items-center justify-center p-4">
                <div class="w-full max-w-md p-3 bg-amber-50 border border-amber-200 rounded text-amber-800 text-center">
                    <div class="font-semibold mb-1 flex items-center justify-center gap-1">
                        <span>⚠️ No Pivot Data Available</span>
                    </div>
                    <div class="text-[11px]">
                        {{ emptyMessage }}
                    </div>
                </div>
            </div>

            <!-- Pivot Table Grid View -->
            <div v-else class="flex-grow overflow-auto border border-gray-200 rounded max-h-[500px]">
                <table class="w-full border-collapse text-left font-mono text-xs">
                    <thead>
                        <!-- Column Headers Row 1 -->
                        <tr class="bg-gray-100 border-b text-gray-700 font-bold">
                            <!-- Row header labels header cell -->
                            <th
                                :colspan="localRows.length || 1"
                                class="p-1.5 border-r bg-gray-200 text-gray-800 sticky top-0 left-0 z-20"
                            >
                                {{ localRows.join(' / ') || 'Row Labels' }}
                            </th>

                            <!-- Column key headers -->
                            <th
                                v-for="colKey in pivotMatrix.colKeys"
                                :key="colKey.join('::')"
                                class="p-1.5 border-r text-center bg-gray-100 sticky top-0 z-10"
                            >
                                {{ colKey.join(' - ') || 'Total' }}
                            </th>

                            <!-- Grand Total Column Header -->
                            <th class="p-1.5 bg-gray-300 text-gray-900 font-bold text-center sticky top-0 right-0 z-10">
                                Grand Total
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Data Rows -->
                        <tr
                            v-for="(rowItem, rIdx) in pivotMatrix.rows"
                            :key="rIdx"
                            :class="rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'"
                            class="hover:bg-blue-50/50 border-b"
                        >
                            <!-- Row label values -->
                            <td
                                v-for="(val, vIdx) in rowItem.rowKey"
                                :key="vIdx"
                                class="p-1.5 border-r font-semibold text-gray-700 bg-gray-50/80 sticky left-0 z-10"
                            >
                                {{ val === '' || val === null || val === undefined ? '(blank)' : val }}
                            </td>
                            <td v-if="!rowItem.rowKey.length" class="p-1.5 border-r font-semibold text-gray-700 bg-gray-50/80 sticky left-0 z-10">
                                Total
                            </td>

                            <!-- Cell Values across Column Keys -->
                            <td
                                v-for="(cellVal, cIdx) in rowItem.cells"
                                :key="cIdx"
                                class="p-1.5 border-r text-right"
                            >
                                {{ formatCell(cellVal) }}
                            </td>

                            <!-- Row Total -->
                            <td class="p-1.5 font-bold text-right bg-gray-100/80 text-blue-900 sticky right-0">
                                {{ formatCell(rowItem.rowTotal) }}
                            </td>
                        </tr>

                        <!-- Grand Total Row -->
                        <tr class="bg-gray-200 font-bold border-t-2 border-gray-400 text-gray-900 sticky bottom-0 z-20">
                            <td
                                :colspan="localRows.length || 1"
                                class="p-1.5 border-r bg-gray-300 sticky left-0 z-30"
                            >
                                Grand Total
                            </td>
                            <td
                                v-for="(colTotal, cIdx) in pivotMatrix.colTotals"
                                :key="cIdx"
                                class="p-1.5 border-r text-right bg-gray-200"
                            >
                                {{ formatCell(colTotal) }}
                            </td>
                            <td class="p-1.5 text-right bg-gray-300 font-extrabold text-blue-950 sticky right-0">
                                {{ formatCell(pivotMatrix.grandTotal) }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    `,
    props: {
        data: {
            type: Array,
            default: () => []
        },
        columns: {
            type: Array,
            default: () => []
        },
        rows: {
            type: Array,
            default: () => []
        },
        cols: {
            type: Array,
            default: () => []
        },
        vals: {
            type: Array,
            default: () => []
        },
        aggregatorName: {
            type: String,
            default: 'Sum'
        },
        readOnly: {
            type: Boolean,
            default: false
        },
        serverPivotData: {
            type: Object,
            default: null
        }
    },
    data() {
        return {
            localRows: [],
            localCols: [],
            localVals: [],
            localAggregator: 'Sum',
            draggedCol: null
        };
    },
    computed: {
        allColumns() {
            if (this.columns && this.columns.length) return this.columns;
            if (this.data && this.data.length && typeof this.data[0] === 'object') {
                return Object.keys(this.data[0]);
            }
            return [];
        },
        availableColumns() {
            const used = new Set([...this.localRows, ...this.localCols, ...this.localVals]);
            return this.allColumns.filter(c => !used.has(c));
        },
        emptyMessage() {
            if (!this.data || !this.data.length) {
                return 'Data source is empty or no dataset is bound.';
            }
            if (!this.localRows.length && !this.localCols.length) {
                return 'Please drag or add at least one field to Rows or Columns to pivot.';
            }
            if (!this.localVals.length) {
                return 'Please drag or add at least one numeric field to Values.';
            }
            return 'No aggregated records match the current pivot selection.';
        },
        pivotMatrix() {
            if (this.serverPivotData && this.serverPivotData.rows) {
                return this.serverPivotData;
            }

            if (!this.data || !this.data.length) return null;
            if (!this.localRows.length && !this.localCols.length) return null;

            const valCols = this.localVals.length ? this.localVals : [];
            const agg = this.localAggregator || 'Sum';

            const rowKeysSet = new Set();
            const colKeysSet = new Set();

            const getTupleKey = (row, fields) => fields.map(f => row[f] === undefined || row[f] === null ? '' : String(row[f]));

            this.data.forEach(row => {
                const rKey = getTupleKey(row, this.localRows);
                const cKey = getTupleKey(row, this.localCols);
                rowKeysSet.add(JSON.stringify(rKey));
                colKeysSet.add(JSON.stringify(cKey));
            });

            const rowKeys = Array.from(rowKeysSet).map(s => JSON.parse(s));
            const colKeys = Array.from(colKeysSet).map(s => JSON.parse(s));

            const cellMap = {};
            this.data.forEach(row => {
                const rKeyStr = JSON.stringify(getTupleKey(row, this.localRows));
                const cKeyStr = JSON.stringify(getTupleKey(row, this.localCols));

                if (!cellMap[rKeyStr]) cellMap[rKeyStr] = {};
                if (!cellMap[rKeyStr][cKeyStr]) cellMap[rKeyStr][cKeyStr] = [];

                if (valCols.length) {
                    valCols.forEach(vCol => {
                        const val = parseFloat(row[vCol]);
                        if (!isNaN(val)) {
                            cellMap[rKeyStr][cKeyStr].push(val);
                        }
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
        }
    },
    watch: {
        rows: {
            handler(v) { this.localRows = [...(v || [])]; },
            immediate: true,
            deep: true
        },
        cols: {
            handler(v) { this.localCols = [...(v || [])]; },
            immediate: true,
            deep: true
        },
        vals: {
            handler(v) { this.localVals = [...(v || [])]; },
            immediate: true,
            deep: true
        },
        aggregatorName: {
            handler(v) { this.localAggregator = v || 'Sum'; },
            immediate: true
        }
    },
    methods: {
        formatCell(val) {
            if (val === null || val === undefined || isNaN(val)) return '—';
            if (Number.isInteger(val)) return val.toLocaleString();
            return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },
        onConfigChange() {
            const newConfig = {
                rows: this.localRows,
                cols: this.localCols,
                vals: this.localVals,
                aggregator_name: this.localAggregator,
                aggregatorName: this.localAggregator
            };
            this.$emit('update:config', newConfig);
            this.$emit('config_changed', newConfig);
        },
        addField(zone, col) {
            if (zone === 'rows' && !this.localRows.includes(col)) this.localRows.push(col);
            if (zone === 'cols' && !this.localCols.includes(col)) this.localCols.push(col);
            if (zone === 'vals' && !this.localVals.includes(col)) this.localVals.push(col);
            this.onConfigChange();
        },
        removeField(zone, idx) {
            if (zone === 'rows') this.localRows.splice(idx, 1);
            if (zone === 'cols') this.localCols.splice(idx, 1);
            if (zone === 'vals') this.localVals.splice(idx, 1);
            this.onConfigChange();
        },
        onDragStart(evt, col, zone) {
            evt.dataTransfer.setData('text/plain', JSON.stringify({ col, zone }));
        },
        onDrop(evt, targetZone) {
            try {
                const raw = evt.dataTransfer.getData('text/plain');
                if (!raw) return;
                const { col } = JSON.parse(raw);
                if (col) this.addField(targetZone, col);
            } catch (e) {
                console.error(e);
            }
        },
        exportCSV() {
            if (!this.pivotMatrix) return;

            const rows = [];
            const headerRow = [
                this.localRows.join(' / ') || 'Row Labels',
                ...this.pivotMatrix.colKeys.map(ck => ck.join(' - ') || 'Total'),
                'Grand Total'
            ];
            rows.push(headerRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));

            this.pivotMatrix.rows.forEach(r => {
                const rowLabel = r.rowKey.length ? r.rowKey.join(' / ') : 'Total';
                const cells = r.cells.map(v => v === null || v === undefined ? '' : v);
                const csvRow = [rowLabel, ...cells, r.rowTotal === null ? '' : r.rowTotal];
                rows.push(csvRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));
            });

            const grandTotalCells = this.pivotMatrix.colTotals.map(v => v === null || v === undefined ? '' : v);
            const grandTotalRow = ['Grand Total', ...grandTotalCells, this.pivotMatrix.grandTotal === null ? '' : this.pivotMatrix.grandTotal];
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
