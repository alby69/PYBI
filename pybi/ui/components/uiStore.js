import { reactive } from 'vue';

export const state = reactive({
    currentSchema: null,
    activePage: '',
    loading: false,
    error: null,
    pageState: {}
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

    return {
        state,
        loadSchema,
        triggerAction
    };
};
