import { reactive, ref, computed, watch, onMounted } from 'vue';

export default {
    template: `
        <div class="report-parameters-panel bg-white border rounded shadow-sm flex flex-col font-sans text-xs transition-all duration-300" :class="isCollapsed ? 'w-10' : 'w-72'">
            <!-- Panel Header -->
            <div class="flex items-center justify-between p-2.5 bg-slate-100 border-b select-none">
                <div v-if="!isCollapsed" class="flex items-center gap-2 font-bold text-slate-800">
                    <span>🎛️ Parametri Report</span>
                    <span v-if="hasActiveFilters" class="px-1.5 py-0.5 text-[9px] bg-blue-600 text-white rounded-full font-semibold">
                        {{ activeFilterCount }}
                    </span>
                </div>
                <button
                    type="button"
                    @click="isCollapsed = !isCollapsed"
                    class="p-1 rounded hover:bg-slate-200 text-slate-600 transition cursor-pointer"
                    :title="isCollapsed ? 'Espandi Parametri' : 'Riduci Panel'"
                >
                    {{ isCollapsed ? '⏩' : '◀' }}
                </button>
            </div>

            <!-- Panel Content -->
            <div v-if="!isCollapsed" class="flex-grow flex flex-col justify-between p-3 overflow-y-auto gap-4">
                <div class="flex flex-col gap-3">
                    <div v-for="param in parameterList" :key="param.name" class="flex flex-col gap-1">
                        <label class="font-bold text-slate-700 flex items-center justify-between">
                            <span>{{ param.label || param.name }}</span>
                            <span v-if="param.dependsOn" class="text-[9px] text-slate-400 font-normal">
                                (Dipende da: {{ param.dependsOn }})
                            </span>
                        </label>

                        <!-- Parameter Select Input / Filter -->
                        <div class="relative">
                            <input
                                type="text"
                                v-model="searchQueries[param.name]"
                                :placeholder="'Cerca ' + (param.label || param.name) + '...'"
                                class="w-full px-2 py-1.5 border rounded bg-slate-50 text-slate-800 focus:bg-white focus:outline-none focus:border-blue-500 text-xs"
                            />
                            <!-- Selected Chips -->
                            <div v-if="selectedValues[param.name] && selectedValues[param.name].length" class="flex flex-wrap gap-1 mt-1.5">
                                <span
                                    v-for="val in selectedValues[param.name]"
                                    :key="val"
                                    class="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full text-[10px] font-medium"
                                >
                                    {{ val }}
                                    <button type="button" @click="removeChip(param.name, val)" class="hover:text-blue-900 font-bold">×</button>
                                </span>
                            </div>

                            <!-- Options Dropdown List -->
                            <div
                                v-if="searchQueries[param.name]"
                                class="absolute z-30 left-0 right-0 mt-1 max-h-36 overflow-y-auto bg-white border rounded shadow-lg p-1 text-slate-700"
                            >
                                <div
                                    v-for="opt in getFilteredOptions(param.name)"
                                    :key="opt"
                                    @click="selectOption(param.name, opt)"
                                    class="px-2 py-1 hover:bg-blue-50 cursor-pointer rounded flex items-center justify-between"
                                    :class="isSelected(param.name, opt) ? 'bg-blue-50 font-bold text-blue-700' : ''"
                                >
                                    <span>{{ opt }}</span>
                                    <span v-if="isSelected(param.name, opt)" class="text-blue-600">✓</span>
                                </div>
                                <div v-if="!getFilteredOptions(param.name).length" class="p-2 text-center text-slate-400 italic">
                                    Nessuna opzione trovata
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Apply & Reset Buttons Footer -->
                <div class="flex flex-col gap-2 pt-2 border-t mt-2">
                    <button
                        type="button"
                        @click="applyParameters"
                        :disabled="isApplying"
                        class="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold rounded flex items-center justify-center gap-2 shadow-sm transition cursor-pointer"
                    >
                        <span v-if="isApplying" class="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                        <span>{{ isApplying ? 'Esecuzione Query...' : '🚀 Applica Report' }}</span>
                    </button>
                    <button
                        type="button"
                        @click="resetParameters"
                        class="w-full py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded text-[11px] cursor-pointer"
                    >
                        Reset Filtri
                    </button>
                </div>
            </div>
        </div>
    `,
    props: {
        projectId: {
            type: String,
            default: 'default'
        },
        parameters: {
            type: Array,
            default: () => [
                { name: 'Paese', table: 'regional_sales', column: 'region', label: 'Paese / Regione' },
                { name: 'SottoRegione', table: 'regional_sales', column: 'sub_region', label: 'Sotto-Regione', dependsOn: 'Paese' }
            ]
        },
        initialValues: {
            type: Object,
            default: () => ({})
        }
    },
    data() {
        return {
            isCollapsed: false,
            isApplying: false,
            selectedValues: {},
            optionsMap: {},
            searchQueries: {}
        };
    },
    computed: {
        parameterList() {
            return this.parameters || [];
        },
        activeFilterCount() {
            let cnt = 0;
            Object.values(this.selectedValues).forEach(arr => {
                if (Array.isArray(arr) && arr.length) cnt += arr.length;
            });
            return cnt;
        },
        hasActiveFilters() {
            return this.activeFilterCount > 0;
        }
    },
    mounted() {
        this.selectedValues = JSON.parse(JSON.stringify(this.initialValues || {}));
        this.parameterList.forEach(param => {
            if (!this.selectedValues[param.name]) {
                this.selectedValues[param.name] = [];
            }
            this.searchQueries[param.name] = '';
            this.fetchOptions(param);
        });
    },
    methods: {
        async fetchOptions(param) {
            const parentFilters = {};
            if (param.dependsOn && this.selectedValues[param.dependsOn]?.length) {
                const parentParam = this.parameterList.find(p => p.name === param.dependsOn);
                if (parentParam) {
                    parentFilters[parentParam.column || parentParam.name] = this.selectedValues[param.dependsOn];
                }
            }

            try {
                const res = await fetch(`/api/v1/projects/${this.projectId}/semantic/parameters`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        table_name: param.table,
                        column_name: param.column || param.name,
                        parent_filters: parentFilters
                    })
                });
                if (res.ok) {
                    const data = await res.json();
                    this.optionsMap[param.name] = data.options || [];
                } else {
                    this.optionsMap[param.name] = [];
                }
            } catch (err) {
                console.error('Parameter fetch error:', err);
                this.optionsMap[param.name] = [];
            }
        },
        getFilteredOptions(paramName) {
            const opts = this.optionsMap[paramName] || [];
            const query = (this.searchQueries[paramName] || '').toLowerCase().trim();
            if (!query) return opts;
            return opts.filter(o => String(o).toLowerCase().includes(query));
        },
        isSelected(paramName, opt) {
            const list = this.selectedValues[paramName] || [];
            return list.includes(opt);
        },
        selectOption(paramName, opt) {
            if (!this.selectedValues[paramName]) this.selectedValues[paramName] = [];
            if (!this.selectedValues[paramName].includes(opt)) {
                this.selectedValues[paramName].push(opt);
            } else {
                this.selectedValues[paramName] = this.selectedValues[paramName].filter(o => o !== opt);
            }

            // Invalidate and refresh dependent options
            this.parameterList.forEach(child => {
                if (child.dependsOn === paramName) {
                    this.selectedValues[child.name] = [];
                    this.fetchOptions(child);
                }
            });
        },
        removeChip(paramName, opt) {
            if (this.selectedValues[paramName]) {
                this.selectedValues[paramName] = this.selectedValues[paramName].filter(o => o !== opt);
                this.parameterList.forEach(child => {
                    if (child.dependsOn === paramName) {
                        this.selectedValues[child.name] = [];
                        this.fetchOptions(child);
                    }
                });
            }
        },
        applyParameters() {
            this.isApplying = true;
            this.$emit('apply_parameters', { filters: JSON.parse(JSON.stringify(this.selectedValues)) });
            setTimeout(() => {
                this.isApplying = false;
            }, 400);
        },
        resetParameters() {
            this.selectedValues = {};
            this.parameterList.forEach(p => {
                this.selectedValues[p.name] = [];
                this.searchQueries[p.name] = '';
                this.fetchOptions(p);
            });
            this.applyParameters();
        }
    }
};
