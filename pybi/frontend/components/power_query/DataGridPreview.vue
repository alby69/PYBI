<template>
  <div class="data-grid-preview flex flex-col flex-grow w-full h-full bg-white overflow-hidden text-xs">
    <!-- Header Status & Toolbar Bar -->
    <div class="flex items-center justify-between p-2 bg-slate-100 border-b border-slate-300 flex-shrink-0">
      <div class="flex items-center gap-2">
        <span class="font-bold text-slate-800 text-xs">📊 Data Preview</span>
        <span v-if="selectedTable" class="px-2 py-0.5 bg-blue-100 text-blue-800 rounded font-mono text-[11px] font-semibold">
          {{ selectedTable }}
        </span>
      </div>

      <!-- Execution Status Info -->
      <div class="flex items-center gap-3 text-slate-500 text-[11px]">
        <span>Rows: <strong class="text-slate-800">{{ previewData.total_rows || rows.length || 0 }}</strong></span>
        <span>Columns: <strong class="text-slate-800">{{ previewData.total_columns || columns.length || 0 }}</strong></span>
        <span v-if="previewData.execution_time">Time: <strong class="text-slate-800">{{ (previewData.execution_time * 1000).toFixed(1) }} ms</strong></span>
      </div>
    </div>

    <!-- Loading State Overlay -->
    <div v-if="isLoading" class="flex-grow flex items-center justify-center bg-white/80 p-8">
      <div class="flex flex-col items-center gap-2 text-blue-600 font-semibold">
        <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span>Executing transformation & updating preview...</span>
      </div>
    </div>

    <!-- Empty State Banner -->
    <div v-else-if="!columns || columns.length === 0" class="flex-grow flex items-center justify-center p-8 bg-slate-50 text-slate-500 italic">
      No data available to display. Select a data source query or apply a transformation.
    </div>

    <!-- Data Grid with Horizontal & Vertical Overflow Scrolling -->
    <div v-else class="flex-grow overflow-x-auto overflow-y-auto border border-slate-200">
      <table class="w-full border-collapse text-left font-mono text-xs" style="white-space: nowrap;">
        <thead>
          <tr class="bg-slate-200 border-b border-slate-300 text-slate-800 font-bold sticky top-0 z-20">
            <!-- Row Index Header -->
            <th class="p-2 border-r border-slate-300 bg-slate-300 text-center w-12 sticky left-0 z-30">
              #
            </th>

            <!-- Dynamic Column Headers -->
            <th
              v-for="col in columns"
              :key="col.name || col"
              class="p-2 border-r border-slate-300 bg-slate-200 text-slate-800 group relative"
            >
              <div class="flex items-center justify-between gap-2">
                <!-- Column Type Icon Badge -->
                <button
                  @click.stop="toggleHeaderMenu(col.name || col)"
                  class="flex items-center gap-1.5 focus:outline-none hover:bg-slate-300 px-1 py-0.5 rounded"
                >
                  <span
                    :class="['px-1 rounded text-[10px] font-bold border', getTypeBadgeClass(col.type || getColumnType(col))]"
                  >
                    {{ getTypeIcon(col.type || getColumnType(col)) }}
                  </span>
                  <span class="font-bold text-xs text-slate-900">{{ col.name || col }}</span>
                  <span class="text-[9px] text-slate-500">▼</span>
                </button>
              </div>

              <!-- Header Dropdown Menu for Column Actions -->
              <div
                v-if="activeHeaderMenu === (col.name || col)"
                class="absolute left-0 top-full mt-1 w-48 bg-white border border-slate-300 rounded shadow-xl z-40 py-1 text-xs font-normal"
              >
                <button @click="handleColumnAction('sort-asc', col.name || col)" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
                  <span>⬆️</span> Sort Ascending
                </button>
                <button @click="handleColumnAction('sort-desc', col.name || col)" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
                  <span>⬇️</span> Sort Descending
                </button>
                <div class="border-t border-slate-200 my-1"></div>
                <button @click="handleColumnAction('rename', col.name || col)" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
                  <span>✏️</span> Rename Column...
                </button>
                <button @click="handleColumnAction('cast', col.name || col)" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
                  <span>🔄</span> Change Type...
                </button>
                <button @click="handleColumnAction('filter', col.name || col)" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
                  <span>🔍</span> Filter Column...
                </button>
                <div class="border-t border-slate-200 my-1"></div>
                <button @click="handleColumnAction('remove', col.name || col)" class="w-full text-left px-3 py-1.5 hover:bg-red-50 text-red-600 flex items-center gap-2">
                  <span>🗑️</span> Remove Column
                </button>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, rIdx) in rows"
            :key="rIdx"
            :class="[
              'border-b transition-colors',
              rIdx % 2 === 0 ? 'bg-white hover:bg-blue-50/60' : 'bg-slate-50/70 hover:bg-blue-50/60'
            ]"
          >
            <!-- Row Index Cell -->
            <td class="p-1.5 border-r border-slate-200 text-center font-sans text-slate-400 bg-slate-100/80 sticky left-0 z-10 w-12 text-[10px]">
              {{ rIdx + 1 }}
            </td>

            <!-- Cell Values -->
            <td
              v-for="col in columns"
              :key="col.name || col"
              class="p-2 border-r border-slate-200 text-slate-800"
            >
              <span v-if="row[col.name || col] === null || row[col.name || col] === undefined" class="text-slate-300 italic">
                null
              </span>
              <span v-else>
                {{ row[col.name || col] }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { useUiStore } from '../../stores/uiStore.js';

export default {
  name: 'DataGridPreview',
  props: {
    columnsProp: {
      type: Array,
      default: () => []
    },
    rowsProp: {
      type: Array,
      default: () => []
    }
  },
  emits: ['column-action'],
  data() {
    return {
      activeHeaderMenu: null
    };
  },
  computed: {
    store() {
      try { return useUiStore(); } catch (e) { return null; }
    },
    selectedTable() {
      return this.store ? this.store.selectedTable : null;
    },
    isLoading() {
      return this.store ? this.store.isLoadingPreview : false;
    },
    previewData() {
      return this.store ? (this.store.previewData || {}) : {};
    },
    columns() {
      if (this.previewData && this.previewData.columns && this.previewData.columns.length > 0) {
        return this.previewData.columns;
      }
      if (this.$props.columnsProp && this.$props.columnsProp.length > 0) {
        return this.$props.columnsProp;
      }
      if (this.rows.length > 0) {
        return Object.keys(this.rows[0]);
      }
      return [];
    },
    rows() {
      if (this.previewData && this.previewData.rows && this.previewData.rows.length > 0) {
        return this.previewData.rows;
      }
      return this.$props.rowsProp || [];
    }
  },
  methods: {
    toggleHeaderMenu(colName) {
      if (this.activeHeaderMenu === colName) {
        this.activeHeaderMenu = null;
      } else {
        this.activeHeaderMenu = colName;
      }
    },
    handleColumnAction(action, colName) {
      this.activeHeaderMenu = null;
      this.$emit('column-action', { action, column: colName });
    },
    getColumnType(colName) {
      if (!this.rows || !this.rows.length) return 'text';
      const sampleVal = this.rows[0][colName];
      if (typeof sampleVal === 'number') {
        return Number.isInteger(sampleVal) ? 'int' : 'decimal';
      }
      if (typeof sampleVal === 'boolean') return 'boolean';
      if (sampleVal instanceof Date || (typeof sampleVal === 'string' && !isNaN(Date.parse(sampleVal)) && sampleVal.includes('-'))) {
        return 'date';
      }
      return 'text';
    },
    getTypeIcon(typeStr) {
      const t = (typeStr || '').toLowerCase();
      if (t.includes('int')) return '123';
      if (t.includes('dec') || t.includes('float') || t.includes('double')) return '1.2';
      if (t.includes('date') || t.includes('time')) return '📅';
      if (t.includes('bool')) return 'TRUE';
      return 'ABC';
    },
    getTypeBadgeClass(typeStr) {
      const t = (typeStr || '').toLowerCase();
      if (t.includes('int') || t.includes('dec') || t.includes('float')) {
        return 'bg-amber-50 text-amber-800 border-amber-300';
      }
      if (t.includes('date') || t.includes('time')) {
        return 'bg-purple-50 text-purple-800 border-purple-300';
      }
      if (t.includes('bool')) {
        return 'bg-emerald-50 text-emerald-800 border-emerald-300';
      }
      return 'bg-blue-50 text-blue-800 border-blue-300';
    }
  },
  mounted() {
    document.addEventListener('click', () => {
      this.activeHeaderMenu = null;
    });
  }
};
</script>
