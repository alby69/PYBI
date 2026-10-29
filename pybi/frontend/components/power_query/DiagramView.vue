<template>
  <div class="diagram-view flex flex-col w-full h-full bg-slate-50 overflow-hidden">
    <div class="flex items-center justify-between px-3 py-1.5 bg-slate-100 border-b border-slate-300 text-xs">
      <div class="flex items-center gap-2 font-bold text-slate-700">
        <span>🗺️</span>
        <span>Query Diagram</span>
        <span class="font-mono text-[10px] text-slate-500">({{ nodes.length }} nodes)</span>
      </div>
      <div class="flex items-center gap-1">
        <button @click="zoomOut" class="px-2 py-0.5 rounded border border-slate-300 bg-white hover:bg-slate-50 font-bold" title="Zoom out">−</button>
        <span class="w-12 text-center font-mono text-[10px] text-slate-600">{{ Math.round(zoom * 100) }}%</span>
        <button @click="zoomIn" class="px-2 py-0.5 rounded border border-slate-300 bg-white hover:bg-slate-50 font-bold" title="Zoom in">＋</button>
        <button @click="zoom = 1" class="px-2 py-0.5 rounded border border-slate-300 bg-white hover:bg-slate-50 text-[10px] font-semibold">Reset</button>
      </div>
    </div>

    <div v-if="!nodes.length" class="flex-grow flex items-center justify-center text-slate-400 italic text-xs">
      Select a query with at least one step to display the diagram.
    </div>

    <div v-else class="flex-grow overflow-auto p-6">
      <div class="inline-flex items-center gap-0 min-w-max" :style="{ transform: `scale(${zoom})`, transformOrigin: 'top left' }">
        <template v-for="(node, idx) in nodes" :key="node.id || idx">
          <div
            @click="selectNode(node)"
            :class="[
              'relative w-44 rounded-lg border-2 shadow-sm cursor-pointer transition-all select-none',
              node.index === activeStepIndex
                ? 'border-blue-500 bg-blue-50 shadow-blue-200 shadow-md ring-2 ring-blue-200'
                : 'border-slate-300 bg-white hover:border-blue-300 hover:shadow'
            ]"
            :title="node.title"
          >
            <div :class="['flex items-center gap-1.5 px-2 py-1 rounded-t-md text-[10px] font-bold uppercase tracking-wide', node.index === 0 ? 'bg-slate-200 text-slate-700' : 'bg-blue-600 text-white']">
              <span>{{ node.icon }}</span>
              <span class="truncate">{{ node.kind }}</span>
              <span class="ml-auto font-mono opacity-70">{{ node.index }}</span>
            </div>
            <div class="px-2 py-2">
              <div class="font-bold text-xs text-slate-800 truncate" :title="node.name">{{ node.name }}</div>
              <div class="mt-1 font-mono text-[10px] text-slate-500 truncate" :title="node.detail">{{ node.detail }}</div>
            </div>
            <div v-if="node.index === activeStepIndex" class="absolute -top-2 -right-2 bg-blue-600 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow">PREVIEW</div>
          </div>

          <div v-if="idx < nodes.length - 1" class="flex items-center text-slate-400 px-1">
            <div class="w-8 border-t-2 border-dashed border-slate-300"></div>
            <span class="text-sm -ml-1">▶</span>
          </div>
        </template>
      </div>
    </div>

    <div class="px-3 py-1 bg-white border-t border-slate-200 text-[10px] text-slate-500">
      Click a node to time-travel the preview to that step.
    </div>
  </div>
</template>

<script>
import { useUiStore } from 'pybi-store';

export default {
  name: 'DiagramView',
  emits: ['select-step'],
  data() {
    return { zoom: 1 };
  },
  computed: {
    store() {
      return useUiStore();
    },
    activeStepIndex() {
      return this.store.activeStepIndex;
    },
    nodes() {
      const table = this.store.selectedTable;
      if (!table) return [];
      const steps = this.store.getStepsForTable(table);
      const nodes = [{
        index: 0,
        kind: 'Source',
        icon: '📁',
        name: table,
        detail: /\.[A-Za-z0-9]+$/.test(table) ? 'File data source' : 'Table data source',
        title: `Preview source: ${table}`,
        stepIndex: 0
      }];
      steps.forEach((step, idx) => {
        nodes.push({
          id: step.id,
          index: idx + 1,
          kind: step.operation || 'Step',
          icon: this.stepIcon(step.operation || step.name),
          name: step.name || this.stepName(step),
          detail: JSON.stringify(step.params || {}),
          title: `${step.name || this.stepName(step)}\n${JSON.stringify(step.params || {}, null, 2)}`,
          stepIndex: idx + 1
        });
      });
      return nodes;
    }
  },
  methods: {
    selectNode(node) {
      this.store.setActiveStepIndex(node.stepIndex);
      this.$emit('select-step', node.stepIndex);
    },
    zoomIn() { this.zoom = Math.min(2, Math.round((this.zoom + 0.1) * 10) / 10); },
    zoomOut() { this.zoom = Math.max(0.4, Math.round((this.zoom - 0.1) * 10) / 10); },
    stepIcon(opStr) {
      const op = (opStr || '').toLowerCase();
      if (op.includes('filter')) return '🔍';
      if (op.includes('rename')) return '✏️';
      if (op.includes('cast') || op.includes('type')) return '🔄';
      if (op.includes('add') || op.includes('conditional')) return '✨';
      if (op.includes('remove') || op.includes('drop')) return '❌';
      if (op.includes('split')) return '✂️';
      if (op.includes('replace')) return '🔁';
      if (op.includes('sort')) return '📶';
      if (op.includes('group')) return '📊';
      if (op.includes('merge') || op.includes('join')) return '🔗';
      return '⚡';
    },
    stepName(step) {
      if (step.operation === 'filter') return `Filtered Rows (${step.params?.condition || ''})`;
      if (step.operation === 'rename_column') return 'Renamed Column';
      if (step.operation === 'cast_column') return 'Changed Type';
      if (step.operation === 'add_column') return `Added Custom Column (${step.params?.new_column || ''})`;
      return step.operation || 'Transformation Step';
    }
  }
};
</script>
