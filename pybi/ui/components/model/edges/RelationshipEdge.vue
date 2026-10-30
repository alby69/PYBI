<template>
  <g class="relationship-edge cursor-pointer" @click.stop="onSelectRelationship">
    <!-- Outer line glow on hover / select -->
    <path
      :d="edgePath"
      class="fill-none stroke-transparent hover:stroke-blue-200/50 stroke-[12]"
    />

    <!-- Main Edge Line -->
    <path
      :d="edgePath"
      class="fill-none transition-all duration-200"
      :class="[
        isSelected ? 'stroke-blue-600 stroke-[3]' : 'stroke-slate-400 stroke-[2]',
        isInactive ? 'stroke-dashed' : ''
      ]"
      :style="isInactive ? { strokeDasharray: '5,5' } : {}"
    />

    <!-- Cardinality Badge - Source (1 or *) -->
    <EdgeLabelRenderer>
      <div
        :style="{ transform: `translate(-50%, -50%) translate(${sourceX}px, ${sourceY}px)` }"
        class="nodrag nopan absolute pointer-events-auto bg-slate-800 text-white font-bold text-[10px] px-1.5 py-0.5 rounded-full shadow"
      >
        {{ sourceLabel }}
      </div>
    </EdgeLabelRenderer>

    <!-- Center Badge - Cross Filter Direction & Active State -->
    <EdgeLabelRenderer>
      <div
        :style="{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }"
        class="nodrag nopan absolute pointer-events-auto cursor-pointer"
        @click.stop="onSelectRelationship"
      >
        <div
          class="flex items-center gap-1 bg-white border px-2 py-0.5 rounded-md shadow-sm text-[11px] font-semibold"
          :class="[
            isSelected ? 'border-blue-500 text-blue-700 bg-blue-50' : 'border-slate-300 text-slate-700 hover:border-slate-400',
            isInactive ? 'opacity-60' : ''
          ]"
        >
          <span>{{ isBothDirection ? '↔️ Both' : '➔ Single' }}</span>
          <span v-if="isInactive" class="text-[9px] text-red-500 font-normal">(Inactive)</span>
        </div>
      </div>
    </EdgeLabelRenderer>

    <!-- Cardinality Badge - Target (1 or *) -->
    <EdgeLabelRenderer>
      <div
        :style="{ transform: `translate(-50%, -50%) translate(${targetX}px, ${targetY}px)` }"
        class="nodrag nopan absolute pointer-events-auto bg-slate-800 text-white font-bold text-[10px] px-1.5 py-0.5 rounded-full shadow"
      >
        {{ targetLabel }}
      </div>
    </EdgeLabelRenderer>
  </g>
</template>

<script setup>
import { computed } from 'vue';
import { getBezierPath, EdgeLabelRenderer } from '@vueflow/core';
import { useModelStore } from '../../../stores/modelStore.js';

const props = defineProps({
  id: String,
  sourceX: Number,
  sourceY: Number,
  targetX: Number,
  targetY: Number,
  sourcePosition: String,
  targetPosition: String,
  data: Object,
  selected: Boolean,
});

const modelStore = useModelStore();

const edgePathParams = computed(() => {
  return getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  });
});

const edgePath = computed(() => edgePathParams.value[0]);
const labelX = computed(() => edgePathParams.value[1]);
const labelY = computed(() => edgePathParams.value[2]);

const isSelected = computed(() => {
  return modelStore.selectedItem?.type === 'relationship' && modelStore.selectedItem?.data?.id === props.data?.id;
});

const isInactive = computed(() => props.data?.is_active === false);
const isBothDirection = computed(() => props.data?.cross_filter_direction === 'both');

const cardinalityStr = computed(() => props.data?.cardinality || '*:1');

const sourceLabel = computed(() => {
  const c = cardinalityStr.value;
  if (c.startsWith('1')) return '1';
  return '*';
});

const targetLabel = computed(() => {
  const c = cardinalityStr.value;
  if (c.endsWith('1')) return '1';
  return '*';
});

function onSelectRelationship() {
  if (props.data) {
    modelStore.selectEntity('relationship', props.data);
  }
}
</script>
