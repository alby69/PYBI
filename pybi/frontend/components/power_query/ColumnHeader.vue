<template>
  <div class="flex items-center justify-between gap-2">
    <button
      @click.stop="$emit('toggle', column)"
      class="flex items-center gap-1.5 focus:outline-none hover:bg-slate-300 px-1 py-0.5 rounded"
      :title="`${column} (${type || 'text'})`"
    >
      <span :class="['px-1 rounded text-[10px] font-bold border', badgeClass]">
        {{ icon }}
      </span>
      <span class="font-bold text-xs text-slate-900">{{ column }}</span>
      <span class="text-[9px] text-slate-500">▼</span>
    </button>
    <span v-if="sortDirection" class="text-[10px] text-blue-700 font-bold">{{ sortDirection === 'desc' ? '↓' : '↑' }}</span>
  </div>
</template>

<script>
export default {
  name: 'ColumnHeader',
  props: {
    column: { type: String, required: true },
    type: { type: String, default: 'text' },
    sortDirection: { type: String, default: '' }
  },
  emits: ['toggle'],
  computed: {
    icon() {
      const type = (this.type || '').toLowerCase();
      if (type.includes('int')) return '123';
      if (type.includes('dec') || type.includes('float') || type.includes('double')) return '1.2';
      if (type.includes('date') || type.includes('time')) return '📅';
      if (type.includes('bool')) return 'TRUE';
      return 'ABC';
    },
    badgeClass() {
      const type = (this.type || '').toLowerCase();
      if (type.includes('int') || type.includes('dec') || type.includes('float')) return 'bg-amber-50 text-amber-800 border-amber-300';
      if (type.includes('date') || type.includes('time')) return 'bg-purple-50 text-purple-800 border-purple-300';
      if (type.includes('bool')) return 'bg-emerald-50 text-emerald-800 border-emerald-300';
      return 'bg-blue-50 text-blue-800 border-blue-300';
    }
  }
};
</script>
