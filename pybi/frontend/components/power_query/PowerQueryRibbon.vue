<template>
  <div class="pq-ribbon bg-slate-100 border-b border-slate-300 select-none">
    <!-- Ribbon Tabs Header -->
    <div class="flex items-center bg-slate-200 border-b border-slate-300 text-xs font-semibold text-slate-700">
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

    <!-- Ribbon Action Toolbar Content -->
    <div class="p-2 flex items-center gap-3 overflow-x-auto min-h-[64px] bg-white">
      <!-- HOME TAB ACTIONS -->
      <template v-if="activeTab === 'home'">
        <!-- Get Data Group -->
        <div class="flex flex-col items-center border-r border-slate-200 pr-3">
          <button
            @click="triggerAction('get-data')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
            title="Import Data Source"
          >
            <span class="text-base mb-0.5">📥</span>
            <span class="font-medium text-[11px]">Get Data</span>
          </button>
          <span class="text-[9px] text-slate-400 mt-1 uppercase font-semibold">Data</span>
        </div>

        <!-- Columns Group -->
        <div class="flex items-center gap-1 border-r border-slate-200 pr-3">
          <button
            @click="triggerAction('choose-columns')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">📋</span>
            <span class="font-medium text-[11px]">Choose Columns</span>
          </button>
          <button
            @click="triggerAction('remove-columns')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">❌</span>
            <span class="font-medium text-[11px]">Remove Columns</span>
          </button>
          <span class="text-[9px] text-slate-400 self-end uppercase font-semibold">Columns</span>
        </div>

        <!-- Rows Group -->
        <div class="flex items-center gap-1 border-r border-slate-200 pr-3">
          <button
            @click="triggerAction('filter-rows')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">🔍</span>
            <span class="font-medium text-[11px]">Filter Rows</span>
          </button>
          <button
            @click="triggerAction('group-by')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">📊</span>
            <span class="font-medium text-[11px]">Group By</span>
          </button>
          <span class="text-[9px] text-slate-400 self-end uppercase font-semibold">Reduce Rows</span>
        </div>

        <!-- Combine Group -->
        <div class="flex items-center gap-1">
          <button
            @click="triggerAction('merge-queries')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">🔗</span>
            <span class="font-medium text-[11px]">Merge Queries</span>
          </button>
          <button
            @click="triggerAction('append-queries')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">➕</span>
            <span class="font-medium text-[11px]">Append Queries</span>
          </button>
        </div>
      </template>

      <!-- TRANSFORM TAB ACTIONS -->
      <template v-if="activeTab === 'transform'">
        <div class="flex items-center gap-2 border-r border-slate-200 pr-3">
          <button
            @click="triggerAction('split-column')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">✂️</span>
            <span class="font-medium text-[11px]">Split Column</span>
          </button>
          <button
            @click="triggerAction('replace-values')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">🔄</span>
            <span class="font-medium text-[11px]">Replace Values</span>
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="triggerAction('transpose')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">↕️</span>
            <span class="font-medium text-[11px]">Transpose</span>
          </button>
          <button
            @click="triggerAction('reverse-rows')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">🔃</span>
            <span class="font-medium text-[11px]">Reverse Rows</span>
          </button>
          <button
            @click="triggerAction('use-first-row-as-headers')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">🔝</span>
            <span class="font-medium text-[11px]">First Row as Header</span>
          </button>
        </div>
      </template>

      <!-- ADD COLUMN TAB ACTIONS -->
      <template v-if="activeTab === 'add-column'">
        <div class="flex items-center gap-2 border-r border-slate-200 pr-3">
          <button
            @click="triggerAction('add-custom-column')"
            class="flex flex-col items-center p-1.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-800 border border-blue-200 text-xs"
          >
            <span class="text-base mb-0.5">✨</span>
            <span class="font-bold text-[11px]">Custom Column</span>
          </button>
          <button
            @click="triggerAction('conditional-column')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">🔀</span>
            <span class="font-medium text-[11px]">Conditional Column</span>
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="triggerAction('column-from-examples')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">💡</span>
            <span class="font-medium text-[11px]">From Examples</span>
          </button>
          <button
            @click="triggerAction('index-column')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">🔢</span>
            <span class="font-medium text-[11px]">Index Column</span>
          </button>
        </div>
      </template>

      <!-- VIEW TAB ACTIONS -->
      <template v-if="activeTab === 'view'">
        <div class="flex items-center gap-2 border-r border-slate-200 pr-3">
          <button
            @click="triggerAction('toggle-data-view')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">👁️</span>
            <span class="font-medium text-[11px]">Data / Schema View</span>
          </button>
          <button
            @click="triggerAction('toggle-query-settings')"
            class="flex flex-col items-center p-1.5 rounded hover:bg-slate-100 text-slate-700 text-xs"
          >
            <span class="text-base mb-0.5">⚙️</span>
            <span class="font-medium text-[11px]">Query Settings</span>
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="triggerAction('open-advanced-editor')"
            class="flex flex-col items-center p-1.5 rounded bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 text-xs"
          >
            <span class="text-base mb-0.5">📜</span>
            <span class="font-bold text-[11px]">Advanced Editor</span>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
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
  methods: {
    triggerAction(actionName, payload = {}) {
      this.$emit('action', { action: actionName, payload });
    }
  }
};
</script>
