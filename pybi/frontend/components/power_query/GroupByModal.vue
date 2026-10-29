<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-lg overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800"><span>📊</span><span>Group By</span></div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 font-bold text-lg">×</button>
      </div>
      <div class="p-4 flex flex-col gap-3 text-xs">
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Group by column</span>
          <select v-model="groupColumn" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
            <option v-for="col in columns" :key="col" :value="col">{{ col }}</option>
          </select>
        </label>
        <div class="grid grid-cols-2 gap-2">
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Aggregate column</span>
            <select v-model="aggregateColumn" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
              <option value="">(none)</option>
              <option v-for="col in columns" :key="col" :value="col">{{ col }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Function</span>
            <select v-model="aggregateFunction" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
              <option value="SUM">Sum</option>
              <option value="COUNT">Count</option>
              <option value="AVG">Average</option>
              <option value="MIN">Min</option>
              <option value="MAX">Max</option>
            </select>
          </label>
        </div>
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Output column name</span>
          <input v-model="alias" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" />
        </label>
      </div>
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">Cancel</button>
        <button @click="submit" :disabled="!groupColumn || (aggregateColumn && !alias)" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold rounded text-xs">Apply</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GroupByModal',
  props: {
    modelValue: { type: Boolean, default: false },
    columns: { type: Array, default: () => [] }
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return { groupColumn: '', aggregateColumn: '', aggregateFunction: 'SUM', alias: '' };
  },
  computed: {
    isOpen: {
      get() { return this.modelValue; },
      set(value) { this.$emit('update:modelValue', value); }
    }
  },
  watch: {
    columns: {
      handler(columns) {
        if (!this.groupColumn && columns.length) this.groupColumn = columns[0];
      },
      immediate: true
    },
    aggregateColumn(value) {
      if (value && !this.alias) this.alias = `${value}_${this.aggregateFunction.toLowerCase()}`;
    }
  },
  methods: {
    close() { this.isOpen = false; },
    submit() {
      if (!this.groupColumn) return;
      const aggregations = [];
      if (this.aggregateColumn && this.alias) {
        aggregations.push({ column: this.aggregateColumn, agg: this.aggregateFunction, alias: this.alias });
      }
      const params = {
        group_columns: [this.groupColumn],
        aggregations
      };
      this.$emit('apply', {
        operation: 'group_by',
        name: `Grouped Rows (${this.groupColumn})`,
        params
      });
      this.close();
    }
  }
};
</script>
