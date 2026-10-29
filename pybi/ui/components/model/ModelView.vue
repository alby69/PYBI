<template>
  <div class="model-view w-full h-screen flex flex-col bg-slate-100 overflow-hidden text-slate-800">
    <!-- Upper Ribbon Toolbar -->
    <ModelToolbar
      @open-manage-relationships="isManageRelModalOpen = true"
      @open-measure-editor="openMeasureEditor(null)"
      @fit-view="onFitView"
    />

    <!-- Main Workspace Layout -->
    <div class="flex-1 flex overflow-hidden relative">
      <!-- Left Panel: Field List -->
      <FieldListPane />

      <!-- Center Canvas: Vue Flow Entity-Relationship Diagram -->
      <div class="flex-1 relative h-full">
        <RelationshipCanvas ref="canvasRef" />
      </div>

      <!-- Right Drawer: Properties Panel -->
      <PropertiesPanel />
    </div>

    <!-- Modals -->
    <ManageRelationshipsModal
      :is-open="isManageRelModalOpen"
      @close="isManageRelModalOpen = false"
    />

    <MeasureEditorModal
      :is-open="isMeasureEditorOpen"
      :measure="editingMeasure"
      @close="isMeasureEditorOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import ModelToolbar from './ModelToolbar.vue';
import FieldListPane from './FieldListPane.vue';
import RelationshipCanvas from './RelationshipCanvas.vue';
import PropertiesPanel from './PropertiesPanel.vue';
import ManageRelationshipsModal from './modals/ManageRelationshipsModal.vue';
import MeasureEditorModal from './modals/MeasureEditorModal.vue';
import { useModelStore } from '../../stores/modelStore.js';

const props = defineProps({
  projectId: {
    type: String,
    default: 'default',
  },
});

const modelStore = useModelStore();
const canvasRef = ref(null);

const isManageRelModalOpen = ref(false);
const isMeasureEditorOpen = ref(false);
const editingMeasure = ref(null);

onMounted(async () => {
  await modelStore.fetchSemanticModel(props.projectId);
});

function openMeasureEditor(measure) {
  editingMeasure.value = measure;
  isMeasureEditorOpen.value = true;
}

function onFitView() {
  if (canvasRef.value?.fitView) {
    canvasRef.value.fitView();
  }
}
</script>
