import { reactive } from 'vue';

export const state = reactive({
    currentSchema: null,
    activePage: '',
    loading: false,
    error: null,
    pageState: {},
    currentSourceTable: null,
    appliedStepsByTable: {},
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
        state.currentSourceTable = tableName;
        if (tableName && !state.appliedStepsByTable[tableName]) {
            state.appliedStepsByTable[tableName] = [];
        }
    }

    function getStepsForTable(tableName) {
        const target = tableName || state.currentSourceTable;
        if (!target) return [];
        return state.appliedStepsByTable[target] || [];
    }

    function setStepsForTable(tableName, steps) {
        if (!tableName) return;
        state.appliedStepsByTable[tableName] = steps || [];
    }

    function addStepForTable(tableName, step) {
        const target = tableName || state.currentSourceTable;
        if (!target) return;
        if (!state.appliedStepsByTable[target]) {
            state.appliedStepsByTable[target] = [];
        }
        state.appliedStepsByTable[target].push(step);
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
        setDrillContext,
        popDrillContext,
        clearDrillContext
    };
};
