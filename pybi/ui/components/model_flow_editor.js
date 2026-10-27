import { VueFlow, Handle, Panel, useVueFlow } from 'https://cdn.jsdelivr.net/npm/@vue-flow/core@1.42.0/dist/vue-flow-core.mjs';

export default {
    template: `
        <div style="width: 100%; height: 100%; min-height: 600px; position: relative;" class="model-flow-editor-container border rounded-lg bg-slate-50 overflow-hidden">
            <VueFlow
                v-model:nodes="localNodes"
                v-model:edges="localEdges"
                :fit-view-on-init="true"
                class="vue-flow-theme-default"
                style="height: 100%; width: 100%;"
                @pane-ready="onPaneReady"
                @node-drag-stop="onNodeDragStop"
                @node-click="onNodeClick"
                @edge-click="onEdgeClick"
                @connect="onConnect"
                @nodes-change="emitChange"
                @edges-change="emitChange"
            >
                <Panel position="top-right" class="flex gap-2 bg-white/90 p-1.5 rounded-lg border border-slate-200 shadow-sm backdrop-blur-sm">
                    <button
                        type="button"
                        @click="fitView"
                        class="px-2.5 py-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded transition-colors flex items-center gap-1 border border-slate-300"
                        title="Adatta alla finestra (Fit View)"
                    >
                        <span>🔍</span>
                        <span>Adatta alla finestra</span>
                    </button>
                </Panel>

                <template #node-table_card="props">
                    <div
                        class="table-card bg-white border-2 rounded-lg shadow-md min-w-[220px] max-w-[280px] overflow-hidden transition-all duration-150"
                        :class="props.selected ? 'border-blue-600 ring-2 ring-blue-200' : 'border-slate-300 hover:border-slate-400'"
                    >
                        <!-- Table Header -->
                        <div class="bg-slate-800 text-white px-3 py-2 flex items-center justify-between cursor-move">
                            <div class="flex items-center gap-1.5 font-semibold text-sm truncate">
                                <span>📊</span>
                                <span class="truncate">{{ props.data.label || props.id }}</span>
                            </div>
                            <span class="text-[10px] text-slate-300 font-mono bg-slate-700 px-1.5 py-0.5 rounded">
                                {{ props.data.source_table || props.id }}
                            </span>
                        </div>

                        <!-- Table Columns -->
                        <div class="p-1.5 bg-slate-50 flex flex-col gap-1 max-h-[300px] overflow-y-auto">
                            <div
                                v-for="col in (props.data.columns || [])"
                                :key="col.name"
                                class="column-row relative flex items-center justify-between px-2 py-1 text-xs bg-white border border-slate-200 rounded hover:bg-blue-50 transition-colors"
                            >
                                <!-- Target Handle (Left) -->
                                <Handle
                                    type="target"
                                    :id="col.name"
                                    position="left"
                                    style="width: 10px; height: 10px; background: #2563eb; border: 2px solid white; left: -6px;"
                                />

                                <div class="flex items-center gap-1 font-mono text-slate-800 truncate">
                                    <span v-if="col.is_key" title="Primary Key" class="text-amber-500 text-xs">🔑</span>
                                    <span class="truncate font-medium">{{ col.name }}</span>
                                </div>
                                <span class="text-[10px] text-slate-400 font-mono ml-2">{{ col.data_type }}</span>

                                <!-- Source Handle (Right) -->
                                <Handle
                                    type="source"
                                    :id="col.name"
                                    position="right"
                                    style="width: 10px; height: 10px; background: #2563eb; border: 2px solid white; right: -6px;"
                                />
                            </div>

                            <!-- Measures Section if any -->
                            <div v-if="props.data.measures && props.data.measures.length > 0" class="mt-1 pt-1 border-t border-slate-200">
                                <div class="text-[10px] font-semibold text-slate-500 uppercase px-1 mb-0.5">Calculated Measures</div>
                                <div
                                    v-for="m in props.data.measures"
                                    :key="m.name"
                                    class="px-2 py-0.5 text-[11px] font-mono text-blue-700 bg-blue-50/60 rounded flex items-center justify-between"
                                >
                                    <span class="truncate">📐 {{ m.name }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </template>
            </VueFlow>
        </div>
    `,
    components: {
        VueFlow,
        Handle,
        Panel
    },
    setup() {
        const { fitView } = useVueFlow();
        return { fitView };
    },
    props: {
        nodes: {
            type: Array,
            default: () => []
        },
        edges: {
            type: Array,
            default: () => []
        }
    },
    data() {
        return {
            localNodes: [],
            localEdges: []
        };
    },
    watch: {
        nodes: {
            handler(newVal) {
                this.localNodes = JSON.parse(JSON.stringify(newVal || []));
            },
            deep: true,
            immediate: true
        },
        edges: {
            handler(newVal) {
                this.localEdges = JSON.parse(JSON.stringify(newVal || []));
            },
            deep: true,
            immediate: true
        }
    },
    methods: {
        emitChange() {
            this.$emit('change', {
                nodes: this.localNodes,
                edges: this.localEdges
            });
        },
        onPaneReady() {
            setTimeout(() => {
                if (this.fitView) {
                    this.fitView({ padding: 0.2 });
                }
            }, 100);
        },
        onNodeClick(payload) {
            const node = payload && payload.node ? payload.node : null;
            if (!node) return;
            this.$emit('node_click', {
                node: node,
                nodes: this.localNodes
            });
        },
        onEdgeClick(payload) {
            const edge = payload && payload.edge ? payload.edge : null;
            if (!edge) return;
            this.$emit('edge_click', {
                edge: edge,
                edges: this.localEdges
            });
        },
        onNodeDragStop(event) {
            this.$emit('node_drag_stop', {
                node: event.node,
                nodes: this.localNodes
            });
            this.emitChange();
        },
        onConnect(connection) {
            const newEdge = {
                id: `rel_${connection.source}_${connection.sourceHandle}_${connection.target}_${connection.targetHandle}`,
                source: connection.source,
                sourceHandle: connection.sourceHandle,
                target: connection.target,
                targetHandle: connection.targetHandle,
                label: '*:1',
                data: {
                    from_table: connection.source,
                    from_column: connection.sourceHandle,
                    to_table: connection.target,
                    to_column: connection.targetHandle,
                    cardinality: '*:1',
                    join_type: 'LEFT',
                    is_active: true
                },
                style: {
                    stroke: '#2563eb',
                    strokeWidth: 2,
                    strokeDasharray: 'none'
                }
            };
            this.localEdges.push(newEdge);
            this.$emit('connect', {
                connection: connection,
                edge: newEdge,
                edges: this.localEdges
            });
            this.emitChange();
        }
    }
};
