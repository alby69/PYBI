<template>
  <div
    class="table-node border rounded-lg bg-white shadow-md overflow-hidden min-w-[220px]"
    :class="{ 'ring-2 ring-blue-500': isSelected }"
    @click.stop="onSelectTable"
  >
    <!-- Header -->
    <div
      class="header px-3 py-2 text-white font-bold text-xs flex items-center justify-between"
      :class="headerClass"
    >
      <div class="flex items-center gap-1.5 truncate">
        <span class="text-sm">📊</span>
        <span class="truncate">{{ data.label || data.name }}</span>
      </div>
      <span class="text-[10px] opacity-80 uppercase px-1 py-0.5 bg-black/20 rounded">
        {{ isFactTable ? 'Fact' : 'Dim' }}
      </span>
    </div>

    <!-- Columns and Measures List -->
    <div class="p-1 text-xs divide-y divide-gray-100 max-h-[300px] overflow-y-auto">
      <!-- Columns -->
      <div
        v-for="col in data.columns || []"
        :key="col.name"
        class="column-row px-2 py-1 flex items-center justify-between hover:bg-slate-50 rounded cursor-pointer relative group"
        :class="{ 'opacity-50': col.is_hidden }"
        @click.stop="onSelectColumn(col)"
      >
        <!-- Left Handle (Target) -->
        <Handle
          :id="`left-${col.name}`"
          type="target"
          :position="Position.Left"
          class="!w-2 !h-2 !bg-blue-600 !border-white"
        />

        <div class="flex items-center gap-1.5 truncate">
          <span class="text-[10px] font-mono text-gray-500 min-w-[20px]">
            {{ getTypeIcon(col.data_type) }}
          </span>
          <span v-if="col.is_key" title="Primary / Foreign Key" class="text-xs">🔑</span>
          <span class="truncate text-slate-700" :class="{ 'font-semibold': col.is_key }">
            {{ col.name }}
          </span>
        </div>

        <span v-if="col.is_hidden" class="text-[10px] text-gray-400">🙈</span>

        <!-- Right Handle (Source) -->
        <Handle
          :id="`right-${col.name}`"
          type="source"
          :position="Position.Right"
          class="!w-2 !h-2 !bg-blue-600 !border-white"
        />
      </div>

      <!-- Measures -->
      <div
        v-for="meas in data.measures || []"
        :key="meas.id || meas.name"
        class="measure-row px-2 py-1 flex items-center justify-between bg-amber-50/50 hover:bg-amber-100/50 rounded cursor-pointer"
        @click.stop="onSelectMeasure(meas)"
      >
        <div class="flex items-center gap-1.5 truncate text-amber-900 font-medium">
          <span class="text-xs font-bold">∑</span>
          <span class="truncate">{{ meas.name }}</span>
        </div>
        <span class="text-[9px] text-amber-700 font-mono">{{ meas.format_string || 'fx' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { Handle, Position } from '@vueflow/core';
import { useModelStore } from '../../../stores/modelStore.js';

const props = defineProps({
  id: String,
  data: Object,
  selected: Boolean,
});

const modelStore = useModelStore();

const isSelected = computed(() => {
  return modelStore.selectedItem?.type === 'table' && modelStore.selectedItem?.data?.name === props.data.name;
});

const isFactTable = computed(() => {
  const name = (props.data.label || props.data.name || '').toLowerCase();
  return name.includes('fact') || name.includes('sales') || name.includes('orders') || name.includes('transactions');
});

const headerClass = computed(() => {
  return isFactTable.value ? 'bg-indigo-600' : 'bg-emerald-600';
});

function getTypeIcon(dataType) {
  const t = (dataType || '').toLowerCase();
  if (t.includes('int') || t.includes('number') || t.includes('float') || t.includes('double') || t.includes('decimal')) {
    return '123';
  }
  if (t.includes('date') || t.includes('time')) {
    return '📅';
  }
  if (t.includes('bool')) {
    return 'T/F';
  }
  return 'ABC';
}

function onSelectTable() {
  modelStore.selectEntity('table', props.data);
}

function onSelectColumn(col) {
  modelStore.selectEntity('column', { ...col, table_name: props.data.name });
}

function onSelectMeasure(meas) {
  modelStore.selectEntity('measure', meas);
}
</script>

<style scoped>
.table-node {
  user-select: none;
}
</style>
