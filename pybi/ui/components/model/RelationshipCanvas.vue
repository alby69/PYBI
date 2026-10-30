<template>
  <div class="relationship-canvas w-full h-full relative bg-slate-50 border rounded-lg overflow-hidden">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :default-viewport="{ zoom: 1 }"
      fit-view-on-init
      class="w-full h-full"
      @connect="onConnect"
      @node-drag-stop="onNodeDragStop"
      @pane-click="onPaneClick"
    >
      <Background pattern-color="#cbd5e1" :gap="16" :size="1" />
      <Controls />
      <MiniMap />
    </VueFlow>
  </div>
</template>

<script setup>
import { ref, watch, markRaw } from 'vue';
import { VueFlow, useVueFlow } from '@vueflow/core';
import { Background } from '@vueflow/background';
import { Controls } from '@vueflow/controls';
import { MiniMap } from '@vueflow/minimap';
import '@vueflow/core/dist/style.css';
import '@vueflow/core/dist/theme-default.css';
import '@vueflow/controls/dist/style.css';
import '@vueflow/minimap/dist/style.css';

import TableNode from './nodes/TableNode.vue';
import RelationshipEdge from './edges/RelationshipEdge.vue';
import { useModelStore } from '../../stores/modelStore.js';

const modelStore = useModelStore();
const { fitView } = useVueFlow();

const nodeTypes = {
  table_card: markRaw(TableNode),
};

const edgeTypes = {
  relationship: markRaw(RelationshipEdge),
};

const nodes = ref([]);
const edges = ref([]);

watch(
  () => [modelStore.tables, modelStore.relationships],
  () => {
    syncFlowElements();
  },
  { deep: true, immediate: true }
);

function syncFlowElements() {
  nodes.value = (modelStore.tables || []).map(tbl => ({
    id: tbl.name,
    type: 'table_card',
    position: { x: tbl.position_x || 50, y: tbl.position_y || 50 },
    data: tbl,
  }));

  edges.value = (modelStore.relationships || []).map((rel, idx) => {
    const fromCol = rel.from_column;
    const toCol = rel.to_column;
    return {
      id: rel.id || `rel_${rel.from_table}_${rel.from_column}_${rel.to_table}_${rel.to_column}_${idx}`,
      type: 'relationship',
      source: rel.from_table,
      sourceHandle: `right-${fromCol}`,
      target: rel.to_table,
      targetHandle: `left-${toCol}`,
      data: rel,
    };
  });
}

function onConnect(connection) {
  const sourceTable = connection.source;
  const sourceHandle = connection.sourceHandle || '';
  const targetTable = connection.target;
  const targetHandle = connection.targetHandle || '';

  const fromCol = sourceHandle.replace('right-', '').replace('left-', '');
  const toCol = targetHandle.replace('right-', '').replace('left-', '');

  if (sourceTable && targetTable && fromCol && toCol) {
    const relId = `rel_${sourceTable}_${fromCol}_${targetTable}_${toCol}`.toLowerCase();
    modelStore.addOrUpdateRelationship({
      id: relId,
      from_table: sourceTable,
      from_column: fromCol,
      to_table: targetTable,
      to_column: toCol,
      cardinality: '*:1',
      cross_filter_direction: 'single',
      join_type: 'LEFT',
      is_active: true,
    });
  }
}

function onNodeDragStop(e) {
  const updatedPositions = {};
  nodes.value.forEach(node => {
    updatedPositions[node.id] = { x: node.position.x, y: node.position.y };
  });
  modelStore.saveModelPositions(updatedPositions);
}

function onPaneClick() {
  modelStore.selectEntity(null, null);
}

defineExpose({
  fitView,
});
</script>

<style>
.vue-flow__node-table_card {
  padding: 0;
  border-radius: 0.5rem;
  background: transparent;
}
</style>
