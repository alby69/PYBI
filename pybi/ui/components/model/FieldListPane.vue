<template>
  <div class="field-list-pane w-64 bg-white border-r border-slate-200 h-full flex flex-col p-3 shadow-sm overflow-hidden">
    <!-- Search Bar -->
    <div class="mb-3">
      <input
        v-model="modelStore.searchFilter"
        type="text"
        placeholder="🔍 Cerca campi e misure..."
        class="w-full border border-slate-300 rounded px-2.5 py-1.5 text-xs focus:outline-none focus:border-blue-500"
      />
    </div>

    <!-- Tree View -->
    <div class="flex-1 overflow-y-auto text-xs space-y-2">
      <div v-for="table in filteredTables" :key="table.name" class="table-group border border-slate-200 rounded overflow-hidden">
        <!-- Table Header -->
        <div
          class="table-header bg-slate-100 px-2.5 py-1.5 font-bold text-slate-700 flex items-center justify-between cursor-pointer hover:bg-slate-200"
          @click="toggleTable(table.name)"
        >
          <div class="flex items-center gap-1.5 truncate">
            <span>{{ isExpanded(table.name) ? '▼' : '▶' }}</span>
            <span>📊</span>
            <span class="truncate">{{ table.name }}</span>
          </div>
          <span class="text-[10px] text-slate-500 font-normal">({{ table.columns.length + (table.measures || []).length }})</span>
        </div>

        <!-- Columns & Measures -->
        <div v-if="isExpanded(table.name)" class="p-1 space-y-0.5 bg-white divide-y divide-slate-50">
          <!-- Columns -->
          <div
            v-for="col in filterColumns(table.columns)"
            :key="col.name"
            class="px-2 py-1 flex items-center justify-between hover:bg-slate-50 rounded cursor-pointer text-slate-700"
            @click="modelStore.selectEntity('column', { ...col, table_name: table.name })"
          >
            <div class="flex items-center gap-1.5 truncate">
              <span class="text-[10px] text-slate-400 font-mono">{{ getTypeIcon(col.data_type) }}</span>
              <span v-if="col.is_key">🔑</span>
              <span class="truncate">{{ col.name }}</span>
            </div>
          </div>

          <!-- Measures -->
          <div
            v-for="meas in filterMeasures(table.measures || [])"
            :key="meas.id || meas.name"
            class="px-2 py-1 flex items-center justify-between hover:bg-amber-50 rounded cursor-pointer text-amber-900 font-medium"
            @click="modelStore.selectEntity('measure', meas)"
          >
            <div class="flex items-center gap-1.5 truncate">
              <span class="text-xs font-bold text-amber-700">∑</span>
              <span class="truncate">{{ meas.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useModelStore } from '../../stores/modelStore.js';

const modelStore = useModelStore();
const expandedTables = ref(new Set());

function toggleTable(tableName) {
  if (expandedTables.value.has(tableName)) {
    expandedTables.value.delete(tableName);
  } else {
    expandedTables.value.add(tableName);
  }
}

function isExpanded(tableName) {
  return expandedTables.value.has(tableName) || !!modelStore.searchFilter;
}

const filteredTables = computed(() => {
  const query = (modelStore.searchFilter || '').toLowerCase().trim();
  if (!query) return modelStore.tables;

  return modelStore.tables.filter(tbl => {
    const tableMatch = tbl.name.toLowerCase().includes(query);
    const colMatch = (tbl.columns || []).some(c => c.name.toLowerCase().includes(query));
    const measMatch = (tbl.measures || []).some(m => m.name.toLowerCase().includes(query));
    return tableMatch || colMatch || measMatch;
  });
});

function filterColumns(cols) {
  const query = (modelStore.searchFilter || '').toLowerCase().trim();
  if (!query) return cols;
  return cols.filter(c => c.name.toLowerCase().includes(query));
}

function filterMeasures(measures) {
  const query = (modelStore.searchFilter || '').toLowerCase().trim();
  if (!query) return measures;
  return measures.filter(m => m.name.toLowerCase().includes(query));
}

function getTypeIcon(dataType) {
  const t = (dataType || '').toLowerCase();
  if (t.includes('int') || t.includes('number') || t.includes('float')) return '123';
  if (t.includes('date') || t.includes('time')) return '📅';
  if (t.includes('bool')) return 'T/F';
  return 'ABC';
}
</script>
