<template>
  <div class="data-grid-preview flex flex-col flex-nowrap flex-grow w-full h-full min-h-0 bg-white overflow-hidden text-xs">
    <div class="flex items-center justify-between p-2 bg-slate-100 border-b border-slate-300 flex-shrink-0">
      <div class="flex items-center gap-2">
        <span class="font-bold text-slate-800 text-xs">📊 Data Preview</span>
        <span v-if="selectedTable" class="px-2 py-0.5 bg-blue-100 text-blue-800 rounded font-mono text-[11px] font-semibold">
          {{ selectedTable }}
        </span>
        <span v-if="activeStepIndex === 0" class="px-2 py-0.5 bg-slate-200 text-slate-700 rounded text-[10px] font-semibold">Source</span>
        <span v-else class="px-2 py-0.5 bg-amber-100 text-amber-800 rounded text-[10px] font-semibold">After step {{ activeStepIndex }}</span>
      </div>
      <div class="flex items-center gap-3 text-slate-500 text-[11px]">
        <span>Rows: <strong class="text-slate-800">{{ previewData.total_rows || rows.length || 0 }}</strong></span>
        <span>Columns: <strong class="text-slate-800">{{ previewData.total_columns || columns.length || 0 }}</strong></span>
        <span v-if="previewData.execution_time">Time: <strong class="text-slate-800">{{ (previewData.execution_time * 1000).toFixed(1) }} ms</strong></span>
      </div>
    </div>

    <div v-if="store.error" class="px-3 py-1.5 bg-red-50 border-b border-red-200 text-red-700 text-[11px] flex items-center gap-2">
      <span>⚠</span>
      <span class="truncate" :title="store.error">{{ store.error }}</span>
      <button @click="store.error = null" class="ml-auto font-bold">×</button>
    </div>

    <div v-if="isLoading" class="flex-grow flex items-center justify-center bg-white/80 p-8">
      <div class="flex flex-col items-center gap-2 text-blue-600 font-semibold">
        <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span>Executing transformation & updating preview...</span>
      </div>
    </div>

    <div v-else-if="!columns || columns.length === 0" class="flex-grow flex items-center justify-center p-8 bg-slate-50 text-slate-500 italic">
      No data available to display. Select a data source query or apply a transformation.
    </div>

    <template v-else>
      <nicegui-DataProfilingBar
        v-if="store.showProfilingBar && store.profilingColumn"
        :column="store.profilingColumn"
        :rows="rows"
        :type="columnType(store.profilingColumn)"
        @close="store.selectProfilingColumn(store.profilingColumn)"
      />

      <div class="flex-grow min-h-0 overflow-x-auto overflow-y-auto border border-slate-200">
        <table class="w-full border-collapse text-left font-mono text-xs" style="white-space: nowrap;">
          <thead>
            <tr class="bg-slate-200 border-b border-slate-300 text-slate-800 font-bold sticky top-0 z-20">
              <th class="p-2 border-r border-slate-300 bg-slate-300 text-center w-12 sticky left-0 z-30">#</th>
              <th
                v-for="col in columns"
                :key="col"
                class="p-2 border-r border-slate-300 bg-slate-200 text-slate-800 relative"
              >
                <nicegui-ColumnHeader
                  :column="col"
                  :type="columnType(col)"
                  :icon="getTypeIcon(col)"
                  :sort-direction="sortState.column === col ? sortState.direction : ''"
                  @toggle="toggleHeaderMenu"
                />
                <nicegui-ColumnHeaderMenu
                  v-if="activeHeaderMenu === col"
                  :column="col"
                  @action="handleColumnAction"
                  @close="activeHeaderMenu = null"
                />
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, rIdx) in rows"
              :key="rIdx"
              :class="['border-b transition-colors', rIdx % 2 === 0 ? 'bg-white hover:bg-blue-50/60' : 'bg-slate-50/70 hover:bg-blue-50/60']"
            >
              <td class="p-1.5 border-r border-slate-200 text-center font-sans text-slate-400 bg-slate-100/80 sticky left-0 z-10 w-12 text-[10px]">
                {{ rIdx + 1 }}
              </td>
              <td v-for="col in columns" :key="col" :class="['p-2 border-r border-slate-200', cellClass(row[col])]">
                <span v-if="row[col] === null || row[col] === undefined" class="text-slate-300 italic">null</span>
                <span v-else>{{ formatCell(row[col]) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script>
import { useUiStore } from 'pybi-store';

export default {
  name: 'DataGridPreview',
  props: {
    columnsProp: { type: Array, default: () => [] },
    rowsProp: { type: Array, default: () => [] }
  },
  emits: ['column-action'],
  data() {
    return {
      activeHeaderMenu: null,
      sortState: { column: '', direction: '' }
    };
  },
  computed: {
    store() {
      return useUiStore();
    },
    selectedTable() {
      return this.store.selectedTable;
    },
    activeStepIndex() {
      return this.store.activeStepIndex;
    },
    isLoading() {
      return this.store.isLoadingPreview;
    },
    previewData() {
      return this.store.previewData || {};
    },
    columns() {
      if (this.previewData.columns?.length) return this.previewData.columns;
      if (this.columnsProp.length) return this.columnsProp;
      if (this.rows.length) return Object.keys(this.rows[0]);
      return [];
    },
    rows() {
      if (this.previewData.rows?.length) return this.previewData.rows;
      return this.rowsProp || [];
    }
  },
  methods: {
    toggleHeaderMenu(column) {
      this.activeHeaderMenu = this.activeHeaderMenu === column ? null : column;
    },
    handleColumnAction(action, column) {
      this.activeHeaderMenu = null;
      if (action === 'profile') {
        this.store.selectProfilingColumn(column);
        return;
      }
      if (action === 'sort-asc' || action === 'sort-desc') {
        this.sortState = { column, direction: action === 'sort-desc' ? 'desc' : 'asc' };
      }
      this.$emit('column-action', { action, column });
    },
    columnType(column) {
      const declared = this.previewData.data_types?.[column];
      if (declared) return declared;
      const sample = this.rows.find(row => row[column] !== null && row[column] !== undefined)?.[column];
      if (typeof sample === 'number') return Number.isInteger(sample) ? 'int' : 'decimal';
      if (typeof sample === 'boolean') return 'boolean';
      if (sample instanceof Date) return 'date';
      if (typeof sample === 'string' && !Number.isNaN(Date.parse(sample)) && /\d{4}-\d{2}-\d{2}/.test(sample)) return 'date';
      return 'text';
    },
    getTypeIcon(column) {
      const type = (this.columnType(column) || '').toLowerCase();
      if (type.includes('int')) return '123';
      if (type.includes('dec') || type.includes('float') || type.includes('double')) return '1.2';
      if (type.includes('date') || type.includes('time')) return '📅';
      if (type.includes('bool')) return 'TRUE';
      return 'ABC';
    },
    formatCell(value) {
      if (typeof value === 'number') {
        return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
      }
      if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE';
      if (typeof value === 'object') return JSON.stringify(value);
      return value;
    },
    cellClass(value) {
      if (value === null || value === undefined) return '';
      if (typeof value === 'number') return 'text-right tabular-nums text-slate-900';
      if (typeof value === 'boolean') return 'text-emerald-700 font-semibold';
      return 'text-slate-800';
    }
  },
  mounted() {
    document.addEventListener('click', () => {
      this.activeHeaderMenu = null;
    });
  }
};
</script>
