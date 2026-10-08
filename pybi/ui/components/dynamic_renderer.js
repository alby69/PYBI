import { reactive } from 'vue';

const uiStoreState = reactive({
    currentSchema: null,
    activePage: '',
    loading: false,
    error: null,
    pageState: {}
});

const useUIStore = () => {
    async function loadSchema(pageName) {
        uiStoreState.loading = true;
        uiStoreState.error = null;
        uiStoreState.activePage = pageName;
        try {
            const res = await fetch(`/api/ui/schema/${pageName}`);
            if (!res.ok) {
                throw new Error(`Failed to load schema for page ${pageName}: ${res.statusText}`);
            }
            const data = await res.json();
            uiStoreState.currentSchema = data;
            uiStoreState.loading = false;
            return data;
        } catch (err) {
            uiStoreState.error = err.message || String(err);
            uiStoreState.loading = false;
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
        state: uiStoreState,
        loadSchema,
        triggerAction
    };
};

export default {
    name: 'DynamicRenderer',
    template: `
        <div class="dynamic-renderer-root w-full">
            <div v-if="uiStore.state.loading" class="p-4 text-center text-gray-500 flex items-center justify-center gap-2">
                <span class="animate-spin">⌛</span> Loading UI Schema...
            </div>
            <div v-else-if="uiStore.state.error" class="p-4 bg-red-50 text-red-700 border border-red-200 rounded text-sm">
                ⚠️ Error loading UI schema: {{ uiStore.state.error }}
            </div>
            <template v-else-if="computedComponents && computedComponents.length">
                <template v-for="(item, idx) in computedComponents" :key="item.id || item.key || idx">
                    <component
                        :is="mapTypeToComponent(item.type)"
                        v-bind="item.props || {}"
                        @click="handleAction(item.action, item)"
                    >
                        <template v-if="item.text">{{ item.text }}</template>
                        <dynamic-renderer
                            v-if="item.children && item.children.length"
                            :schema="{ components: item.children }"
                        />
                    </component>
                </template>
            </template>
            <div v-else class="p-2 text-gray-400 text-xs italic">
                (No component schema defined)
            </div>
        </div>
    `,
    props: {
        schema: {
            type: [Object, Array],
            default: () => null
        },
        pageName: {
            type: String,
            default: ''
        }
    },
    setup() {
        const uiStore = useUIStore();
        return { uiStore };
    },
    computed: {
        computedComponents() {
            if (this.schema) {
                if (Array.isArray(this.schema)) return this.schema;
                if (this.schema.components) return this.schema.components;
            }
            if (this.uiStore.state.currentSchema && this.uiStore.state.currentSchema.components) {
                return this.uiStore.state.currentSchema.components;
            }
            return [];
        }
    },
    watch: {
        pageName: {
            handler(val) {
                if (val) {
                    this.uiStore.loadSchema(val);
                }
            },
            immediate: true
        }
    },
    methods: {
        mapTypeToComponent(type) {
            if (!type) return 'div';
            if (type.startsWith('custom:')) {
                return type.replace('custom:', '');
            }
            return type;
        },
        async handleAction(action, item) {
            if (action) {
                await this.uiStore.triggerAction(action, { item });
            }
            this.$emit('action', { action, item });
        }
    }
};
