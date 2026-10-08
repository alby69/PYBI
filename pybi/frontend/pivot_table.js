export default {
    template: `
        <div class="pybi-pivot-container w-full h-full flex flex-col bg-white border rounded shadow-sm p-3 overflow-hidden text-xs text-gray-800">
            <!-- Header Controls & Report Filter Dropdowns -->
            <div v-if="localFilters.length || !readOnly" class="border-b pb-2 mb-2 flex flex-wrap items-center justify-between gap-2 bg-slate-50 p-2 rounded">
                <!-- Active Report Filter Selectors -->
                <div class="flex items-center gap-3 flex-wrap">
                    <div v-for="fCol in localFilters" :key="fCol" class="flex items-center gap-1 bg-white border px-2 py-0.5 rounded shadow-xs">
                        <span class="font-semibold text-gray-700 text-xs">🔍 {{ fCol }}:</span>
                        <select
                            :value="localFilterValues[fCol] || ''"
                            @change="setFilterValue(fCol, $event.target.value)"
                            class="border rounded px-1.5 py-0.5 text-xs bg-gray-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                            <option value="">(All)</option>
                            <option v-for="opt in getFilterOptions(fCol)" :key="opt" :value="opt">{{ opt }}</option>
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
            <div v-if="!readOnly" class="grid grid-cols-1 md:grid-cols-5 gap-2 mb-3 bg-gray-50 p-2 rounded border border-gray-200">
                <!-- Available Fields -->
                <div class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[85px]">
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
                            class="group relative px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-mono text-[10px] cursor-grab flex items-center gap-1 hover:bg-blue-100"
                        >
                            <span>{{ col }}</span>
                            <div class="hidden group-hover:flex items-center gap-0.5 ml-1">
                                <button type="button" @click="addField('filters', col)" class="hover:text-blue-900 font-bold text-[9px]" title="Add Filter">+F</button>
                                <button type="button" @click="addField('rows', col)" class="hover:text-blue-900 font-bold text-[9px]" title="Add Rows">+R</button>
                                <button type="button" @click="addField('cols', col)" class="hover:text-blue-900 font-bold text-[9px]" title="Add Columns">+C</button>
                                <button type="button" @click="addField('vals', col)" class="hover:text-blue-900 font-bold text-[9px]" title="Add Values">+V</button>
                            </div>
                        </div>
                        <span v-if="!availableColumns.length" class="text-[10px] text-gray-400 italic">No unused fields</span>
                    </div>
                </div>

                <!-- Filters Drop Zone -->
                <div
                    @dragover.prevent
                    @drop="onDrop($event, 'filters')"
                    class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[85px]"
                >
                    <span class="font-bold text-[11px] text-gray-600 mb-1">Filters (Slicers)</span>
                    <div class="flex flex-wrap gap-1 items-center flex-grow">
                        <div
                            v-for="(col, idx) in localFilters"
                            :key="col"
                            class="px-1.5 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200 font-mono text-[10px] flex items-center gap-1"
                        >
                            <span>{{ col }}</span>
                            <button type="button" @click="removeField('filters', idx)" class="text-sky-600 hover:text-red-600 font-bold ml-1">×</button>
                        </div>
                        <span v-if="!localFilters.length" class="text-[10px] text-gray-400 italic">Drop filter fields here</span>
                    </div>
                </div>

                <!-- Rows Drop Zone -->
                <div
                    @dragover.prevent
                    @drop="onDrop($event, 'rows')"
                    class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[85px]"
                >
                    <span class="font-bold text-[11px] text-gray-600 mb-1">Rows</span>
                    <div class="flex flex-wrap gap-1 items-center flex-grow">
                        <div
                            v-for="(col, idx) in localRows"
                            :key="col"
                            class="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono text-[10px] flex items-center gap-1"
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
                    class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[85px]"
                >
                    <span class="font-bold text-[11px] text-gray-600 mb-1">Columns</span>
                    <div class="flex flex-wrap gap-1 items-center flex-grow">
                        <div
                            v-for="(col, idx) in localCols"
                            :key="col"
                            class="px-1.5 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200 font-mono text-[10px] flex items-center gap-1"
                        >
                            <span>{{ col }}</span>
                            <button type="button" @click="removeField('cols', idx)" class="text-purple-600 hover:text-red-600 font-bold ml-1">×</button>
                        </div>
                        <span v-if="!localCols.length" class="text-[10px] text-gray-400 italic">Drop column fields here</span>
                    </div>
                </div>

                <!-- Values Drop Zone with Independent Aggregation & Show As -->
                <div
                    @dragover.prevent
                    @drop="onDrop($event, 'vals')"
                    class="flex flex-col bg-white p-2 rounded border border-gray-200 min-h-[85px]"
                >
                    <span class="font-bold text-[11px] text-gray-600 mb-1">Values</span>
                    <div class="flex flex-col gap-1.5 flex-grow">
                        <div
                            v-for="(vSpec, idx) in localVals"
                            :key="vSpec.field + '-' + idx"
                            class="p-1 rounded bg-amber-50 text-amber-900 border border-amber-200 text-[10px] flex flex-col gap-0.5"
                        >
                            <div class="flex items-center justify-between font-mono font-bold">
                                <span>{{ vSpec.field }}</span>
                                <button type="button" @click="removeField('vals', idx)" class="text-amber-600 hover:text-red-600 font-bold">×</button>
                            </div>
                            <div class="flex items-center justify-between gap-1">
                                <select
                                    v-model="vSpec.agg"
                                    @change="onConfigChange"
                                    class="border rounded px-1 py-0.5 text-[9px] bg-white text-gray-800"
                                >
                                    <option value="Sum">Sum</option>
                                    <option value="Count">Count</option>
                                    <option value="Average">Average</option>
                                    <option value="Min">Min</option>
                                    <option value="Max">Max</option>
                                </select>
                                <select
                                    v-model="vSpec.showAs"
                                    @change="onConfigChange"
                                    class="border rounded px-1 py-0.5 text-[9px] bg-white text-gray-800"
                                    title="Show Values As"
                                >
                                    <option value="None">Normal</option>
                                    <option value="% of Grand Total">% Grand Total</option>
                                    <option value="% of Column Total">% Column Total</option>
                                    <option value="% of Row Total">% Row Total</option>
                                </select>
                            </div>
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
                        <!-- Column Headers Row -->
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
                            <th v-if="showGrandTotals" class="p-1.5 bg-gray-300 text-gray-900 font-bold text-center sticky top-0 right-0 z-10">
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
                            <td v-if="showGrandTotals" class="p-1.5 font-bold text-right bg-gray-100/80 text-blue-900 sticky right-0">
                                {{ formatCell(rowItem.rowTotal) }}
                            </td>
                        </tr>

                        <!-- Grand Total Row -->
                        <tr v-if="showGrandTotals" class="bg-gray-200 font-bold border-t-2 border-gray-400 text-gray-900 sticky bottom-0 z-20">
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
            type: [Array, String],
            default: () => []
        },
        values: {
            type: [Array, String],
            default: () => []
        },
        filters: {
            type: Array,
            default: () => []
        },
        filterValues: {
            type: Object,
            default: () => ({})
        },
        aggregatorName: {
            type: String,
            default: 'Sum'
        },
        showRowSubtotals: {
            type: Boolean,
            default: true
        },
        showColSubtotals: {
            type: Boolean,
            default: true
        },
        showGrandTotals: {
            type: Boolean,
            default: true
        },
        emptyValuePlaceholder: {
            type: String,
            default: '—'
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
            localFilters: [],
            localFilterValues: {},
            localAggregator: 'Sum'
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
            const usedFields = new Set([
                ...this.localRows,
                ...this.localCols,
                ...this.localFilters,
                ...this.localVals.map(v => v.field)
            ]);
            return this.allColumns.filter(c => !usedFields.has(c));
        },
        filteredData() {
            if (!this.data || !this.data.length) return [];
            if (!this.localFilters.length) return this.data;

            return this.data.filter(row => {
                for (const fCol of this.localFilters) {
                    const selectedVal = this.localFilterValues[fCol];
                    if (selectedVal !== undefined && selectedVal !== null && selectedVal !== '') {
                        if (String(row[fCol]) !== String(selectedVal)) {
                            return false;
                        }
                    }
                }
                return true;
            });
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
            return 'No aggregated records match the current pivot selection or report filter.';
        },
        pivotMatrix() {
            if (this.serverPivotData && this.serverPivotData.rows) {
                return this.serverPivotData;
            }

            const dataToPivot = this.filteredData;
            if (!dataToPivot || !dataToPivot.length) return null;
            if (!this.localRows.length && !this.localCols.length) return null;

            const valSpecs = this.localVals.length
                ? this.localVals
                : [{ field: 'val', agg: this.localAggregator || 'Sum', showAs: 'None' }];

            const rowKeysSet = new Set();
            const colKeysSet = new Set();

            const getTupleKey = (row, fields) => fields.map(f => row[f] === undefined || row[f] === null ? '' : String(row[f]));

            dataToPivot.forEach(row => {
                const rKey = getTupleKey(row, this.localRows);
                const cKey = getTupleKey(row, this.localCols);
                rowKeysSet.add(JSON.stringify(rKey));
                colKeysSet.add(JSON.stringify(cKey));
            });

            const rowKeys = Array.from(rowKeysSet).map(s => JSON.parse(s));
            const baseColKeys = Array.from(colKeysSet).map(s => JSON.parse(s));

            // Map cells: cellMap[rKeyStr][cKeyStr][vSpecIdx] -> array of numbers
            const cellMap = {};
            dataToPivot.forEach(row => {
                const rKeyStr = JSON.stringify(getTupleKey(row, this.localRows));
                const cKeyStr = JSON.stringify(getTupleKey(row, this.localCols));

                if (!cellMap[rKeyStr]) cellMap[rKeyStr] = {};
                if (!cellMap[rKeyStr][cKeyStr]) {
                    cellMap[rKeyStr][cKeyStr] = valSpecs.map(() => []);
                }

                valSpecs.forEach((spec, vIdx) => {
                    const val = parseFloat(row[spec.field]);
                    if (!isNaN(val)) {
                        cellMap[rKeyStr][cKeyStr][vIdx].push(val);
                    }
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

            // Calculate raw aggregate matrix
            // Columns layout: if multiple valSpecs, expand colKeys with metric labels
            const expandedColKeys = [];
            if (baseColKeys.length && valSpecs.length > 1) {
                baseColKeys.forEach(cKey => {
                    valSpecs.forEach(spec => {
                        expandedColKeys.push([...cKey, `${spec.field} (${spec.agg})`]);
                    });
                });
            } else if (baseColKeys.length) {
                baseColKeys.forEach(cKey => expandedColKeys.push(cKey));
            } else if (valSpecs.length > 1) {
                valSpecs.forEach(spec => expandedColKeys.push([`${spec.field} (${spec.agg})`]));
            } else {
                expandedColKeys.push([]);
            }

            // Raw cells and row totals calculation
            const rawMatrixRows = [];
            const rawColAllValues = expandedColKeys.map(() => []);
            const rawGrandAllValues = valSpecs.map(() => []);

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
                            if (values.length) {
                                rowAllValues[vIdx].push(...values);
                                rawGrandAllValues[vIdx].push(...values);
                            }
                        });
                    });
                } else if (baseColKeys.length) {
                    const spec = valSpecs[0];
                    baseColKeys.forEach(cKey => {
                        const cKeyStr = JSON.stringify(cKey);
                        const values = cellMap[rKeyStr] && cellMap[rKeyStr][cKeyStr] ? cellMap[rKeyStr][cKeyStr][0] : [];
                        const val = calcAgg(values, spec.agg);
                        cells.push(val);
                        if (values.length) {
                            rowAllValues[0].push(...values);
                            rawGrandAllValues[0].push(...values);
                        }
                    });
                } else if (valSpecs.length > 1) {
                    valSpecs.forEach((spec, vIdx) => {
                        const values = cellMap[rKeyStr] && cellMap[rKeyStr]['[]'] ? cellMap[rKeyStr]['[]'][vIdx] : [];
                        const val = calcAgg(values, spec.agg);
                        cells.push(val);
                        if (values.length) {
                            rowAllValues[vIdx].push(...values);
                            rawGrandAllValues[vIdx].push(...values);
                        }
                    });
                } else {
                    const spec = valSpecs[0];
                    const values = cellMap[rKeyStr] && cellMap[rKeyStr]['[]'] ? cellMap[rKeyStr]['[]'][0] : [];
                    const val = calcAgg(values, spec.agg);
                    cells.push(val);
                    if (values.length) {
                        rowAllValues[0].push(...values);
                        rawGrandAllValues[0].push(...values);
                    }
                }

                // Row total
                const firstValTotal = calcAgg(rowAllValues[0], valSpecs[0].agg);
                rawMatrixRows.push({
                    rowKey: rKey,
                    cells,
                    rowTotal: firstValTotal
                });
            });

            // Column Totals
            const rawColTotals = expandedColKeys.map((cKey, cIdx) => {
                const colCells = rawMatrixRows.map(r => r.cells[cIdx]).filter(v => v !== null && v !== undefined);
                if (!colCells.length) return null;
                const vIdx = valSpecs.length > 1 ? (cIdx % valSpecs.length) : 0;
                return calcAgg(colCells, valSpecs[vIdx].agg);
            });

            // Grand Total
            const rawGrandTotal = calcAgg(rawGrandAllValues[0], valSpecs[0].agg);

            // Apply "Show Values As" secondary calculations if specified
            const hasShowAs = valSpecs.some(s => s.showAs && s.showAs !== 'None');
            if (!hasShowAs) {
                return {
                    colKeys: expandedColKeys,
                    rows: rawMatrixRows,
                    colTotals: rawColTotals,
                    grandTotal: rawGrandTotal
                };
            }

            // Post-process with Show Values As calculations
            const processedRows = rawMatrixRows.map(rowItem => {
                const newCells = rowItem.cells.map((cellVal, cIdx) => {
                    if (cellVal === null || cellVal === undefined) return null;
                    const vIdx = valSpecs.length > 1 ? (cIdx % valSpecs.length) : 0;
                    const showAs = valSpecs[vIdx].showAs;

                    if (showAs === '% of Grand Total') {
                        const targetGrand = rawGrandTotal || 1;
                        return (cellVal / targetGrand) * 100;
                    } else if (showAs === '% of Column Total') {
                        const targetCol = rawColTotals[cIdx] || 1;
                        return (cellVal / targetCol) * 100;
                    } else if (showAs === '% of Row Total') {
                        const targetRow = rowItem.rowTotal || 1;
                        return (cellVal / targetRow) * 100;
                    }
                    return cellVal;
                });

                return {
                    ...rowItem,
                    cells: newCells
                };
            });

            return {
                colKeys: expandedColKeys,
                rows: processedRows,
                colTotals: rawColTotals,
                grandTotal: rawGrandTotal
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
            handler(v) { this.syncLocalVals(v); },
            immediate: true,
            deep: true
        },
        values: {
            handler(v) { if (v && v.length) this.syncLocalVals(v); },
            immediate: true,
            deep: true
        },
        filters: {
            handler(v) { this.localFilters = [...(v || [])]; },
            immediate: true,
            deep: true
        },
        filterValues: {
            handler(v) { this.localFilterValues = { ...(v || {}) }; },
            immediate: true,
            deep: true
        },
        aggregatorName: {
            handler(v) {
                this.localAggregator = v || 'Sum';
                if (this.localVals.length === 1) {
                    this.localVals[0].agg = this.localAggregator;
                }
            },
            immediate: true
        }
    },
    methods: {
        syncLocalVals(valsProp) {
            if (!valsProp) {
                this.localVals = [];
                return;
            }
            if (typeof valsProp === 'string') {
                const parts = valsProp.split(',').map(s => s.trim()).filter(Boolean);
                this.localVals = parts.map(f => ({ field: f, agg: this.localAggregator || 'Sum', showAs: 'None' }));
                return;
            }
            if (Array.isArray(valsProp)) {
                this.localVals = valsProp.map(item => {
                    if (typeof item === 'object' && item !== null) {
                        return {
                            field: item.field || item.col || '',
                            agg: item.agg || item.aggregatorName || this.localAggregator || 'Sum',
                            showAs: item.showAs || 'None'
                        };
                    }
                    return {
                        field: String(item),
                        agg: this.localAggregator || 'Sum',
                        showAs: 'None'
                    };
                }).filter(v => v.field);
            }
        },
        formatCell(val) {
            if (val === null || val === undefined || isNaN(val)) return this.emptyValuePlaceholder || '—';
            if (Number.isInteger(val)) return val.toLocaleString();
            return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },
        getFilterOptions(col) {
            if (!this.data || !this.data.length) return [];
            const set = new Set();
            this.data.forEach(row => {
                if (row[col] !== undefined && row[col] !== null && row[col] !== '') {
                    set.add(String(row[col]));
                }
            });
            return Array.from(set).sort();
        },
        setFilterValue(col, val) {
            this.localFilterValues = { ...this.localFilterValues, [col]: val };
            this.onConfigChange();
        },
        onConfigChange() {
            const newConfig = {
                rows: this.localRows,
                cols: this.localCols,
                vals: this.localVals,
                values: this.localVals,
                filters: this.localFilters,
                filter_values: this.localFilterValues,
                filterValues: this.localFilterValues,
                aggregator_name: this.localVals.length ? this.localVals[0].agg : this.localAggregator,
                aggregatorName: this.localVals.length ? this.localVals[0].agg : this.localAggregator
            };
            this.$emit('update:config', newConfig);
            this.$emit('config_changed', newConfig);
        },
        addField(zone, col) {
            if (zone === 'rows' && !this.localRows.includes(col)) this.localRows.push(col);
            if (zone === 'cols' && !this.localCols.includes(col)) this.localCols.push(col);
            if (zone === 'filters' && !this.localFilters.includes(col)) this.localFilters.push(col);
            if (zone === 'vals' && !this.localVals.some(v => v.field === col)) {
                this.localVals.push({ field: col, agg: this.localAggregator || 'Sum', showAs: 'None' });
            }
            this.onConfigChange();
        },
        removeField(zone, idx) {
            if (zone === 'rows') this.localRows.splice(idx, 1);
            if (zone === 'cols') this.localCols.splice(idx, 1);
            if (zone === 'filters') {
                const removed = this.localFilters.splice(idx, 1)[0];
                if (removed && this.localFilterValues[removed]) {
                    delete this.localFilterValues[removed];
                }
            }
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
                ...this.pivotMatrix.colKeys.map(ck => ck.join(' - ') || 'Total')
            ];
            if (this.showGrandTotals) {
                headerRow.push('Grand Total');
            }
            rows.push(headerRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));

            this.pivotMatrix.rows.forEach(r => {
                const rowLabel = r.rowKey.length ? r.rowKey.join(' / ') : 'Total';
                const cells = r.cells.map(v => v === null || v === undefined ? '' : v);
                const csvRow = [rowLabel, ...cells];
                if (this.showGrandTotals) {
                    csvRow.push(r.rowTotal === null ? '' : r.rowTotal);
                }
                rows.push(csvRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));
            });

            if (this.showGrandTotals) {
                const grandTotalCells = this.pivotMatrix.colTotals.map(v => v === null || v === undefined ? '' : v);
                const grandTotalRow = ['Grand Total', ...grandTotalCells, this.pivotMatrix.grandTotal === null ? '' : this.pivotMatrix.grandTotal];
                rows.push(grandTotalRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));
            }

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
