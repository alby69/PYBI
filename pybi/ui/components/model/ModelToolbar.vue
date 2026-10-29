<template>
  <div class="model-toolbar w-full bg-slate-100 border-b border-slate-200 px-4 py-2 flex items-center justify-between gap-3 shadow-sm">
    <!-- Left Group: Actions -->
    <div class="flex items-center gap-2">
      <!-- Gestisci Relazioni -->
      <button
        class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-xs flex items-center gap-1.5 shadow-sm transition"
        @click="$emit('open-manage-relationships')"
      >
        <span>🔗</span>
        <span>Gestisci relazioni</span>
      </button>

      <!-- Rileva Automatica -->
      <button
        class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium text-xs flex items-center gap-1.5 shadow-sm transition disabled:opacity-50"
        :disabled="modelStore.isAutodetectLoading"
        @click="modelStore.runAutodetect()"
      >
        <span>✨</span>
        <span>{{ modelStore.isAutodetectLoading ? 'Scansione...' : 'Rileva automatica' }}</span>
      </button>

      <!-- Nuova Misura -->
      <button
        class="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded font-medium text-xs flex items-center gap-1.5 shadow-sm transition"
        @click="$emit('open-measure-editor')"
      >
        <span>∑</span>
        <span>Nuova misura</span>
      </button>

      <div class="h-5 w-px bg-slate-300 mx-1"></div>

      <!-- Layout Automatico (Star Schema) -->
      <button
        class="px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white rounded font-medium text-xs flex items-center gap-1.5 shadow-sm transition"
        @click="autoLayoutStarSchema"
      >
        <span>📐</span>
        <span>Layout automatico</span>
      </button>
    </div>

    <!-- Right Group: Zoom Controls & Canvas Actions -->
    <div class="flex items-center gap-2">
      <button
        class="px-2.5 py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded text-xs font-semibold shadow-sm"
        title="Fit View"
        @click="$emit('fit-view')"
      >
        <span>🔍 Adatta alla schermata</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { useModelStore } from '../../stores/modelStore.js';

const emit = defineEmits(['open-manage-relationships', 'open-measure-editor', 'fit-view']);
const modelStore = useModelStore();

function autoLayoutStarSchema() {
  const tables = modelStore.tables;
  if (!tables || tables.length === 0) return;

  const factTables = tables.filter(t => {
    const name = (t.name || '').toLowerCase();
    return name.includes('fact') || name.includes('sales') || name.includes('orders') || name.includes('transactions');
  });

  const dimTables = tables.filter(t => !factTables.includes(t));

  const newPositions = {};

  // Position Facts in center
  factTables.forEach((f, idx) => {
    newPositions[f.name] = { x: 400 + idx * 280, y: 300 };
  });

  // Position Dims around facts in a circle/arc
  const radius = 350;
  dimTables.forEach((d, idx) => {
    const angle = (idx / Math.max(1, dimTables.length)) * 2 * Math.PI;
    const x = 400 + Math.cos(angle) * radius;
    const y = 300 + Math.sin(angle) * radius;
    newPositions[d.name] = { x: Math.max(50, x), y: Math.max(50, y) };
  });

  modelStore.saveModelPositions(newPositions);
  emit('fit-view');
}
</script>
