<template>
  <div class="properties-panel w-80 bg-white border-l border-slate-200 h-full flex flex-col p-4 shadow-sm overflow-y-auto">
    <!-- Header -->
    <div class="border-b border-slate-200 pb-3 mb-4 flex items-center justify-between">
      <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
        <span>⚙️</span>
        <span>Proprietà {{ entityTypeName }}</span>
      </h3>
      <button
        v-if="modelStore.selectedItem"
        class="text-xs text-slate-400 hover:text-slate-600 font-semibold"
        @click="modelStore.selectEntity(null, null)"
      >
        ✕ Chiudi
      </button>
    </div>

    <!-- Empty State -->
    <div v-if="!selectedItem" class="text-slate-400 text-xs italic py-8 text-center">
      Seleziona una tabella, colonna o relazione nel canvas per visualizzarne e modificarne le proprietà.
    </div>

    <!-- Relationship Properties -->
    <div v-else-if="selectedItem.type === 'relationship'" class="flex flex-col gap-3 text-xs">
      <div>
        <label class="block font-semibold text-slate-700 mb-1">Tabella di origine (From)</label>
        <select
          v-model="relForm.from_table"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300"
          @change="onRelationshipChange"
        >
          <option v-for="t in modelStore.tables" :key="t.name" :value="t.name">{{ t.name }}</option>
        </select>
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Colonna di origine</label>
        <select
          v-model="relForm.from_column"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300"
          @change="onRelationshipChange"
        >
          <option v-for="c in fromColumns" :key="c.name" :value="c.name">{{ c.name }}</option>
        </select>
      </div>

      <div class="my-1 border-t border-slate-100"></div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Tabella di destinazione (To)</label>
        <select
          v-model="relForm.to_table"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300"
          @change="onRelationshipChange"
        >
          <option v-for="t in modelStore.tables" :key="t.name" :value="t.name">{{ t.name }}</option>
        </select>
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Colonna di destinazione</label>
        <select
          v-model="relForm.to_column"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300"
          @change="onRelationshipChange"
        >
          <option v-for="c in toColumns" :key="c.name" :value="c.name">{{ c.name }}</option>
        </select>
      </div>

      <div class="my-1 border-t border-slate-100"></div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Cardinalità</label>
        <select
          v-model="relForm.cardinality"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300"
          @change="onRelationshipChange"
        >
          <option value="1:1">1:1 (One to One)</option>
          <option value="1:*">1:* (One to Many)</option>
          <option value="*:1">*:1 (Many to One)</option>
          <option value="*:*">*:* (Many to Many)</option>
        </select>
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Direzione filtro incrociato</label>
        <select
          v-model="relForm.cross_filter_direction"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300"
          @change="onRelationshipChange"
        >
          <option value="single">Single (Unidirezionale)</option>
          <option value="both">Both (Bidirezionale)</option>
        </select>
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Tipo di Join</label>
        <select
          v-model="relForm.join_type"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300"
          @change="onRelationshipChange"
        >
          <option value="LEFT">LEFT OUTER JOIN</option>
          <option value="INNER">INNER JOIN</option>
          <option value="RIGHT">RIGHT OUTER JOIN</option>
          <option value="FULL">FULL OUTER JOIN</option>
        </select>
      </div>

      <div class="flex items-center justify-between py-2 border-t border-b border-slate-100 my-1">
        <span class="font-semibold text-slate-700">Relazione Attiva</span>
        <input
          type="checkbox"
          v-model="relForm.is_active"
          class="w-4 h-4 text-blue-600 rounded"
          @change="onRelationshipChange"
        />
      </div>

      <button
        class="mt-4 px-3 py-2 bg-red-50 hover:bg-red-100 text-red-700 rounded font-semibold text-xs border border-red-200 transition flex items-center justify-center gap-1.5"
        @click="deleteSelectedRelationship"
      >
        <span>🗑️</span>
        <span>Elimina Relazione</span>
      </button>
    </div>

    <!-- Column Properties -->
    <div v-else-if="selectedItem.type === 'column'" class="flex flex-col gap-3 text-xs">
      <div>
        <label class="block font-semibold text-slate-700 mb-1">Nome Colonna</label>
        <input
          v-model="selectedItem.data.name"
          type="text"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300 font-mono"
          readonly
        />
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Tipo Dati</label>
        <input
          v-model="selectedItem.data.data_type"
          type="text"
          class="w-full border rounded px-2 py-1.5 bg-slate-50 border-slate-300 font-mono"
          readonly
        />
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Cartella di visualizzazione</label>
        <input
          v-model="selectedItem.data.display_folder"
          type="text"
          placeholder="es. Anagrafica"
          class="w-full border rounded px-2 py-1.5 bg-white border-slate-300"
          @change="onColumnChange"
        />
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Formattazione Stringa</label>
        <input
          v-model="selectedItem.data.format_string"
          type="text"
          placeholder="es. #,##0.00"
          class="w-full border rounded px-2 py-1.5 bg-white border-slate-300"
          @change="onColumnChange"
        />
      </div>

      <div class="flex items-center justify-between py-2 border-t border-b border-slate-100 my-1">
        <span class="font-semibold text-slate-700">Nascosto (Is Hidden)</span>
        <input
          type="checkbox"
          v-model="selectedItem.data.is_hidden"
          class="w-4 h-4 text-blue-600 rounded"
          @change="onColumnChange"
        />
      </div>
    </div>

    <!-- Measure Properties -->
    <div v-else-if="selectedItem.type === 'measure'" class="flex flex-col gap-3 text-xs">
      <div>
        <label class="block font-semibold text-slate-700 mb-1">Nome Misura</label>
        <input
          v-model="selectedItem.data.name"
          type="text"
          class="w-full border rounded px-2 py-1.5 bg-white border-slate-300 font-semibold"
          @change="onMeasureChange"
        />
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Tabella di appartenenza (Home Table)</label>
        <select
          v-model="selectedItem.data.table_name"
          class="w-full border rounded px-2 py-1.5 bg-white border-slate-300"
          @change="onMeasureChange"
        >
          <option v-for="t in modelStore.tables" :key="t.name" :value="t.name">{{ t.name }}</option>
        </select>
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Formula (DAX / DuckDB SQL)</label>
        <textarea
          v-model="selectedItem.data.expression"
          rows="4"
          class="w-full border rounded p-2 bg-slate-900 text-green-400 font-mono text-[11px]"
          @change="onMeasureChange"
        ></textarea>
      </div>

      <div>
        <label class="block font-semibold text-slate-700 mb-1">Formattazione</label>
        <input
          v-model="selectedItem.data.format_string"
          type="text"
          class="w-full border rounded px-2 py-1.5 bg-white border-slate-300"
          @change="onMeasureChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useModelStore } from '../../stores/modelStore.js';

