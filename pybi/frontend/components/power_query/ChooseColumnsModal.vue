<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-md overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800"><span>📋</span><span>Choose Columns</span></div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 font-bold text-lg">×</button>
      </div>
      <div class="p-4 flex flex-col gap-2 text-xs">
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-1"><input type="radio" value="keep" v-model="mode" /> Keep selected</label>
          <label class="flex items-center gap-1"><input type="radio" value="remove" v-model="mode" /> Remove selected</label>
        </div>
        <div class="max-h-64 overflow-y-auto border border-slate-200 rounded p-2 flex flex-col gap-1">
          <label v-for="col in columns" :key="col" class="flex items-center gap-2 px-1 py-0.5 hover:bg-slate-50 rounded cursor-pointer">
            <input type="checkbox" :value="col" v-model="selected" />
            <span class="font-mono text-[11px]">{{ col }}</span>
          </label>
          <span v-if="!columns.length" class="text-slate-400 italic">No columns available.</span>
        </div>
        <div class="flex items-center gap-2 text-[10px] text-slate-500">
          <button @click="selectAll" class="text-blue-600 hover:underline">Select all</button>
          <button @click="clearAll" class="text-blue-600 hover:underline">Clear</button>
          <span class="ml-auto">{{ selected.length }} selected</span>
        </div>
      </div>
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">Cancel</button>
        <button @click="submit" :disabled="!selected.length" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold rounded text-xs">Apply</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChooseColumnsModal',
  props: {
    modelValue: { type: Boolean, default: false },
    columns: { type: Array, default: () => [] },
    defaultMode: { type: String, default: 'keep' }
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return { selected: [], mode: 'keep' };
  },
  computed: {
    isOpen: {
      get() { return this.modelValue; },
      set(value) { this.$emit('update:modelValue', value); }
    }
  },
  watch: {
    isOpen(value) {
      if (value) {
        this.selected = [...this.columns];
        this.mode = this.defaultMode || 'keep';
      }
    }
  },
  methods: {
    close() { this.isOpen = false; },
    selectAll() { this.selected = [...this.columns]; },
    clearAll() { this.selected = []; },
    submit() {
      if (!this.selected.length) return;
      if (this.mode === 'keep') {
        this.$emit('apply', {
          operation: 'select',
          name: `Kept Columns (${this.selected.length})`,
          params: { columns: [...this.selected] }
        });
      } else {
        this.$emit('apply', {
          operation: 'remove_column',
          name: `Removed Columns (${this.selected.length})`,
          params: { columns: [...this.selected] }
        });
      }
      this.close();
    }
  }
};
</script>
