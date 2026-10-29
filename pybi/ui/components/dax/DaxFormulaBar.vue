<template>
  <div class="dax-formula-bar-container bg-grey-2 q-pa-xs border-bottom">
    <div class="row items-center q-col-gutter-xs">
      <!-- Icona Misura / Azioni -->
      <div class="col-auto row items-center">
        <q-icon name="functions" color="primary" size="sm" class="q-mr-xs" />
        <q-btn icon="check" color="positive" flat dense round @click="commitMeasure" :disabled="!isValid" />
        <q-btn icon="close" color="negative" flat dense round @click="cancelEdit" />
        <q-separator vertical class="q-mx-xs" />
      </div>

      <!-- Monaco Code Editor Host -->
      <div class="col">
        <div ref="editorRef" class="dax-monaco-editor" style="height: 38px; width: 100%;"></div>
      </div>

      <!-- Help & Status Badge -->
      <div class="col-auto row items-center">
        <q-badge :color="isValid ? 'positive' : 'negative'" class="q-mr-xs">
          {{ isValid ? 'Sintassi Valida' : 'Errore Sintassi' }}
        </q-badge>
        <q-btn icon="help_outline" flat dense round color="grey-7" @click="showDaxHelper = true" />
      </div>
    </div>

    <!-- Drawer / Modale di Aiuto Funzioni DAX -->
    <q-dialog v-model="showDaxHelper">
      <q-card style="width: 700px; max-width: 90vw;">
        <q-card-section class="row items-center">
          <div class="text-h6">Guida e Prontuario Funzioni DAX</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section class="q-pa-md">
          <q-input v-model="searchFilter" placeholder="Cerca funzione DAX (es. CALCULATE, DATESYTD)..." dense outlined class="q-mb-md" />
          <q-list separator class="scroll" style="max-height: 400px;">
            <q-item v-for="(info, name) in filteredFunctions" :key="name" clickable @click="insertFunction(name, info.syntax)">
              <q-item-section>
                <q-item-label class="text-bold text-primary">{{ name }}</q-item-label>
                <q-item-label caption class="text-monospace">{{ info.syntax }}</q-item-label>
                <q-item-label caption>{{ info.doc }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-chip dense color="blue-1" text-color="blue-9">{{ info.category }}</q-chip>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useDaxStore } from '../../stores/daxStore';

const props = defineProps({
  measureId: String,
  initialExpression: { type: String, default: 'Total Sales = SUM(Sales[Amount])' }
});

const daxStore = useDaxStore();
const editorRef = ref(null);
const isValid = ref(true);
const showDaxHelper = ref(false);
const searchFilter = ref('');

const daxFunctions = {
  CALCULATE: { category: 'Filter', syntax: 'CALCULATE(<expr>, <filter1>, ...)', doc: 'Valuta un\'espressione in un contesto di filtro modificato.' },
  SUMX: { category: 'Aggregation', syntax: 'SUMX(<table>, <expr>)', doc: 'Calcola la somma di un\'espressione riga per riga.' },
  DATESYTD: { category: 'Time Intelligence', syntax: 'DATESYTD(<dates>)', doc: 'Restituisce le date dall\'inizio dell\'anno ad oggi.' },
  FILTER: { category: 'Filter', syntax: 'FILTER(<table>, <condition>)', doc: 'Filtra una tabella in base a una condizione.' },
  ALL: { category: 'Filter', syntax: 'ALL([<table>|<column>])', doc: 'Rimuove tutti i filtri dal contesto.' }
};

const filteredFunctions = computed(() => {
  if (!searchFilter.value) return daxFunctions;
  const q = searchFilter.value.toUpperCase();
  return Object.fromEntries(
    Object.entries(daxFunctions).filter(([k]) => k.includes(q))
  );
});

let monacoInstance = null;

onMounted(() => {
  if (window.monaco) {
    monacoInstance = window.monaco.editor.create(editorRef.value, {
      value: props.initialExpression,
      language: 'sql',
      theme: 'vs',
      minimap: { enabled: false },
      lineNumbers: 'off',
      glyphMargin: false,
      folding: false,
      scrollBeyondLastLine: false,
      wordWrap: 'on'
    });

    monacoInstance.onDidChangeModelContent(() => {
      const expr = monacoInstance.getValue();
      validateFormula(expr);
    });
  }
});

async function validateFormula(expr) {
  const res = await daxStore.validateExpression(expr);
  isValid.value = res.is_valid;
}

function commitMeasure() {
  if (monacoInstance) {
    daxStore.saveMeasure(monacoInstance.getValue());
  }
}

function cancelEdit() {
  if (monacoInstance) {
    monacoInstance.setValue(props.initialExpression);
  }
}

function insertFunction(name, syntax) {
  if (monacoInstance) {
    monacoInstance.trigger('keyboard', 'type', { text: `${name}(` });
    showDaxHelper.value = false;
  }
}
</script>

<style scoped>
.dax-formula-bar-container {
  border-bottom: 1px solid #e0e0e0;
}
.dax-monaco-editor {
  border: 1px solid #ccc;
  border-radius: 4px;
}
</style>
