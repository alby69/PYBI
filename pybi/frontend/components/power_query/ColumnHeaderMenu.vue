<template>
  <div
    class="absolute left-0 top-full mt-1 w-52 bg-white border border-slate-300 rounded shadow-xl z-40 py-1 text-xs font-normal"
    @click.stop
  >
    <button @click="emitAction('sort-asc')" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
      <span>⬆️</span> Sort Ascending
    </button>
    <button @click="emitAction('sort-desc')" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
      <span>⬇️</span> Sort Descending
    </button>
    <div class="border-t border-slate-200 my-1"></div>
    <button @click="emitAction('filter')" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
      <span>🔍</span> Filter Column...
    </button>
    <button @click="emitAction('rename')" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
      <span>✏️</span> Rename Column...
    </button>
    <button @click="emitAction('cast')" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
      <span>🔄</span> Change Type...
    </button>
    <button @click="emitAction('duplicate')" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
      <span>🧬</span> Duplicate Column
    </button>
    <button @click="emitAction('profile')" class="w-full text-left px-3 py-1.5 hover:bg-blue-50 text-slate-700 flex items-center gap-2">
      <span>📈</span> Column Profile
    </button>
    <div class="border-t border-slate-200 my-1"></div>
    <button @click="emitAction('remove')" class="w-full text-left px-3 py-1.5 hover:bg-red-50 text-red-600 flex items-center gap-2">
      <span>🗑️</span> Remove Column
    </button>
  </div>
</template>

<script>
export default {
  name: 'ColumnHeaderMenu',
  props: {
    column: { type: String, required: true }
  },
  emits: ['action', 'close'],
  methods: {
    emitAction(action) {
      this.$emit('action', action, this.column);
      this.$emit('close');
    }
  }
};
</script>
