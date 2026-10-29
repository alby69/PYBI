<template>
  <div class="power-query-editor flex flex-col flex-nowrap w-full h-full min-h-[560px] bg-slate-100 font-sans text-slate-800 overflow-hidden select-none">
    <nicegui-PowerQueryRibbon @action="handleRibbonAction" />
    <nicegui-FormulaBar @apply-formula="handleFormulaApply" />

    <div class="flex flex-nowrap flex-grow w-full overflow-hidden relative min-h-0">
      <nicegui-QueriesPane
        :tables="tables"
        @select-query="handleSelectQuery"
        @action="handlePaneAction"
      />

      <div class="flex flex-col flex-grow min-w-0 min-h-0 overflow-hidden">
        <nicegui-DataGridPreview
          v-if="store.currentView === 'grid'"
          @column-action="handleColumnAction"
        />
        <nicegui-DiagramView
          v-else
          @select-step="handleStepSelected"
        />
      </div>

      <nicegui-AppliedStepsPanel
        @edit-step-settings="handleEditStepSettings"
        @step-selected="handleStepSelected"
        @query-renamed="handleQueryRenamed"
      />
    </div>

    <div class="bg-slate-800 text-slate-300 text-[11px] px-3 py-1 flex flex-nowrap items-center justify-between border-t border-slate-700 flex-shrink-0">
      <div class="flex items-center gap-4">
        <span>Active Table: <strong class="text-white">{{ store.selectedTable || 'None' }}</strong></span>
        <span>Rows: <strong class="text-white">{{ store.previewData.total_rows || 0 }}</strong></span>
        <span>Columns: <strong class="text-white">{{ store.previewData.total_columns || 0 }}</strong></span>
        <span>Steps: <strong class="text-white">{{ activeStepCount }}</strong></span>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="store.isSaving" class="text-amber-300">Saving...</span>
        <span v-if="store.isExecuting" class="text-amber-300">Executing...</span>
        <span v-if="store.previewData.execution_time" class="text-emerald-400">Preview: {{ (store.previewData.execution_time * 1000).toFixed(1) }} ms</span>
        <span class="text-slate-400">Power Query Engine (DuckDB / SQL)</span>
      </div>
    </div>

    <nicegui-FilterModal
      v-model="modals.filter"
      :columns="columns"
      :default-column="modalColumn"
      @apply="applyStep"
    />
    <nicegui-GroupByModal v-model="modals.group" :columns="columns" @apply="applyStep" />
    <nicegui-MergeJoinModal v-model="modals.merge" :columns="columns" :tables="mergeTables" @apply="applyStep" />
    <nicegui-ChooseColumnsModal v-model="modals.choose" :columns="columns" :default-mode="chooseMode" @apply="applyStep" />
    <nicegui-ReplaceValuesModal v-model="modals.replace" :columns="columns" @apply="applyStep" />
    <nicegui-SplitColumnModal v-model="modals.split" :columns="columns" @apply="applyStep" />
    <nicegui-ConditionalColumnModal v-model="modals.conditional" :columns="columns" @apply="applyStep" />
    <nicegui-CustomColumnModal v-model="modals.custom" @add-column="handleAddCustomColumn" />
    <nicegui-AdvancedEditorModal
      v-model="modals.advanced"
      :query="advancedQuery"
      @apply="handleAdvancedApply"
    />
  </div>
</template>

<script>
import { useUiStore } from 'pybi-store';

