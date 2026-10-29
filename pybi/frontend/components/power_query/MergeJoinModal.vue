<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-lg overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800"><span>🔗</span><span>Merge Queries</span></div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 font-bold text-lg">×</button>
      </div>
      <div class="p-4 flex flex-col gap-3 text-xs">
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Right table / file</span>
          <select v-model="rightTable" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
            <option v-for="table in tables" :key="table" :value="table">{{ table }}</option>
          </select>
        </label>
        <label class="flex flex-col gap-1">
          <span class="font-semibold text-slate-700">Join type</span>
          <select v-model="joinType" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
            <option value="inner">Inner</option>
            <option value="left">Left outer</option>
            <option value="right">Right outer</option>
            <option value="full">Full outer</option>
          </select>
        </label>
        <div class="grid grid-cols-2 gap-2">
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Left key</span>
            <select v-model="leftKey" class="px-2 py-1.5 border border-slate-300 rounded bg-white">
              <option v-for="col in columns" :key="col" :value="col">{{ col }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1">
            <span class="font-semibold text-slate-700">Right key</span>
            <input v-model="rightKey" type="text" class="px-2 py-1.5 border border-slate-300 rounded bg-white font-mono" placeholder="same as left" />
          </label>
        </div>
      </div>
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">Cancel</button>
        <button @click="submit" :disabled="!rightTable || !leftKey" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold rounded text-xs">Merge</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MergeJoinModal',
  props: {
    modelValue: { type: Boolean, default: false },
    columns: { type: Array, default: () => [] },
    tables: { type: Array, default: () => [] }
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return { rightTable: '', joinType: 'left', leftKey: '', rightKey: '' };
  },
  computed: {
    isOpen: {
      get() { return this.modelValue; },
      set(value) { this.$emit('update:modelValue', value); }
    }
  },
  watch: {
    tables: {
      handler(tables) {
        if (!this.rightTable && tables.length) this.rightTable = tables[0];
      },
      immediate: true
    },
    columns: {
      handler(columns) {
        if (!this.leftKey && columns.length) this.leftKey = columns[0];
      },
      immediate: true
    }
  },
  methods: {
    close() { this.isOpen = false; },
    submit() {
      if (!this.rightTable || !this.leftKey) return;
      const rightColumn = this.rightKey || this.leftKey;
      const params = {
        target_table: this.rightTable,
        right_table: this.rightTable,
        how: this.joinType,
        left_on: this.leftKey,
        right_on: rightColumn
      };
      if (/\.[A-Za-z0-9]+$/.test(this.rightTable)) {
        params.target_path = this.rightTable;
        params.right_path = this.rightTable;
      }
      this.$emit('apply', {
        operation: 'merge',
        name: `Merged with ${this.rightTable}`,
        params
      });
      this.close();
    }
  }
};
</script>