const modelStore = useModelStore();

const selectedItem = computed(() => modelStore.selectedItem);

const entityTypeName = computed(() => {
  if (!selectedItem.value) return '';
  switch (selectedItem.value.type) {
    case 'relationship': return 'Relazione';
    case 'column': return 'Colonna';
    case 'measure': return 'Misura Calcolata';
    case 'table': return 'Tabella';
    default: return '';
  }
});

const relForm = ref({});

watch(
  () => selectedItem.value,
  (item) => {
    if (item?.type === 'relationship') {
      relForm.value = { ...item.data };
    }
  },
  { immediate: true, deep: true }
);

const fromColumns = computed(() => {
  const tbl = modelStore.tables.find(t => t.name === relForm.value.from_table);
  return tbl ? tbl.columns : [];
});

const toColumns = computed(() => {
  const tbl = modelStore.tables.find(t => t.name === relForm.value.to_table);
  return tbl ? tbl.columns : [];
});

function onRelationshipChange() {
  if (selectedItem.value?.type === 'relationship') {
    modelStore.addOrUpdateRelationship({ ...relForm.value });
  }
}

function deleteSelectedRelationship() {
  if (relForm.value.id) {
    modelStore.deleteRelationship(relForm.value.id);
  }
}

function onColumnChange() {
  modelStore.persistModel();
}

function onMeasureChange() {
  if (selectedItem.value?.type === 'measure') {
    modelStore.saveMeasure({ ...selectedItem.value.data });
  }
}
</script>
