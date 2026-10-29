<template>
  <div class="formula-bar flex flex-nowrap items-center gap-2 p-1.5 bg-slate-100 border-b border-slate-300 text-xs select-none">
    <div class="flex items-center gap-1 font-mono font-bold text-blue-700 px-2 py-0.5 bg-blue-50 border border-blue-200 rounded">
      <span>fx</span>
    </div>
    <div class="flex-grow">
      <input
        v-model="formulaText"
        @keyup.enter="applyFormula"
        type="text"
        :placeholder="placeholder"
        class="w-full px-2 py-1 text-xs font-mono bg-white border border-slate-300 rounded text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </div>
    <button
      @click="applyFormula"
      class="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded text-xs transition-colors flex items-center gap-1"
      title="Apply expression as a new custom column"
    >
      <span>✓</span>
      <span>Apply</span>
    </button>
  </div>
</template>

<script>
import { useUiStore } from 'pybi-store';

export default {
  name: 'FormulaBar',
  emits: ['apply-formula'],
  data() {
    return { localFormula: '' };
  },
  computed: {
    store() {
      return useUiStore();
    },
    activeStepIndex() {
      return this.store.activeStepIndex;
    },
    selectedTable() {
      return this.store.selectedTable;
    },
    activeStep() {
      if (!this.selectedTable || this.activeStepIndex <= 0) return null;
      const steps = this.store.getStepsForTable(this.selectedTable);
      return steps[this.activeStepIndex - 1] || null;
    },
    formulaText: {
      get() {
        if (this.localFormula) return this.localFormula;
        const step = this.activeStep;
        if (!step) return this.selectedTable ? `Table("${this.selectedTable}")` : '';
        if (step.params?.expression) return step.params.expression;
        if (step.params?.condition) return step.params.condition;
        return JSON.stringify(step.params || {});
      },
      set(value) {
        this.localFormula = value;
      }
    },
    placeholder() {
      return this.selectedTable ? 'Enter an expression or inspect the selected step...' : 'Select a query...';
    }
  },
  watch: {
    activeStepIndex() {
      this.localFormula = '';
    },
    selectedTable() {
      this.localFormula = '';
    }
  },
  methods: {
    applyFormula() {
      const expression = (this.formulaText || '').trim();
      if (!expression) return;
      this.$emit('apply-formula', expression);
      this.localFormula = '';
    }
  }
};
</script>
