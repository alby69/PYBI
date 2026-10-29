<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden">
      <!-- Modal Header -->
      <div class="px-6 py-4 bg-slate-800 text-white flex items-center justify-between">
        <h2 class="text-base font-bold flex items-center gap-2">
          <span>🔗</span>
          <span>Gestisci Relazioni Modello</span>
        </h2>
        <button class="text-slate-400 hover:text-white font-bold" @click="close">✕</button>
      </div>

      <!-- Modal Body -->
      <div class="p-6 overflow-y-auto flex-1">
        <table class="w-full text-xs text-left border-collapse">
          <thead>
            <tr class="bg-slate-100 text-slate-700 border-b">
              <th class="p-2 font-semibold">Attiva</th>
              <th class="p-2 font-semibold">Da Tabella</th>
              <th class="p-2 font-semibold">Da Colonna</th>
              <th class="p-2 font-semibold">A Tabella</th>
              <th class="p-2 font-semibold">A Colonna</th>
              <th class="p-2 font-semibold">Cardinalità</th>
              <th class="p-2 font-semibold">Filtro Incrociato</th>
              <th class="p-2 font-semibold text-right">Azione</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="!modelStore.relationships || modelStore.relationships.length === 0">
              <td colspan="8" class="p-4 text-center text-slate-400 italic">
                Nessuna relazione presente nel modello. Fai clic su "Rileva Automatica" o trascina colonne nel canvas.
              </td>
            </tr>
            <tr
              v-for="rel in modelStore.relationships"
              :key="rel.id"
              class="hover:bg-slate-50"
            >
              <td class="p-2">
                <input
                  type="checkbox"
                  v-model="rel.is_active"
                  class="rounded text-blue-600"
                  @change="modelStore.addOrUpdateRelationship(rel)"
                />
              </td>
              <td class="p-2 font-medium text-slate-800">{{ rel.from_table }}</td>
              <td class="p-2 font-mono text-slate-600">{{ rel.from_column }}</td>
              <td class="p-2 font-medium text-slate-800">{{ rel.to_table }}</td>
              <td class="p-2 font-mono text-slate-600">{{ rel.to_column }}</td>
              <td class="p-2">
                <span class="px-1.5 py-0.5 bg-slate-100 border rounded font-mono font-semibold text-slate-700">
                  {{ rel.cardinality }}
                </span>
              </td>
              <td class="p-2">
                <span class="text-slate-600 capitalize">{{ rel.cross_filter_direction || 'single' }}</span>
              </td>
              <td class="p-2 text-right">
                <button
                  class="text-red-600 hover:text-red-800 font-semibold px-1.5 py-0.5 rounded hover:bg-red-50"
                  @click="modelStore.deleteRelationship(rel.id)"
                >
                  Elimina
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Modal Footer -->
      <div class="px-6 py-3 bg-slate-50 border-t flex items-center justify-between">
        <button
          class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium text-xs flex items-center gap-1 shadow-sm"
          :disabled="modelStore.isAutodetectLoading"
          @click="modelStore.runAutodetect()"
        >
          <span>✨</span>
          <span>Rileva automatica (Autodetect)</span>
        </button>

        <button
          class="px-4 py-1.5 bg-slate-700 hover:bg-slate-800 text-white rounded font-medium text-xs shadow-sm"
          @click="close"
        >
          Chiudi
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useModelStore } from '../../../stores/modelStore.js';

const props = defineProps({
  isOpen: Boolean,
});

const emit = defineEmits(['close']);
const modelStore = useModelStore();

function close() {
  emit('close');
}
</script>
