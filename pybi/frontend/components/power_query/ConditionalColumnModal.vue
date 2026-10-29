<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-lg overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800"><span>🔀</span><span>Conditional Column</span></div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 font-bold text-lg">×</button>
      </div>
      <div class="p-4 flex flex-col gap-3 text-xs">
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">New column name</span>
          <input v-model="newColumn" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" />
        </label>
        <div class="grid grid-cols-3 gap-2">
          <label class="flex flex-col gap-1 col-span-1">
            <span class="font-semibold text-slate-700">If column</span>
            <select v-model="conditionColumn" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
              <option v-for="col in columns" :key="col" :value="col">{{ col }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Operator</span>
            <select v-model="operator" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
              <option value="=">=</option>
              <option value="!=">!=</option>
              <option value=">">&gt;</option>
              <option value="<">&lt;</option>
              <option value=">=">&gt;=</option>
              <option value="<=">&lt;=</option>
            </select>
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Value</span>
            <input v-model="conditionValue" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" />
          </label>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Then</span>
            <input v-model="thenValue" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Else</span>
            <input v-model="elseValue" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" />
          </label>
        </div>
      </div>
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">Cancel</button>
        <button @click="submit" :disabled="!newColumn || !conditionColumn" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold rounded text-xs">Add Column</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConditionalColumnModal',
  props: {
    modelValue: { type: Boolean, default: false },
    columns: { type: Array, default: () => [] }
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return {
      newColumn: 'Conditional',
      conditionColumn: '',
      operator: '=',
      conditionValue: '',
      thenValue: 'Yes',
      elseValue: 'No'
    };
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
        if (!this.conditionColumn && columns.length) this.conditionColumn = columns[0];
      },
      immediate: true
    }
  },
  methods: {
    close() { this.isOpen = false; },
    submit() {
      if (!this.newColumn || !this.conditionColumn) return;
      this.$emit('apply', {
        operation: 'conditional_column',
        name: `Added Conditional Column (${this.newColumn})`,
        params: {
          new_column: this.newColumn,
          cond_col: this.conditionColumn,
          cond_op: this.operator,
          cond_val: this.conditionValue,
          then_value: this.thenValue,
          else_value: this.elseValue
        }
      });
      this.close();
    }
  }
};
</script>