export default {
  name: 'PowerQueryEditor',
  props: {
    tablesProp: { type: Array, default: () => [] },
    selectedTable: { type: String, default: '' },
    appliedStepsByTable: { type: Object, default: () => ({}) },
    projectId: { type: String, default: 'default' }
  },
  data() {
    return {
      modals: {
        filter: false,
        group: false,
        merge: false,
        choose: false,
        replace: false,
        split: false,
        conditional: false,
        custom: false,
        advanced: false
      },
      modalColumn: '',
      chooseMode: 'keep',
      lastProvidedSteps: ''
    };
  },
  computed: {
    store() {
      return useUiStore();
    },
    tables() {
      if (this.tablesProp.length > 0) {
        return this.tablesProp.map(table => (typeof table === 'string' ? table : table.name)).filter(Boolean);
      }
      return this.store.tables || [];
    },
    mergeTables() {
      return this.tables.filter(table => table !== this.store.selectedTable);
    },
    columns() {
      const previewColumns = this.store.previewData?.columns || [];
      if (previewColumns.length) return previewColumns;
      const rows = this.store.previewData?.rows || [];
      if (rows.length) return Object.keys(rows[0]);
      return [];
    },
    activeStepCount() {
      const table = this.store.selectedTable;
      return table ? this.store.getStepsForTable(table).length : 0;
    },
    advancedQuery() {
      return this.store.currentQuery();
    }
  },
  watch: {
    projectId(value) {
      this.store.setProject(value);
    },
    tablesProp(value) {
      this.store.setTables(value);
    },
    selectedTable(value) {
      if (value && value !== this.store.selectedTable) {
        this.store.setSelectedTable(value, { force: true });
      }
    },
    appliedStepsByTable: {
      deep: true,
      handler(value) {
        const serialized = JSON.stringify(value || {});
        if (serialized === this.lastProvidedSteps) return;
        this.lastProvidedSteps = serialized;
        Object.entries(value || {}).forEach(([table, steps]) => {
          this.store.setStepsForTable(table, steps || []);
        });
      }
    }
  },
  mounted() {
    this.store.setProject(this.projectId);
    this.store.setTables(this.tablesProp);
    Object.entries(this.appliedStepsByTable || {}).forEach(([table, steps]) => {
      this.store.setStepsForTable(table, steps || []);
    });
    const initialTable = this.selectedTable || this.tables[0];
    if (initialTable) this.store.setSelectedTable(initialTable, { force: true });
  },
  methods: {
    handleRibbonAction({ action, payload }) {
      const firstColumn = this.store.profilingColumn || this.columns[0];
      if (action === 'get-data') {
        this.$emit('request-get-data');
      } else if (action === 'refresh-preview') {
        this.store.fetchPreview();
      } else if (action === 'save-query') {
        this.store.saveQuery();
      } else if (action === 'execute-query') {
        this.store.executeQuery();
      } else if (action === 'choose-columns') {
        this.chooseMode = 'keep';
        this.modals.choose = true;
      } else if (action === 'remove-columns') {
        this.chooseMode = 'remove';
        this.modals.choose = true;
      } else if (action === 'filter-rows') {
        this.modalColumn = firstColumn || '';
        this.modals.filter = true;
      } else if (action === 'sort-asc' || action === 'sort-desc') {
        if (!firstColumn) return this.notifyMissingColumn();
        this.applyStep({
          operation: 'sort',
          name: `Sorted Rows (${firstColumn} ${action === 'sort-desc' ? 'descending' : 'ascending'})`,
          params: { column: firstColumn, descending: action === 'sort-desc' }
        });
      } else if (action === 'group-by') {
        this.modals.group = true;
      } else if (action === 'merge-queries') {
        this.modals.merge = true;
      } else if (action === 'deduplicate') {
        this.applyStep({ operation: 'deduplicate', name: 'Removed Duplicate Rows', params: {} });
      } else if (action === 'export-python-script') {
        this.store.exportPythonScript();
      } else if (action === 'split-column') {
        this.modals.split = true;
      } else if (action === 'replace-values') {
        this.modals.replace = true;
      } else if (action === 'rename-column') {
        this.renameColumnPrompt(firstColumn);
      } else if (action === 'change-type') {
        this.castColumnPrompt(firstColumn);
      } else if (action === 'text-format-trim') {
        this.textTransform('trim');
      } else if (action === 'text-format-upper') {
        this.textTransform('upper');
      } else if (action === 'text-format-lower') {
        this.textTransform('lower');
      } else if (action === 'reset-steps') {
        if (window.confirm('Remove all transformation steps from the current query?')) {
          this.store.clearSteps();
        }
      } else if (action === 'add-custom-column') {
        this.modals.custom = true;
      } else if (action === 'conditional-column') {
        this.modals.conditional = true;
      } else if (action === 'index-column') {
        this.applyStep({ operation: 'index_column', name: 'Added Index Column', params: { column_name: 'index', start_value: 1, increment: 1 } });
      } else if (action === 'duplicate-column') {
        this.duplicateColumnPrompt(firstColumn);
      } else if (action === 'toggle-data-view') {
        this.store.setView('grid');
      } else if (action === 'toggle-diagram-view') {
        this.store.setView('diagram');
      } else if (action === 'toggle-profiling') {
        this.store.showProfilingBar = !this.store.showProfilingBar;
      } else if (action === 'open-advanced-editor') {
        this.modals.advanced = true;
      }
    },
    handleColumnAction({ action, column }) {
      if (action === 'sort-asc' || action === 'sort-desc') {
        this.applyStep({
          operation: 'sort',
          name: `Sorted Rows (${column} ${action === 'sort-desc' ? 'descending' : 'ascending'})`,
          params: { column, descending: action === 'sort-desc' }
        });
      } else if (action === 'filter') {
        this.modalColumn = column;
        this.modals.filter = true;
      } else if (action === 'rename') {
        this.renameColumnPrompt(column);
      } else if (action === 'cast') {
        this.castColumnPrompt(column);
      } else if (action === 'duplicate') {
        this.duplicateColumnPrompt(column);
      } else if (action === 'remove') {
        this.applyStep({ operation: 'remove_column', name: `Removed Column (${column})`, params: { column } });
      }
    },
    handleSelectQuery(tableName) {
      this.store.setStatus(`Query "${tableName}" selected.`);
    },
    handlePaneAction({ action, table }) {
      if (action === 'deleted') this.store.setStatus(`Query "${table}" deleted.`);
      if (action === 'duplicated') this.store.setStatus(`Query duplicated as "${table}".`);
      if (action === 'referenced') this.store.setStatus(`Reference query "${table}" created.`);
    },
    handleStepSelected() {},
    handleEditStepSettings({ step, index }) {
      const raw = window.prompt('Step parameters (JSON)', JSON.stringify(step.params || {}, null, 2));
      if (raw === null) return;
      try {
        const params = JSON.parse(raw);
        this.store.updateStep(index, { ...step, params });
      } catch (err) {
        window.alert(`Invalid JSON: ${err.message}`);
      }
    },
    handleQueryRenamed(newName) {
      this.store.setStatus(`Query renamed to "${newName}".`);
    },
    handleFormulaApply(expression) {
      this.applyStep({
        operation: 'add_column',
        name: 'Added Custom Column (Formula)',
        params: { new_column: 'CustomFormula', expression, mode: 'expression' }
      });
    },
    handleAddCustomColumn({ new_column, expression }) {
      this.applyStep({
        operation: 'add_column',
        name: `Added Custom Column (${new_column})`,
        params: { new_column, expression, mode: 'expression' }
      });
    },
    handleAdvancedApply(query) {
      if (Array.isArray(query.steps)) {
        this.store.setStepsForTable(this.store.selectedTable, query.steps);
        this.store.fetchPreview();
        this.store.setStatus('Advanced editor changes applied.');
      }
      if (query.query_name && query.query_name !== this.store.selectedTable) {
        this.store.renameTable(this.store.selectedTable, query.query_name);
      }
    },
    applyStep(step) {
      if (!step) return;
      this.store.addStep(step);
      this.store.setStatus(step.name || 'Transformation applied.');
    },
    notifyMissingColumn() {
      this.store.error = 'No column available for this action. Refresh the preview first.';
    },
    renameColumnPrompt(column) {
      if (!column) return this.notifyMissingColumn();
      const newName = window.prompt(`Rename column "${column}" to:`, `${column}_renamed`);
      if (!newName || newName === column) return;
      this.applyStep({
        operation: 'rename_column',
        name: `Renamed Column (${column})`,
        params: { mapping: { [column]: newName } }
      });
    },
    castColumnPrompt(column) {
      if (!column) return this.notifyMissingColumn();
      const type = window.prompt(`Change type for "${column}" to (text, int, decimal, boolean, date):`, 'text');
      if (!type) return;
      this.applyStep({
        operation: 'cast_column',
        name: `Changed Type (${column} -> ${type})`,
        params: { casts: { [column]: type } }
      });
    },
    duplicateColumnPrompt(column) {
      if (!column) return this.notifyMissingColumn();
      const newName = window.prompt(`Duplicate "${column}" as:`, `${column}_copy`);
      if (!newName) return;
      this.applyStep({
        operation: 'add_column',
        name: `Duplicated Column (${column})`,
        params: { new_column: newName, expression: `"${column}"` }
      });
    },
    textTransform(action) {
      const textColumns = this.columns.filter(column => {
        const sample = this.store.previewData.rows.find(row => row[column] !== null && row[column] !== undefined)?.[column];
        return typeof sample === 'string' || sample === undefined;
      });
      if (!textColumns.length) return this.notifyMissingColumn();
      this.applyStep({
        operation: 'text_transform',
        name: `Text ${action} (${textColumns.join(', ')})`,
        params: { columns: textColumns, action }
      });
    }
  }
};
</script>
