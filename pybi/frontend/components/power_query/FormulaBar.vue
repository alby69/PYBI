<template>
  <div class="formula-bar flex items-center gap-2 p-1.5 bg-slate-100 border-b border-slate-300 text-xs select-none">
    <div class="flex items-center gap-1 font-mono font-bold text-blue-700 px-2 py-0.5 bg-blue-50 border border-blue-200 rounded">
      <span>fx</span>
    </div>
    <div class="flex-grow">
      <input
        v-model="formulaText"
        @keyup.enter="applyFormula"
        type="text"
        placeholder="Select a step or enter expression..."
        class="w-full px-2 py-1 text-xs font-mono bg-white border border-slate-300 rounded text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </div>
    <button
      @click="applyFormula"
      class="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded text-xs transition-colors flex items-center gap-1"
      title="Execute Formula"
    >
      <span>✓</span>
      <span>Apply</span>
    </button>
  </div>
</template>

<script>
import { useUiStore } from '../../stores/uiStore.js';

export default {
  name: 'FormulaBar',
  emits: ['apply-formula'],
  data() {
    return {
      localFormula: ''
    };
  },
  computed: {
    store() {
      try { return useUiStore(); } catch (e) { return null; }
    },
    activeStepIndex() {
      return this.store ? this.store.activeStepIndex : -1;
    },
    selectedTable() {
      return this.store ? this.store.selectedTable : null;
    },
    formulaText: {
      get() {
        if (this.localFormula) return this.localFormula;
        if (!this.store || !this.selectedTable) return '';
        const steps = this.store.getStepsForTable(this.selectedTable);
        if (this.activeStepIndex >= 0 && steps[this.activeStepIndex]) {
          const s = steps[this.activeStepIndex];
          if (s.params?.expression) return s.params.expression;
          if (s.params?.condition) return s.params.condition;
          return JSON.stringify(s.params || {});
        }
        return `Table.SelectRows("${this.selectedTable}")`;
      },
      set(val) {
        this.localFormula = val;
      }
    }
  },
  methods: {
    applyFormula() {
      this.$emit('apply-formula', this.formulaText);
    }
  }
};
</script>
