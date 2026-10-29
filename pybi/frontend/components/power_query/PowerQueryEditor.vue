<template>
  <div class="power-query-editor flex flex-col w-full h-screen bg-slate-100 font-sans text-slate-800 overflow-hidden select-none">
    <!-- BLOCK 1: RIBBON TOOLBAR -->
    <PowerQueryRibbon @action="handleRibbonAction" />

    <!-- BLOCK 5: FORMULA BAR (fx) -->
    <FormulaBar @apply-formula="handleFormulaApply" />

    <!-- CENTRAL WORKSPACE (3 PANELS: QUERIES PANE | DATA GRID | QUERY SETTINGS) -->
    <div class="flex flex-grow w-full overflow-hidden relative">
      <!-- BLOCK 2: QUERIES PANE (Left) -->
      <QueriesPane
        :tables="tables"
        @select-query="handleSelectQuery"
        @action="handleQueryAction"
      />

      <!-- BLOCK 3: DATA GRID PREVIEW (Center) -->
      <DataGridPreview
        @column-action="handleColumnAction"
      />

      <!-- BLOCK 4: QUERY SETTINGS & APPLIED STEPS (Right) -->
      <AppliedStepsPanel
        @edit-step-settings="handleEditStepSettings"
        @query-renamed="handleQueryRenamed"
      />
    </div>

    <!-- STATUS BAR -->
    <div class="bg-slate-800 text-slate-300 text-[11px] px-3 py-1 flex items-center justify-between border-t border-slate-700 flex-shrink-0">
      <div class="flex items-center gap-4">
        <span>Active Table: <strong class="text-white">{{ selectedTable || 'None' }}</strong></span>
        <span>Rows: <strong class="text-white">{{ totalRows }}</strong></span>
        <span>Columns: <strong class="text-white">{{ totalColumns }}</strong></span>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="executionTime">Execution Time: <strong class="text-emerald-400">{{ (executionTime * 1000).toFixed(1) }} ms</strong></span>
        <span class="text-slate-400">Power Query Engine (DuckDB / SQL)</span>
      </div>
    </div>

    <!-- MODAL DIALOGS -->
    <CustomColumnModal
      v-model="isCustomColumnModalOpen"
      @add-column="handleAddCustomColumn"
    />
  </div>
</template>

<script>
import PowerQueryRibbon from './PowerQueryRibbon.vue';
import QueriesPane from './QueriesPane.vue';
import DataGridPreview from './DataGridPreview.vue';
import AppliedStepsPanel from './AppliedStepsPanel.vue';
import FormulaBar from './FormulaBar.vue';
import CustomColumnModal from './CustomColumnModal.vue';
import { useUiStore } from '../../stores/uiStore.js';

export default {
  name: 'PowerQueryEditor',
  components: {
    PowerQueryRibbon,
    QueriesPane,
    DataGridPreview,
    AppliedStepsPanel,
    FormulaBar,
    CustomColumnModal
  },
  props: {
    tablesProp: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      isCustomColumnModalOpen: false
    };
  },
  computed: {
    store() {
      try { return useUiStore(); } catch (e) { return null; }
    },
    selectedTable() {
      return this.store ? this.store.selectedTable : null;
    },
    tables() {
      if (this.$props.tablesProp && this.$props.tablesProp.length > 0) {
        return this.$props.tablesProp;
      }
      if (this.store && this.store.appliedStepsByTable) {
        return Object.keys(this.store.appliedStepsByTable);
      }
      return ['sales_data.csv'];
    },
    totalRows() {
      return this.store?.previewData?.total_rows || this.store?.previewData?.rows?.length || 0;
    },
    totalColumns() {
      return this.store?.previewData?.total_columns || this.store?.previewData?.columns?.length || 0;
    },
    executionTime() {
      return this.store?.previewData?.execution_time || 0;
    }
  },
  methods: {
    handleRibbonAction({ action, payload }) {
      if (action === 'add-custom-column') {
        this.isCustomColumnModalOpen = true;
      } else if (action === 'filter-rows') {
        this.addStep({ operation: 'filter', name: 'Filtered Rows', params: { condition: "amount > 0" } });
      } else if (action === 'remove-columns') {
        this.addStep({ operation: 'remove_column', name: 'Removed Column', params: {} });
      } else if (action === 'split-column') {
        this.addStep({ operation: 'split_column', name: 'Split Column by Delimiter', params: { delimiter: '_' } });
      } else if (action === 'replace-values') {
        this.addStep({ operation: 'replace_values', name: 'Replaced Values', params: { old_value: '', new_value: 'N/A' } });
      }
    },
    handleFormulaApply(formulaStr) {
      this.addStep({
        operation: 'add_column',
        name: 'Custom Formula Expression',
        params: { expression: formulaStr }
      });
    },
    handleSelectQuery(tableName) {
      if (this.store && typeof this.store.setSelectedTable === 'function') {
        this.store.setSelectedTable(tableName);
      }
    },
    handleQueryAction({ action, table }) {
      if (action === 'duplicate' && this.store) {
        const steps = this.store.getStepsForTable(table);
        const newName = `${table}_copy`;
        this.store.setStepsForTable(newName, [...steps]);
        this.store.setSelectedTable(newName);
      }
    },
    handleColumnAction({ action, column }) {
      if (action === 'remove') {
        this.addStep({ operation: 'remove_column', name: `Remove Column (${column})`, params: { column } });
      } else if (action === 'rename') {
        this.addStep({ operation: 'rename_column', name: `Rename Column (${column})`, params: { mapping: { [column]: `${column}_renamed` } } });
      } else if (action === 'cast') {
        this.addStep({ operation: 'cast_column', name: `Change Type (${column})`, params: { casts: { [column]: 'text' } } });
      }
    },
    handleAddCustomColumn({ new_column, expression }) {
      this.addStep({
        operation: 'add_column',
        name: `Added Custom (${new_column})`,
        params: { new_column, expression, mode: 'expression' }
      });
    },
    handleEditStepSettings({ step, index }) {
      console.log('Edit step settings:', step, index);
    },
    handleQueryRenamed(newName) {
      if (this.store && this.selectedTable) {
        const currentSteps = this.store.getStepsForTable(this.selectedTable);
        this.store.setStepsForTable(newName, currentSteps);
        this.store.setSelectedTable(newName);
      }
    },
    addStep(step) {
      if (this.store && typeof this.store.addStep === 'function') {
        this.store.addStep(step);
      }
    }
  }
};
</script>
