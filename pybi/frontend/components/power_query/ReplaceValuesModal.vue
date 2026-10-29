<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-md overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800"><span>🔄</span><span>Replace Values</span></div>
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
          <span class="font-semibold text-slate-700">Find value</span>
          <input v-model="oldValue" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" />
        </label>
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Replace with</span>
          <input v-model="newValue" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" />
        </label>
      </div>
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">Cancel</button>
        <button @click="submit" :disabled="!column || !oldValue" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold rounded text-xs">Apply</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReplaceValuesModal',
  props: {
    modelValue: { type: Boolean, default: false },
    columns: { type: Array, default: () => [] }
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return { column: '', oldValue: '', newValue: '' };
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
        if (!this.column && columns.length) this.column = columns[0];
      },
      immediate: true
    }
  },
  methods: {
    close() { this.isOpen = false; },
    submit() {
      if (!this.column || !this.oldValue) return;
      this.$emit('apply', {
        operation: 'replace_values',
        name: `Replaced Values (${this.column})`,
        params: { column: this.column, old_value: this.oldValue, new_value: this.newValue }
      });
      this.close();
    }
  }
};
</script>
