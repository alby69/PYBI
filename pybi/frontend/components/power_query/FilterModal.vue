<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-lg overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800"><span>🔍</span><span>Filter Rows</span></div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 font-bold text-lg">×</button>
      </div>
      <div class="p-4 flex flex-col gap-3 text-xs">
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Column</span>
          <select v-model="column" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
            <option v-for="col in columns" :key="col" :value="col">{{ col }}</option>
          </select>
        </label>
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Operator</span>
          <select v-model="operator" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
            <option value="=">equals (=)</option>
            <option value="!=">not equals (!=)</option>
            <option value=">">greater than (&gt;)</option>
            <option value="<">less than (&lt;)</option>
            <option value=">=">greater or equal (&gt;=)</option>
            <option value="<=">less or equal (&lt;=)</option>
            <option value="contains">contains</option>
            <option value="startswith">starts with</option>
            <option value="endswith">ends with</option>
            <option value="isnull">is null</option>
            <option value="isnotnull">is not null</option>
          </select>
        </label>
        <label v-if="!['isnull', 'isnotnull'].includes(operator)" class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Value</span>
          <input v-model="value" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" placeholder="e.g. EU" />
        </label>
        <div class="bg-slate-50 border border-slate-200 rounded p-2 text-[11px] font-mono text-slate-600">
          WHERE {{ previewCondition }}
        </div>
      </div>
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">Cancel</button>
        <button @click="submit" :disabled="!column || !canSubmit" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold rounded text-xs">Apply</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FilterModal',
  props: {
    modelValue: { type: Boolean, default: false },
    columns: { type: Array, default: () => [] },
    defaultColumn: { type: String, default: '' }
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return { column: '', operator: '=', value: '' };
  },
  computed: {
    isOpen: {
      get() { return this.modelValue; },
      set(value) { this.$emit('update:modelValue', value); }
    },
    canSubmit() {
      return ['isnull', 'isnotnull'].includes(this.operator) || String(this.value).trim() !== '';
    },
    previewCondition() {
      const col = `"${(this.column || 'column').replaceAll('"', '""')}"`;
      if (this.operator === 'isnull') return `${col} IS NULL`;
      if (this.operator === 'isnotnull') return `${col} IS NOT NULL`;
      const escaped = String(this.value).replaceAll("'", "''");
      if (this.operator === 'contains') return `${col} LIKE '%${escaped}%'`;
      if (this.operator === 'startswith') return `${col} LIKE '${escaped}%'`;
      if (this.operator === 'endswith') return `${col} LIKE '%${escaped}'`;
      return `${col} ${this.operator} ${this.quotedValue}`;
    },
    quotedValue() {
      const raw = String(this.value);
      return /^-?\d+(\.\d+)?$/.test(raw) ? raw : `'${raw.replaceAll("'", "''")}'`;
    }
  },
  watch: {
    defaultColumn(value) {
      if (value && !this.column) this.column = value;
    },
    columns: {
      handler(columns) {
        if (!this.column && columns.length) this.column = columns[0];
      },
      immediate: true
    }
  },
  methods: {
    close() { this.isOpen = false; },
    submit() {
      if (!this.column || !this.canSubmit) return;
      const params = { column: this.column, operator: this.operator, condition: this.previewCondition };
      if (!['isnull', 'isnotnull'].includes(this.operator)) params.value = this.value;
      this.$emit('apply', {
        operation: 'filter',
        name: `Filtered Rows (${this.column} ${this.operator} ${this.value || ''})`.trim(),
        params
      });
      this.close();
    }
  }
};
</script>
