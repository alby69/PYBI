import { defineStore } from 'pinia';
import { reactive } from 'vue';

export const useUiStore = defineStore('ui', {
  state: () => ({
    activeProject: null,
    selectedTable: null,
    activeStepIndex: -1,
    appliedStepsByTable: {}, // Formato: { "Customers": [ step1, step2 ], "Orders": [ step1 ] }
    previewData: {
      columns: [],
      rows: [],
      total_rows: 0,
      total_columns: 0,
      execution_time: 0
    },
    isLoadingPreview: false,
    currentSchema: null,
    activePage: '',
    loading: false,
    error: null,
    pageState: {},
    currentSourceTable: null,
    drillContext: null,
    drillHistory: []
  }),
  actions: {
    setSelectedTable(tableName) {
      this.selectedTable = tableName;
      this.currentSourceTable = tableName;
      if (!this.appliedStepsByTable[tableName]) {
        this.appliedStepsByTable[tableName] = [];
      }
      this.activeStepIndex = this.appliedStepsByTable[tableName].length - 1;
      this.fetchPreview();
    },
    addStep(step) {
      if (!this.selectedTable && !this.currentSourceTable) return;
      const target = this.selectedTable || this.currentSourceTable;
      const steps = this.appliedStepsByTable[target] || [];
      steps.push(step);
      this.appliedStepsByTable[target] = steps;
      this.activeStepIndex = steps.length - 1;
      this.fetchPreview();
    },
    removeStep(index) {
      const target = this.selectedTable || this.currentSourceTable;
      if (!target || !this.appliedStepsByTable[target]) return;
      this.appliedStepsByTable[target].splice(index, 1);
      this.activeStepIndex = Math.min(this.activeStepIndex, this.appliedStepsByTable[target].length - 1);
      this.fetchPreview();
    },
    async fetchPreview() {
      const target = this.selectedTable || this.currentSourceTable;
      if (!target) return;
      this.isLoadingPreview = true;
      try {
        const payload = {
          query: {
            query_name: target,
            source: { table_name: target },
            steps: this.appliedStepsByTable[target] || []
          },
          step_index: this.activeStepIndex
        };
        const projId = this.activeProject || 'default';
        const response = await fetch(`/api/v1/projects/${projId}/etl/preview`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        this.previewData = await response.json();
      } catch (err) {
        console.error("Errore nel recupero della preview ETL:", err);
      } finally {
        this.isLoadingPreview = false;
      }
    },
    setCurrentSourceTable(tableName) {
      this.setSelectedTable(tableName);
    },
    getStepsForTable(tableName) {
      const target = tableName || this.selectedTable || this.currentSourceTable;
      if (!target) return [];
      return this.appliedStepsByTable[target] || [];
    },
    setStepsForTable(tableName, steps) {
      if (!tableName) return;
      this.appliedStepsByTable[tableName] = steps || [];
    },
    addStepForTable(tableName, step) {
      const target = tableName || this.selectedTable || this.currentSourceTable;
      if (!target) return;
      if (!this.appliedStepsByTable[target]) {
        this.appliedStepsByTable[target] = [];
      }
      this.appliedStepsByTable[target].push(step);
      this.activeStepIndex = this.appliedStepsByTable[target].length - 1;
    },
    async exportPythonScript(tableName) {
      const target = tableName || this.selectedTable || this.currentSourceTable || 'Sales_Data';
      const projId = this.activeProject || 'default';
      const payload = {
        query_id: target,
        query_name: target,
        source: { table_name: target },
        steps: this.appliedStepsByTable[target] || []
      };
      try {
        const response = await fetch(`/api/v1/projects/${projId}/etl/export/python`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`Export failed: ${response.statusText}`);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pipeline_${target}.py`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        console.error('Errore durante l\'esportazione dello script Python Polars:', err);
      }
    }
  }
});

export const state = reactive({
    currentSchema: null,
    activePage: '',
    loading: false,
    error: null,
    pageState: {},
    currentSourceTable: null,
    activeProject: null,
    selectedTable: null,
    activeStepIndex: -1,
    appliedStepsByTable: {},
    previewData: {
      columns: [],
      rows: [],
      total_rows: 0,
      total_columns: 0,
      execution_time: 0
    },
    isLoadingPreview: false,
    drillContext: null,
    drillHistory: []
});

export const useUIStore = () => {
    async function loadSchema(pageName) {
        state.loading = true;
        state.error = null;
        state.activePage = pageName;
        try {
            const res = await fetch(`/api/ui/schema/${pageName}`);
            if (!res.ok) {
                throw new Error(`Failed to load schema for page ${pageName}: ${res.statusText}`);
            }
            const data = await res.json();
            state.currentSchema = data;
            state.loading = false;
            return data;
        } catch (err) {
            state.error = err.message || String(err);
            state.loading = false;
            console.error('uiStore.loadSchema error:', err);
            return null;
        }
    }

    async function triggerAction(action, payload = {}) {
        if (!action) return;
        if (typeof action === 'string' && action.startsWith('api:')) {
            const parts = action.split(':');
            const method = parts[1] && ['GET', 'POST', 'PUT', 'DELETE'].includes(parts[1].toUpperCase()) ? parts[1].toUpperCase() : 'POST';
            const endpoint = parts.length > 2 ? parts.slice(2).join(':') : parts[1];
            try {
                const options = {
                    method,
                    headers: { 'Content-Type': 'application/json' }
                };
                if (method !== 'GET') {
                    options.body = JSON.stringify(payload);
                }
                const res = await fetch(endpoint, options);
                return await res.json();
            } catch (e) {
                console.error('Action API trigger error:', e);
            }
        }
    }

    function setCurrentSourceTable(tableName) {
        state.selectedTable = tableName;
        state.currentSourceTable = tableName;
        if (tableName && !state.appliedStepsByTable[tableName]) {
            state.appliedStepsByTable[tableName] = [];
        }
        state.activeStepIndex = (state.appliedStepsByTable[tableName] || []).length - 1;
    }

    function getStepsForTable(tableName) {
        const target = tableName || state.selectedTable || state.currentSourceTable;
        if (!target) return [];
        return state.appliedStepsByTable[target] || [];
    }

    function setStepsForTable(tableName, steps) {
        if (!tableName) return;
        state.appliedStepsByTable[tableName] = steps || [];
    }

    function addStepForTable(tableName, step) {
        const target = tableName || state.selectedTable || state.currentSourceTable;
        if (!target) return;
        if (!state.appliedStepsByTable[target]) {
            state.appliedStepsByTable[target] = [];
        }
        state.appliedStepsByTable[target].push(step);
        state.activeStepIndex = state.appliedStepsByTable[target].length - 1;
    }

    async function exportPythonScript(tableName) {
        const target = tableName || state.selectedTable || state.currentSourceTable || 'Sales_Data';
        const projId = state.activeProject || 'default';
        const payload = {
            query_id: target,
            query_name: target,
            source: { table_name: target },
            steps: state.appliedStepsByTable[target] || []
        };
        try {
            const response = await fetch(`/api/v1/projects/${projId}/etl/export/python`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error(`Export failed: ${response.statusText}`);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `pipeline_${target}.py`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Errore durante l\'esportazione dello script Python Polars:', err);
        }
    }

    function setDrillContext(targetReport, filters) {
        if (state.drillContext || state.activePage) {
            state.drillHistory.push({
                activePage: state.activePage,
                drillContext: state.drillContext ? JSON.parse(JSON.stringify(state.drillContext)) : null,
                timestamp: new Date().toISOString()
            });
        }
        state.drillContext = {
            targetReport,
            filters: JSON.parse(JSON.stringify(filters || {})),
            timestamp: new Date().toISOString()
        };
        if (targetReport && typeof targetReport === 'string') {
            state.activePage = targetReport;
        }
        return state.drillContext;
    }

    function popDrillContext() {
        if (state.drillHistory.length > 0) {
            const prev = state.drillHistory.pop();
            state.drillContext = prev.drillContext;
            if (prev.activePage) {
                state.activePage = prev.activePage;
            }
            return prev;
        } else {
            state.drillContext = null;
            return null;
        }
    }

    function clearDrillContext() {
        state.drillContext = null;
        state.drillHistory = [];
    }

    return {
        state,
        loadSchema,
        triggerAction,
        setCurrentSourceTable,
        getStepsForTable,
        setStepsForTable,
        addStepForTable,
        exportPythonScript,
        setDrillContext,
        popDrillContext,
        clearDrillContext
    };
};
