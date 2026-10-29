<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-lg flex flex-col overflow-hidden">
      <!-- Header -->
      <div class="px-6 py-4 bg-slate-800 text-white flex items-center justify-between">
        <h2 class="text-base font-bold flex items-center gap-2">
          <span>∑</span>
          <span>{{ measureForm.id ? 'Modifica Misura Calcolata' : 'Nuova Misura Calcolata' }}</span>
        </h2>
        <button class="text-slate-400 hover:text-white font-bold" @click="close">✕</button>
      </div>

      <!-- Form Body -->
      <div class="p-6 flex flex-col gap-4 text-xs">
        <div>
          <label class="block font-semibold text-slate-700 mb-1">Tabella di appartenenza (Home Table)</label>
          <select
            v-model="measureForm.table_name"
            class="w-full border rounded px-3 py-2 bg-slate-50 border-slate-300"
          >
            <option v-for="t in modelStore.tables" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>
        </div>

        <div>
          <label class="block font-semibold text-slate-700 mb-1">Nome Misura</label>
          <input
            v-model="measureForm.name"
            type="text"
            placeholder="es. Totale Vendite"
            class="w-full border rounded px-3 py-2 bg-white border-slate-300 font-medium text-slate-800"
          />
        </div>

        <div>
          <label class="block font-semibold text-slate-700 mb-1">Formula Espressione (DAX / DuckDB SQL)</label>
          <textarea
            v-model="measureForm.expression"
            rows="4"
            placeholder="es. SUM(FactOrders.SalesAmount)"
            class="w-full border rounded p-2 bg-slate-900 text-green-400 font-mono text-xs"
          ></textarea>
        </div>

        <div>
          <label class="block font-semibold text-slate-700 mb-1">Formattazione Stringa</label>
          <input
            v-model="measureForm.format_string"
            type="text"
            placeholder="€ #,##0.00"
            class="w-full border rounded px-3 py-2 bg-white border-slate-300"
          />
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-3 bg-slate-50 border-t flex items-center justify-end gap-2">
        <button
          class="px-4 py-1.5 border border-slate-300 text-slate-700 rounded font-medium text-xs hover:bg-slate-100"
          @click="close"
        >
          Annulla
        </button>
        <button
          class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-xs shadow-sm"
          @click="save"
        >
          Salva Misura
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useModelStore } from '../../../stores/modelStore.js';

const props = defineProps({
  isOpen: Boolean,
  measure: Object,
});

const emit = defineEmits(['close']);
const modelStore = useModelStore();

const measureForm = ref({
  id: '',
  name: '',
  table_name: '',
  expression: '',
  format_string: '€ #,##0.00',
});

watch(
  () => props.measure,
  (m) => {
    if (m) {
      measureForm.value = { ...m };
    } else {
      const defaultTable = modelStore.tables[0]?.name || '';
      measureForm.value = {
        id: '',
        name: 'Totale Vendite',
        table_name: defaultTable,
        expression: `SUM(${defaultTable}.SalesAmount)`,
        format_string: '€ #,##0.00',
      };
    }
  },
  { immediate: true }
);

function close() {
  emit('close');
}

async function save() {
  if (!measureForm.value.name || !measureForm.value.table_name) return;
  await modelStore.saveMeasure({ ...measureForm.value });
  close();
}
</script>
