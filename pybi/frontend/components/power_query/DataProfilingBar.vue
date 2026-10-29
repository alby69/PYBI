<template>
  <div class="data-profiling-bar flex items-center gap-4 px-3 py-1.5 bg-indigo-50 border-b border-indigo-200 text-[11px] text-indigo-900 select-none">
    <div class="flex items-center gap-1 font-bold">
      <span>📈</span>
      <span>Column profile:</span>
      <span class="font-mono bg-white/70 px-1.5 py-0.5 rounded border border-indigo-200">{{ column }}</span>
    </div>
    <div class="flex items-center gap-4 flex-wrap">
      <span>Rows: <strong>{{ total }}</strong></span>
      <span>Nulls: <strong>{{ nulls }}</strong> ({{ nullPercent }}%)</span>
      <span>Distinct: <strong>{{ distinct }}</strong></span>
      <span v-if="numeric">Min: <strong>{{ format(min) }}</strong></span>
      <span v-if="numeric">Max: <strong>{{ format(max) }}</strong></span>
      <span v-if="numeric">Avg: <strong>{{ format(avg) }}</strong></span>
      <span v-if="!numeric && mostCommon">Most common: <strong>{{ mostCommon }}</strong></span>
    </div>
    <button @click="$emit('close')" class="ml-auto text-indigo-500 hover:text-indigo-800 font-bold" title="Close profile">×</button>
  </div>
</template>

<script>
export default {
  name: 'DataProfilingBar',
  props: {
    column: { type: String, required: true },
    rows: { type: Array, default: () => [] },
    type: { type: String, default: '' }
  },
  emits: ['close'],
  computed: {
    values() {
      return this.rows.map(row => row?.[this.column]).filter(value => value !== null && value !== undefined);
    },
    total() {
      return this.rows.length;
    },
    nulls() {
      return this.total - this.values.length;
    },
    nullPercent() {
      return this.total === 0 ? '0.0' : ((this.nulls / this.total) * 100).toFixed(1);
    },
    distinct() {
      return new Set(this.values.map(value => String(value))).size;
    },
    numeric() {
      if (this.values.length === 0) return false;
      return this.values.every(value => typeof value === 'number' || (!isNaN(Number(value)) && String(value).trim() !== ''));
    },
    numericValues() {
      return this.values.map(Number).filter(value => !Number.isNaN(value));
    },
    min() {
      return this.numericValues.length ? Math.min(...this.numericValues) : null;
    },
    max() {
      return this.numericValues.length ? Math.max(...this.numericValues) : null;
    },
    avg() {
      if (!this.numericValues.length) return null;
      return this.numericValues.reduce((sum, value) => sum + value, 0) / this.numericValues.length;
    },
    mostCommon() {
      if (this.numeric) return '';
      const counts = new Map();
      this.values.forEach(value => {
        const key = String(value);
        counts.set(key, (counts.get(key) || 0) + 1);
      });
      let best = '';
      let bestCount = 0;
      counts.forEach((count, key) => {
        if (count > bestCount) {
          best = key;
          bestCount = count;
        }
      });
      return best ? `${best} (${bestCount})` : '';
    }
  },
  methods: {
    format(value) {
      if (value === null || value === undefined) return '—';
      if (typeof value !== 'number') return value;
      return Number.isInteger(value) ? value : value.toFixed(2);
    }
  }
};
</script>
