import { VueFlow } from 'https://cdn.jsdelivr.net/npm/@vue-flow/core@1.42.0/dist/vue-flow-core.mjs';

export default {
    template: `
        <div style="width: 100%; height: 100%; min-height: 500px; position: relative;" class="flow-editor-container border rounded bg-slate-50">
            <VueFlow
                v-model:nodes="localNodes"
                v-model:edges="localEdges"
                :fit-view-on-init="true"
                class="vue-flow-theme-default"
                style="height: 100%; width: 100%;"
                @node-drag-stop="onNodeDragStop"
                @connect="onConnect"
            >
            </VueFlow>
        </div>
    `,
    components: {
        VueFlow
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
        onNodeDragStop(event) {
            this.$emit('node_drag_stop', {
                node: event.node,
                nodes: this.localNodes
            });
            this.$emit('change', {
                nodes: this.localNodes,
                edges: this.localEdges
            });
        },
        onConnect(connection) {
            const newEdge = {
                id: `e_${connection.source}_${connection.target}_${Date.now()}`,
                source: connection.source,
                target: connection.target,
                label: connection.label || ''
            };
            this.localEdges.push(newEdge);
            this.$emit('connect', {
                connection: connection,
                edge: newEdge,
                edges: this.localEdges
            });
            this.$emit('change', {
                nodes: this.localNodes,
                edges: this.localEdges
            });
        }
    }
};
