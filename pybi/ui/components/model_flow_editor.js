import { VueFlow, Handle, Panel, useVueFlow } from 'https://cdn.jsdelivr.net/npm/@vue-flow/core@1.42.0/dist/vue-flow-core.mjs';

export default {
    template: `
        <div style="width: 100%; height: 100%; min-height: 600px; position: relative; background-color: #f8fafc; background-image: radial-gradient(#cbd5e1 1px, transparent 1px); background-size: 20px 20px;" class="model-flow-editor-container border border-slate-300 rounded-lg overflow-hidden">
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
                @pane-click="onPaneClick"
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
                        class="table-card relative flex flex-col bg-white border rounded-lg shadow-lg min-w-[220px] min-h-[160px] overflow-visible transition-all duration-150"
                        style="width: 100%; height: 100%; box-sizing: border-box;"
                        :class="props.selected ? 'border-teal-700 ring-2 ring-teal-200' : 'border-slate-300 hover:border-teal-500'"
                    >
                        <Handle
                            type="target"
                            id="__table_target__"
                            position="left"
                            style="width: 12px; height: 12px; background: #64748b; border: 2px solid white; left: -6px; top: 50%;"
                        />
                        <Handle
                            type="source"
                            id="__table_source__"
                            position="right"
                            style="width: 12px; height: 12px; background: #0f766e; border: 2px solid white; right: -6px; top: 50%;"
                        />
                        <!-- Table Header -->
                        <div
                            class="text-white px-3 py-2 rounded-t-md flex items-center justify-between cursor-move"
                            :class="props.data.is_fact ? 'bg-teal-800' : 'bg-slate-700'"
                        >
                            <div class="flex items-center gap-1.5 font-semibold text-sm truncate">
                                <span>{{ props.data.is_fact ? '▦' : '▤' }}</span>
                                <span class="truncate">{{ props.data.label || props.id }}</span>
                            </div>
                            <span class="text-[10px] text-white/80 font-mono bg-black/20 px-1.5 py-0.5 rounded">{{ props.data.is_fact ? 'FACT' : 'DIM' }}</span>
                        </div>
                        <div class="px-3 py-1 border-b border-slate-100 bg-slate-50 text-[10px] text-slate-500 font-mono truncate">
                            Source: {{ props.data.source_table || props.id }}
                        </div>

                        <!-- Table Columns -->
                        <div class="table-columns min-h-0 flex-1 p-1.5 bg-white flex flex-col gap-1 overflow-y-auto rounded-b-md">
                            <div
                                v-for="col in (props.data.columns || [])"
                                :key="col.name"
                                class="column-row relative flex items-center justify-between px-2 py-1.5 text-xs bg-white border border-slate-200 rounded hover:bg-teal-50 hover:border-teal-200 transition-colors"
                            >
                                <!-- Target Handle (Left) -->
                                <Handle
                                    type="target"
                                    :id="'target:' + col.name"
                                    position="left"
                                    style="width: 10px; height: 10px; background: #64748b; border: 2px solid white; left: -6px;"
                                />

                                <div class="flex items-center gap-1 font-mono text-slate-800 truncate">
                                    <span v-if="col.is_key" title="Primary Key" class="text-amber-500 text-xs">🔑</span>
                                    <span class="truncate font-medium">{{ col.name }}</span>
                                </div>
                                <span class="text-[10px] text-slate-400 font-mono ml-2">{{ col.data_type }}</span>

                                <!-- Source Handle (Right) -->
                                <Handle
                                    type="source"
                                    :id="'source:' + col.name"
                                    position="right"
                                    style="width: 10px; height: 10px; background: #0f766e; border: 2px solid white; right: -6px;"
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
                        <button
                            v-if="props.selected"
                            type="button"
                            class="table-resize-handle nodrag nopan"
                            style="position: absolute; right: 2px; bottom: 2px; width: 18px; height: 18px; padding: 0; border: 0; border-radius: 0 0 6px 0; background: transparent; cursor: nwse-resize; z-index: 20;"
                            title="Ridimensiona tabella"
                            aria-label="Ridimensiona tabella"
                            @pointerdown.stop.prevent="startResize($event, props.id)"
                        >
                            <span style="position: absolute; right: 3px; bottom: 3px; width: 8px; height: 8px; border-right: 2px solid #0f766e; border-bottom: 2px solid #0f766e;"></span>
                        </button>
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
            localEdges: [],
            resizeSession: null
        };
    },
    beforeUnmount() {
        this.stopResize();
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
        startResize(event, nodeId) {
            const node = this.localNodes.find(item => item.id === nodeId);
            const nodeElement = event.currentTarget.closest('.vue-flow__node');
            if (!node || !nodeElement) return;

            const viewport = nodeElement.closest('.vue-flow')?.querySelector('.vue-flow__viewport');
            const transform = viewport ? getComputedStyle(viewport).transform : 'none';
            const zoom = transform === 'none' ? 1 : new DOMMatrixReadOnly(transform).a;
            const bounds = nodeElement.getBoundingClientRect();
            this.resizeSession = {
                nodeId,
                pointerId: event.pointerId,
                startX: event.clientX,
                startY: event.clientY,
                startWidth: bounds.width / zoom,
                startHeight: bounds.height / zoom,
                zoom
            };
            window.addEventListener('pointermove', this.resizeNode);
            window.addEventListener('pointerup', this.stopResize);
            window.addEventListener('pointercancel', this.stopResize);
        },
        resizeNode(event) {
            const session = this.resizeSession;
            if (!session || event.pointerId !== session.pointerId) return;
            const node = this.localNodes.find(item => item.id === session.nodeId);
            if (!node) return;
            const width = Math.max(220, session.startWidth + (event.clientX - session.startX) / session.zoom);
            const height = Math.max(160, session.startHeight + (event.clientY - session.startY) / session.zoom);
            node.style = { ...node.style, width: `${width}px`, height: `${height}px` };
            node.width = width;
            node.height = height;
        },
        stopResize(event) {
            const session = this.resizeSession;
            if (!session || (event?.pointerId !== undefined && event.pointerId !== session.pointerId)) return;
            window.removeEventListener('pointermove', this.resizeNode);
            window.removeEventListener('pointerup', this.stopResize);
            window.removeEventListener('pointercancel', this.stopResize);
            this.resizeSession = null;
            const node = this.localNodes.find(item => item.id === session.nodeId);
            if (!node) return;
            this.$emit('node_resize_stop', {
                node: { id: node.id, width: node.width, height: node.height },
                nodes: this.localNodes
            });
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
        onPaneClick() {
            this.$emit('pane_click', {});
        },
        onNodeDragStop(event) {
            this.$emit('node_drag_stop', {
                node: event.node,
                nodes: this.localNodes
            });
            this.emitChange();
        },
        onConnect(connection) {
            const sourceColumn = connection.sourceHandle?.startsWith('source:')
                ? connection.sourceHandle.slice('source:'.length)
                : connection.sourceHandle;
            const targetColumn = connection.targetHandle?.startsWith('target:')
                ? connection.targetHandle.slice('target:'.length)
                : connection.targetHandle;
            const newEdge = {
                id: `rel_${connection.source}_${connection.sourceHandle}_${connection.target}_${connection.targetHandle}`,
                source: connection.source,
                sourceHandle: connection.sourceHandle,
                target: connection.target,
                targetHandle: connection.targetHandle,
                label: '*:1',
                data: {
                    from_table: connection.source,
                    from_column: sourceColumn,
                    to_table: connection.target,
                    to_column: targetColumn,
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
