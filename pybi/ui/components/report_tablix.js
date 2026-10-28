import { reactive, computed } from 'vue';

export default {
    template: `
        <div class="report-tablix-container w-full h-full flex flex-col text-xs font-sans border rounded bg-white overflow-hidden shadow-sm">
            <!-- Tablix Header Bar -->
            <div class="flex items-center justify-between px-3 py-1.5 bg-slate-100 border-b shrink-0 text-slate-800">
                <div class="flex items-center gap-2 font-bold">
                    <span>📊 Report Tablix</span>
                    <span v-if="rowGroups.length" class="text-[10px] text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                        Raggruppamenti: {{ rowGroups.join(' › ') }}
                    </span>
                </div>
                <div class="flex items-center gap-2 text-[10px]">
                    <button
                        type="button"
                        @click="expandAll"
                        class="px-2 py-0.5 rounded bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium cursor-pointer"
                    >Espandi Tutti</button>
                    <button
                        type="button"
                        @click="collapseAll"
                        class="px-2 py-0.5 rounded bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium cursor-pointer"
                    >Collassa Tutti</button>
                    <button
                        type="button"
                        @click="exportTablixCSV"
                        class="px-2 py-0.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-medium cursor-pointer"
                    >📥 CSV</button>
                </div>
            </div>

            <!-- Tablix Hierarchy Table -->
            <div class="flex-grow overflow-auto p-1">
                <table v-if="hierarchicalRows.length" class="w-full border-collapse font-mono text-[11px]">
                    <thead>
                        <tr class="bg-slate-200 text-slate-800 font-bold border-b sticky top-0 z-10">
                            <th class="p-1.5 border-r text-left bg-slate-200 sticky left-0 min-w-[180px]">
                                {{ rowGroups.join(' / ') || 'Gruppo / Elemento' }}
                            </th>
                            <th
                                v-for="m in activeMeasures"
                                :key="m.col || m"
                                class="p-1.5 border-r text-right bg-slate-200 min-w-[100px]"
                            >
                                {{ m.title || (m.col ? (m.col + ' (' + (m.agg || 'Sum') + ')') : m) }}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="(row, idx) in hierarchicalRows"
                            :key="row.key"
                            :class="getRowClass(row)"
                            class="border-b transition hover:bg-blue-50/60 cursor-pointer"
                            @click="onRowClick(row)"
                        >
                            <!-- Hierarchy Row Group Label -->
                            <td
                                class="p-1.5 border-r font-semibold flex items-center gap-1.5 sticky left-0 bg-white/90"
                                :style="{ paddingLeft: (row.level * 16 + 8) + 'px' }"
                            >
                                <button
                                    v-if="row.hasChildren"
                                    type="button"
                                    @click.stop="toggleGroup(row.key)"
                                    class="w-4 h-4 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold flex items-center justify-center text-[10px] cursor-pointer shrink-0 border"
                                >
                                    {{ isCollapsed(row.key) ? '+' : '-' }}
                                </button>
                                <span v-else class="w-4 h-4 inline-block shrink-0"></span>
                                <span :class="row.isTotal ? 'font-bold text-slate-900' : 'text-slate-800'">
                                    {{ row.label }}
                                </span>
                            </td>

                            <!-- Measure Values -->
                            <td
                                v-for="(m, mIdx) in activeMeasures"
                                :key="mIdx"
                                class="p-1.5 border-r text-right"
                                :style="getConditionalStyle(row.values[m.col || m], m.col || m)"
                            >
                                <span v-if="getConditionalIcon(row.values[m.col || m], m.col || m)" class="mr-1">
                                    {{ getConditionalIcon(row.values[m.col || m], m.col || m) }}
                                </span>
                                {{ formatValue(row.values[m.col || m]) }}
                            </td>
                        </tr>

                        <!-- Grand Total Row -->
                        <tr v-if="showGrandTotal" class="bg-slate-300 font-extrabold text-slate-950 border-t-2 border-slate-500 sticky bottom-0">
                            <td class="p-1.5 border-r sticky left-0 bg-slate-300">
                                Total Generale (Grand Total)
                            </td>
                            <td
                                v-for="(m, mIdx) in activeMeasures"
                                :key="mIdx"
                                class="p-1.5 border-r text-right text-blue-950 font-black"
                            >
                                {{ formatValue(grandTotalValues[m.col || m]) }}
                            </td>
                        </tr>
                    </tbody>
                </table>

                <div v-else class="p-4 text-center text-slate-500 italic">
                    ⚠️ Nessun dato disponibile per Tablix. Selezionare dati e raggruppamenti.
                </div>
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
        rowGroups: {
            type: Array,
            default: () => []
        },
        measures: {
            type: Array,
            default: () => []
        },
        conditionalFormatting: {
            type: Array,
            default: () => []
        },
        drillAction: {
            type: Object,
            default: () => null
        },
        showGrandTotal: {
            type: Boolean,
            default: true
        }
    },
    data() {
        return {
            collapsedKeys: {}
        };
    },
    computed: {
        activeMeasures() {
            if (this.measures && this.measures.length) {
                return this.measures.map(m => typeof m === 'string' ? { col: m, agg: 'Sum', title: m } : m);
            }
            if (this.columns && this.columns.length) {
                const numericCols = this.columns.filter(c => !this.rowGroups.includes(c));
                if (numericCols.length) {
                    return numericCols.slice(0, 4).map(c => ({ col: c, agg: 'Sum', title: c }));
                }
            }
            return [{ col: 'val', agg: 'Sum', title: 'Valore' }];
        },
        hierarchicalRows() {
            if (!this.data || !this.data.length) return [];
            const groups = this.rowGroups.length ? this.rowGroups : (this.columns.length ? [this.columns[0]] : []);
            const rows = [];

            const buildLevel = (items, level, parentKey, parentPath) => {
                if (level >= groups.length) return;
                const groupField = groups[level];
                const groupedMap = {};

                items.forEach(item => {
                    const val = item[groupField] !== undefined && item[groupField] !== null ? String(item[groupField]) : 'N/D';
                    if (!groupedMap[val]) groupedMap[val] = [];
                    groupedMap[val].push(item);
                });

                Object.keys(groupedMap).forEach(gVal => {
                    const gItems = groupedMap[gVal];
                    const currentKey = parentKey ? `${parentKey}::${gVal}` : gVal;
                    const currentPath = { ...parentPath, [groupField]: gVal };
                    const hasChildren = level < groups.length - 1;

                    // Calculate group measure aggregations
                    const measureVals = {};
                    this.activeMeasures.forEach(m => {
                        const colName = m.col || m;
                        const nums = gItems.map(it => parseFloat(it[colName])).filter(v => !isNaN(v));
                        measureVals[colName] = this.calcAgg(nums, m.agg || 'Sum');
                    });

                    rows.push({
                        key: currentKey,
                        label: gVal,
                        level,
                        hasChildren,
                        isTotal: false,
                        values: measureVals,
                        path: currentPath,
                        rawItems: gItems
                    });

                    // Recurse down children if not collapsed
                    if (hasChildren && !this.collapsedKeys[currentKey]) {
                        buildLevel(gItems, level + 1, currentKey, currentPath);
                    }
                });
            };

            buildLevel(this.data, 0, '', {});
            return rows;
        },
        grandTotalValues() {
            if (!this.data || !this.data.length) return {};
            const totals = {};
            this.activeMeasures.forEach(m => {
                const colName = m.col || m;
                const nums = this.data.map(it => parseFloat(it[colName])).filter(v => !isNaN(v));
                totals[colName] = this.calcAgg(nums, m.agg || 'Sum');
            });
            return totals;
        }
    },
    methods: {
        toggleGroup(key) {
            this.collapsedKeys[key] = !this.collapsedKeys[key];
        },
        isCollapsed(key) {
            return !!this.collapsedKeys[key];
        },
        expandAll() {
            this.collapsedKeys = {};
        },
        collapseAll() {
            const allKeys = {};
            this.hierarchicalRows.forEach(r => {
                if (r.hasChildren) allKeys[r.key] = true;
            });
            this.collapsedKeys = allKeys;
        },
        calcAgg(values, agg) {
            if (!values || !values.length) return 0;
            const name = (agg || 'Sum').toLowerCase();
            if (name === 'count') return values.length;
            if (name === 'average' || name === 'avg') return values.reduce((a, b) => a + b, 0) / values.length;
            if (name === 'min') return Math.min(...values);
            if (name === 'max') return Math.max(...values);
            return values.reduce((a, b) => a + b, 0);
        },
        formatValue(val) {
            if (val === null || val === undefined || isNaN(val)) return '—';
            if (Number.isInteger(val)) return val.toLocaleString();
            return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        },
        getRowClass(row) {
            if (row.level === 0) return 'bg-slate-50 font-bold';
            if (row.level === 1) return 'bg-white font-semibold';
            return 'bg-white text-slate-700';
        },
        getConditionalStyle(val, colName) {
            if (val === null || val === undefined || isNaN(val)) return {};
            if (!this.conditionalFormatting || !this.conditionalFormatting.length) return {};

            for (const rule of this.conditionalFormatting) {
                if (rule.column && rule.column !== colName) continue;
                const op = rule.operator || rule.rule || '>';
                const target = parseFloat(rule.value);
                let matched = false;

                if (op === '>' && val > target) matched = true;
                else if (op === '>=' && val >= target) matched = true;
                else if (op === '<' && val < target) matched = true;
                else if (op === '<=' && val <= target) matched = true;
                else if ((op === '==' || op === '=') && val === target) matched = true;
                else if (op === '!=' && val !== target) matched = true;

                if (matched && rule.style) {
                    return {
                        color: rule.style.color || rule.color || 'inherit',
                        backgroundColor: rule.style.backgroundColor || rule.style.background || rule.background || 'transparent',
                        fontWeight: rule.style.fontWeight || 'normal'
                    };
                }
            }
            return {};
        },
        getConditionalIcon(val, colName) {
            if (!this.conditionalFormatting || !this.conditionalFormatting.length) return '';
            for (const rule of this.conditionalFormatting) {
                if (rule.column && rule.column !== colName) continue;
                const op = rule.operator || rule.rule || '>';
                const target = parseFloat(rule.value);
                let matched = false;

                if (op === '>' && val > target) matched = true;
                else if (op === '>=' && val >= target) matched = true;
                else if (op === '<' && val < target) matched = true;
                else if (op === '<=' && val <= target) matched = true;

                if (matched && (rule.style?.icon || rule.icon)) {
                    const ic = rule.style?.icon || rule.icon;
                    if (ic === 'trending_up') return '📈';
                    if (ic === 'trending_down') return '📉';
                    return ic;
                }
            }
            return '';
        },
        onRowClick(row) {
            const payload = {
                path: row.path,
                label: row.label,
                level: row.level,
                values: row.values,
                drillAction: this.drillAction
            };
            this.$emit('row_click', payload);
            this.$emit('drill_click', payload);
        },
        exportTablixCSV() {
            const rows = [];
            const header = [this.rowGroups.join(' / ') || 'Group', ...this.activeMeasures.map(m => m.title || m.col || m)];
            rows.push(header.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));

            this.hierarchicalRows.forEach(r => {
                const vals = this.activeMeasures.map(m => r.values[m.col || m] ?? '');
                const line = [r.label, ...vals];
                rows.push(line.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','));
            });

            const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(rows.join('\n'));
            const link = document.createElement('a');
            link.setAttribute('href', csvContent);
            link.setAttribute('download', 'tablix_export.csv');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
};
