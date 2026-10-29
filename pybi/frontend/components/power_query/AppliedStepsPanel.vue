<template>
  <div
    :class="[
      'applied-steps-panel flex flex-col bg-slate-50 border-l border-slate-300 transition-all duration-200 select-none h-full',
      isCollapsed ? 'w-10' : 'w-72'
    ]"
  >
    <!-- Header with Collapse Toggle -->
    <div class="flex items-center justify-between p-2 bg-slate-200 border-b border-slate-300">
      <button
        @click="isCollapsed = !isCollapsed"
        class="p-1 rounded hover:bg-slate-300 text-slate-600 focus:outline-none text-xs"
        :title="isCollapsed ? 'Expand Query Settings' : 'Collapse Query Settings'"
      >
        <span v-if="isCollapsed">◀</span>
        <span v-else">▶</span>
      </button>
      <div v-if="!isCollapsed" class="flex items-center gap-1.5 font-bold text-xs text-slate-800 truncate mr-auto ml-2">
        <span>⚙️</span>
        <span>Query Settings</span>
      </div>
    </div>

    <!-- Panel Body -->
    <div v-if="!isCollapsed" class="flex-grow flex flex-col p-3 overflow-y-auto gap-4">
      <!-- Section 1: PROPERTIES -->
      <div class="flex flex-col gap-1.5 bg-white p-2.5 rounded border border-slate-200 shadow-xs">
        <span class="font-bold text-xs text-slate-700 uppercase tracking-wider text-[10px]">Properties</span>
        <label class="text-[11px] font-semibold text-slate-600">Name</label>
        <input
          v-model="queryName"
          @change="updateQueryName"
          type="text"
          class="px-2 py-1 text-xs border border-slate-300 rounded bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium"
        />
      </div>

      <!-- Section 2: APPLIED STEPS -->
      <div class="flex flex-col flex-grow gap-2">
        <div class="flex items-center justify-between">
          <span class="font-bold text-xs text-slate-700 uppercase tracking-wider text-[10px]">Applied Steps</span>
          <span class="text-[10px] text-slate-400">({{ appliedSteps.length }} steps)</span>
        </div>

        <!-- Step 0: Source -->
        <div
          @click="selectStep(-1)"
          :class="[
            'group flex items-center justify-between p-2 rounded border cursor-pointer text-xs transition-all',
            activeStepIndex === -1 || activeStepIndex === 0
              ? 'bg-blue-100 border-blue-400 font-bold text-blue-900 shadow-xs'
              : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700'
          ]"
        >
          <div class="flex items-center gap-2 truncate flex-grow">
            <span class="text-base">📁</span>
            <span class="truncate">Source</span>
          </div>
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-200 text-blue-800 font-mono">0</span>
        </div>

        <!-- Steps 1..N -->
        <div
          v-for="(step, idx) in appliedSteps"
          :key="step.id || idx"
          @click="selectStep(idx)"
          :class="[
            'group flex items-center justify-between p-2 rounded border cursor-pointer text-xs transition-all',
            activeStepIndex === idx
              ? 'bg-blue-100 border-blue-400 font-bold text-blue-900 shadow-xs'
              : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700'
          ]"
        >
          <div class="flex items-center gap-2 truncate flex-grow mr-1">
            <span class="text-sm">{{ getStepIcon(step.operation || step.name) }}</span>
            <span class="truncate">{{ step.name || formatStepName(step) }}</span>
          </div>

          <!-- Step Quick Action Buttons (Settings Gear & Delete Trash) -->
          <div class="flex items-center gap-1 opacity-80 group-hover:opacity-100">
            <button
              @click.stop="openStepSettings(step, idx)"
              class="p-1 hover:bg-slate-200 rounded text-slate-600 hover:text-blue-700"
              title="Step Settings (Gear)"
            >
              ⚙️
            </button>
            <button
              @click.stop="deleteStep(idx)"
              class="p-1 hover:bg-red-100 rounded text-slate-600 hover:text-red-600"
              title="Delete Step (Trash)"
            >
              🗑️
            </button>
          </div>
        </div>

        <div v-if="appliedSteps.length === 0" class="text-xs text-slate-400 italic p-3 text-center border border-dashed border-slate-200 rounded">
          No transformation steps applied yet. Select an action from the Ribbon or Column headers.
        </div>
      </div>
    </div>

    <!-- Collapsed State -->
    <div v-else class="flex flex-col items-center py-4 gap-4 text-slate-500 text-sm">
      <span title="Applied Steps">⚙️</span>
    </div>
  </div>
</template>

<script>
import { useUiStore } from '../../stores/uiStore.js';

export default {
  name: 'AppliedStepsPanel',
  emits: ['edit-step-settings', 'step-selected', 'query-renamed'],
  data() {
    return {
      isCollapsed: false,
      localQueryName: ''
    };
  },
  computed: {
    store() {
      try { return useUiStore(); } catch (e) { return null; }
    },
    selectedTable() {
      return this.store ? this.store.selectedTable : 'sales_data.csv';
    },
    queryName: {
      get() {
        return this.localQueryName || this.selectedTable || 'Query1';
      },
      set(val) {
        this.localQueryName = val;
      }
    },
    activeStepIndex() {
      return this.store ? this.store.activeStepIndex : -1;
    },
    appliedSteps() {
      if (this.store && typeof this.store.getStepsForTable === 'function') {
        return this.store.getStepsForTable(this.selectedTable) || [];
      }
      return [];
    }
  },
  watch: {
    selectedTable: {
      handler(newTable) {
        this.localQueryName = newTable;
      },
      immediate: true
    }
  },
  methods: {
    selectStep(index) {
      if (this.store) {
        this.store.activeStepIndex = index;
        this.store.fetchPreview();
      }
      this.$emit('step-selected', index);
    },
    deleteStep(index) {
      if (this.store && typeof this.store.removeStep === 'function') {
        this.store.removeStep(index);
      }
    },
    openStepSettings(step, index) {
      this.$emit('edit-step-settings', { step, index });
    },
    updateQueryName() {
      this.$emit('query-renamed', this.queryName);
    },
    getStepIcon(opStr) {
      const op = (opStr || '').toLowerCase();
      if (op.includes('filter')) return '🔍';
      if (op.includes('rename')) return '✏️';
      if (op.includes('cast') || op.includes('type')) return '🔄';
      if (op.includes('add') || op.includes('custom') || op.includes('conditional')) return '✨';
      if (op.includes('remove') || op.includes('drop')) return '❌';
      if (op.includes('split')) return '✂️';
      if (op.includes('replace')) return '🔁';
      if (op.includes('sort')) return '📶';
      if (op.includes('group')) return '📊';
      return '⚡';
    },
    formatStepName(step) {
      if (!step) return 'Step';
      if (step.operation === 'filter') return `Filtered Rows (${step.params?.condition || ''})`;
      if (step.operation === 'rename_column') return `Renamed Column`;
      if (step.operation === 'cast_column') return `Changed Type`;
      if (step.operation === 'add_column') return `Added Custom Column (${step.params?.new_column || ''})`;
      return step.operation || 'Transformation Step';
    }
  }
};
</script>
