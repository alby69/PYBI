<template>
  <div class="pq-ribbon bg-slate-100 border-b border-slate-300 select-none">
    <div class="flex items-center justify-between bg-slate-200 border-b border-slate-300 text-xs font-semibold text-slate-700">
      <div class="flex items-center">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'px-4 py-1.5 transition-colors focus:outline-none',
            activeTab === tab.id
              ? 'bg-white text-blue-700 border-t-2 border-blue-600 font-bold shadow-xs'
              : 'hover:bg-slate-300 text-slate-600'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="flex items-center gap-2 px-3 text-[11px]">
        <span v-if="store.statusMessage" class="text-emerald-700 font-medium truncate max-w-xs">{{ store.statusMessage }}</span>
        <span v-if="store.error" class="text-red-700 font-medium truncate max-w-xs" :title="store.error">⚠ {{ store.error }}</span>
      </div>
    </div>

    <div class="p-2 flex flex-nowrap items-center gap-3 overflow-x-auto min-h-[64px] bg-white">
      <template v-if="activeTab === 'home'">
        <div class="flex flex-col items-center border-r border-slate-200 pr-3">
          <button @click="triggerAction('get-data')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs" title="Import data source">
            <span class="text-base mb-0.5">📥</span>
            <span class="font-medium text-[11px]">Get Data</span>
          </button>
          <span class="text-[9px] text-slate-400 mt-1 uppercase font-semibold">Data</span>
        </div>

        <div class="flex items-center gap-1 border-r border-slate-200 pr-3">
          <button
            @click="triggerAction('undo')"
            :disabled="!canUndo"
            :class="['flex flex-col items-center p-1.5 rounded text-xs', canUndo ? 'hover:bg-slate-100 text-slate-700' : 'text-slate-300 cursor-not-allowed']"
            title="Undo (Ctrl+Z)"
          >
            <span class="text-base mb-0.5">↩️</span>
            <span class="font-medium text-[11px]">Undo</span>
          </button>
          <button
            @click="triggerAction('redo')"
            :disabled="!canRedo"
            :class="['flex flex-col items-center p-1.5 rounded text-xs', canRedo ? 'hover:bg-slate-100 text-slate-700' : 'text-slate-300 cursor-not-allowed']"
            title="Redo (Ctrl+Y)"
          >
            <span class="text-base mb-0.5">↪️</span>
            <span class="font-medium text-[11px]">Redo</span>
          </button>
          <span class="text-[9px] text-slate-400 self-end uppercase font-semibold">History</span>
        </div>

        <div class="flex items-center gap-1 border-r border-slate-200 pr-3">
          <button @click="triggerAction('refresh-preview')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs" title="Refresh preview">
            <span class="text-base mb-0.5">🔄</span>
            <span class="font-medium text-[11px]">Refresh</span>
          </button>
          <button @click="triggerAction('load-query')" class="flex flex-col items-center p-1.5 rounded bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 text-xs" title="Load query">
            <span class="text-base mb-0.5">📂</span>
            <span class="font-bold text-[11px]">Load</span>
          </button>
          <button @click="triggerAction('save-query')" class="flex flex-col items-center p-1.5 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 text-xs" title="Save query">
            <span class="text-base mb-0.5">💾</span>
            <span class="font-bold text-[11px]">Save</span>
          </button>
          <button @click="triggerAction('execute-query')" class="flex flex-col items-center p-1.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 text-xs" title="Execute full query">
            <span class="text-base mb-0.5">▶️</span>
            <span class="font-bold text-[11px]">Execute</span>
          </button>
          <span class="text-[9px] text-slate-400 self-end uppercase font-semibold">Query</span>
        </div>

        <div class="flex items-center gap-1 border-r border-slate-200 pr-3">
          <button @click="triggerAction('choose-columns')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">📋</span>
            <span class="font-medium text-[11px]">Choose Columns</span>
          </button>
          <button @click="triggerAction('remove-columns')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">❌</span>
            <span class="font-medium text-[11px]">Remove Columns</span>
          </button>
          <span class="text-[9px] text-slate-400 self-end uppercase font-semibold">Columns</span>
        </div>

        <div class="flex items-center gap-1 border-r border-slate-200 pr-3">
          <button @click="triggerAction('filter-rows')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔍</span>
            <span class="font-medium text-[11px]">Filter Rows</span>
          </button>
          <button @click="triggerAction('sort-asc')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">⬆️</span>
            <span class="font-medium text-[11px]">Sort Asc</span>
          </button>
          <button @click="triggerAction('sort-desc')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">⬇️</span>
            <span class="font-medium text-[11px]">Sort Desc</span>
          </button>
          <button @click="triggerAction('group-by')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">📊</span>
            <span class="font-medium text-[11px]">Group By</span>
          </button>
          <span class="text-[9px] text-slate-400 self-end uppercase font-semibold">Reduce Rows</span>
        </div>

        <div class="flex items-center gap-1 border-r border-slate-200 pr-3">
          <button @click="triggerAction('merge-queries')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔗</span>
            <span class="font-medium text-[11px]">Merge Queries</span>
          </button>
          <button @click="triggerAction('deduplicate')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🧹</span>
            <span class="font-medium text-[11px]">Remove Duplicates</span>
          </button>
        </div>

        <div class="flex items-center gap-1">
          <button @click="triggerAction('export-python-script')" class="flex flex-col items-center p-1.5 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 text-xs" title="Export pipeline as Polars Python script">
            <span class="text-base mb-0.5">🐍</span>
            <span class="font-bold text-[11px]">Export Python</span>
          </button>
        </div>
      </template>

      <template v-if="activeTab === 'transform'">
        <div class="flex items-center gap-2 border-r border-slate-200 pr-3">
          <button @click="triggerAction('split-column')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">✂️</span>
            <span class="font-medium text-[11px]">Split Column</span>
          </button>
          <button @click="triggerAction('replace-values')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔄</span>
            <span class="font-medium text-[11px]">Replace Values</span>
          </button>
          <button @click="triggerAction('rename-column')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">✏️</span>
            <span class="font-medium text-[11px]">Rename Column</span>
          </button>
          <button @click="triggerAction('change-type')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔣</span>
            <span class="font-medium text-[11px]">Change Type</span>
          </button>
        </div>
        <div class="flex items-center gap-2 border-r border-slate-200 pr-3">
          <button @click="triggerAction('text-format-trim')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">␣</span>
            <span class="font-medium text-[11px]">Trim</span>
          </button>
          <button @click="triggerAction('text-format-upper')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔠</span>
            <span class="font-medium text-[11px]">Uppercase</span>
          </button>
          <button @click="triggerAction('text-format-lower')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔡</span>
            <span class="font-medium text-[11px]">Lowercase</span>
          </button>
        </div>
        <div class="flex items-center gap-2">
          <button @click="triggerAction('reset-steps')" class="flex flex-col items-center p-1.5 rounded bg-red-50 hover:bg-red-100 text-red-800 border border-red-200 text-xs">
            <span class="text-base mb-0.5">↺</span>
            <span class="font-bold text-[11px]">Reset Steps</span>
          </button>
        </div>
      </template>

      <template v-if="activeTab === 'add-column'">
        <div class="flex items-center gap-2 border-r border-slate-200 pr-3">
          <button @click="triggerAction('add-custom-column')" class="flex flex-col items-center p-1.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-800 border border-blue-200 text-xs">
            <span class="text-base mb-0.5">✨</span>
            <span class="font-bold text-[11px]">Custom Column</span>
          </button>
          <button @click="triggerAction('conditional-column')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔀</span>
            <span class="font-medium text-[11px]">Conditional Column</span>
          </button>
        </div>
        <div class="flex items-center gap-2">
          <button @click="triggerAction('index-column')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🔢</span>
            <span class="font-medium text-[11px]">Index Column</span>
          </button>
          <button @click="triggerAction('duplicate-column')" class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs">
            <span class="text-base mb-0.5">🧬</span>
            <span class="font-medium text-[11px]">Duplicate Column</span>
          </button>
        </div>
      </template>

      <template v-if="activeTab === 'view'">
        <div class="flex items-center gap-2 border-r border-slate-200 pr-3">
          <button @click="triggerAction('toggle-data-view')" :class="['flex flex-col items-center p-1.5 rounded text-xs', store.currentView === 'grid' ? 'bg-blue-100 text-blue-900 border border-blue-300' : 'hover:bg-slate-100 text-slate-700']">
            <span class="text-base mb-0.5">▦</span>
            <span class="font-medium text-[11px]">Data View</span>
          </button>
          <button @click="triggerAction('toggle-diagram-view')" :class="['flex flex-col items-center p-1.5 rounded text-xs', store.currentView === 'diagram' ? 'bg-blue-100 text-blue-900 border border-blue-300' : 'hover:bg-slate-100 text-slate-700']">
            <span class="text-base mb-0.5">🗺️</span>
            <span class="font-medium text-[11px]">Diagram View</span>
          </button>
          <button @click="triggerAction('toggle-profiling')" :class="['flex flex-col items-center p-1.5 rounded text-xs', store.showProfilingBar ? 'bg-blue-100 text-blue-900 border border-blue-300' : 'hover:bg-slate-100 text-slate-700']">
            <span class="text-base mb-0.5">📈</span>
            <span class="font-medium text-[11px]">Profiling</span>
          </button>
          <button @click="triggerAction('toggle-log')" :class="['flex flex-col items-center p-1.5 rounded text-xs', store.showLog ? 'bg-blue-100 text-blue-900 border border-blue-300' : 'hover:bg-slate-100 text-slate-700']">
            <span class="text-base mb-0.5">📜</span>
            <span class="font-medium text-[11px]">Console Log</span>
          </button>
        </div>
        <div class="flex items-center gap-2">
          <button @click="triggerAction('open-advanced-editor')" class="flex flex-col items-center p-1.5 rounded bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 text-xs">
            <span class="text-base mb-0.5">📜</span>
            <span class="font-bold text-[11px]">Advanced Editor</span>
          </button>
          <button @click="triggerAction('export-python-script')" class="flex flex-col items-center p-1.5 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 text-xs">
            <span class="text-base mb-0.5">🐍</span>
            <span class="font-bold text-[11px]">Export Python</span>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { useUiStore } from 'pybi-store';

export default {
  name: 'PowerQueryRibbon',
  emits: ['action'],
  data() {
    return {
      activeTab: 'home',
      tabs: [
        { id: 'home', label: 'Home' },
        { id: 'transform', label: 'Transform' },
        { id: 'add-column', label: 'Add Column' },
        { id: 'view', label: 'View' }
      ]
    };
  },
  computed: {
    store() {
      return useUiStore();
    },
    canUndo() {
      return Array.isArray(this.store.history) && this.store.history.length > 0;
    },
    canRedo() {
      return Array.isArray(this.store.future) && this.store.future.length > 0;
    }
  },
  methods: {
    triggerAction(actionName, payload = {}) {
      this.$emit('action', { action: actionName, payload });
    }
  }
};
</script>
