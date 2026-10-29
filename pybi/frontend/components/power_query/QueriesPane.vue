<template>
  <div
    :class="[
      'queries-pane flex flex-col bg-slate-50 border-r border-slate-300 transition-all duration-200 select-none h-full',
      isCollapsed ? 'w-10' : 'w-64'
    ]"
  >
    <!-- Pane Header with Collapse Toggle -->
    <div class="flex items-center justify-between p-2 bg-slate-200 border-b border-slate-300">
      <div v-if="!isCollapsed" class="flex items-center gap-1.5 font-bold text-xs text-slate-800 truncate">
        <span>🗂️</span>
        <span>Queries ({{ queriesList.length }})</span>
      </div>
      <button
        @click="isCollapsed = !isCollapsed"
        class="p-1 rounded hover:bg-slate-300 text-slate-600 focus:outline-none text-xs ml-auto"
        :title="isCollapsed ? 'Expand Queries Pane' : 'Collapse Queries Pane'"
      >
        <span v-if="isCollapsed">▶</span>
        <span v-else">◀</span>
      </button>
    </div>

    <!-- Expanded Body Content -->
    <div v-if="!isCollapsed" class="flex-grow flex flex-col p-2 overflow-y-auto gap-2">
      <!-- Search Filter -->
      <div class="relative">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search queries..."
          class="w-full px-2 py-1 text-xs border border-slate-300 rounded bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <span v-if="searchQuery" @click="searchQuery = ''" class="absolute right-2 top-1 cursor-pointer text-slate-400 text-xs">×</span>
      </div>

      <!-- Queries & Sources Tree List -->
      <div class="flex flex-col gap-1 mt-1">
        <div
          v-for="query in filteredQueries"
          :key="query.name || query"
          @click="selectQuery(query.name || query)"
          @contextmenu.prevent="openContextMenu($event, query.name || query)"
          :class="[
            'group relative flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer text-xs border transition-colors',
            selectedTable === (query.name || query)
              ? 'bg-blue-100 border-blue-400 text-blue-900 font-bold'
              : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700'
          ]"
        >
          <div class="flex items-center gap-2 truncate flex-grow">
            <span>📄</span>
            <span class="truncate">{{ query.name || query }}</span>
          </div>

          <!-- Dropdown Context Menu Trigger Button -->
          <div class="relative">
            <button
              @click.stop="toggleMenu(query.name || query)"
              class="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-slate-200 rounded text-slate-600 text-xs"
              title="Query actions"
            >
              ⋮
            </button>

            <!-- Inline Context Menu Dropdown -->
            <div
              v-if="activeContextMenu === (query.name || query)"
              class="absolute right-0 top-full mt-1 w-40 bg-white border border-slate-300 rounded shadow-lg z-30 py-1 text-xs font-normal"
            >
              <button @click.stop="handleContextAction('duplicate', query.name || query)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">📋 Duplicate</button>
              <button @click.stop="handleContextAction('reference', query.name || query)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">🔗 Reference</button>
              <button @click.stop="handleContextAction('rename', query.name || query)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">✏️ Rename</button>
              <button @click.stop="handleContextAction('move-group', query.name || query)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">📁 Move to Group</button>
              <div class="border-t border-slate-200 my-0.5"></div>
              <button @click.stop="handleContextAction('delete', query.name || query)" class="w-full text-left px-3 py-1 hover:bg-red-50 text-red-600">🗑️ Delete</button>
            </div>
          </div>
        </div>

        <div v-if="filteredQueries.length === 0" class="text-xs text-slate-400 italic p-2 text-center">
          No queries found.
        </div>
      </div>
    </div>

    <!-- Collapsed Vertical Bar -->
    <div v-else class="flex flex-col items-center py-4 gap-4 text-slate-500 text-sm">
      <span title="Queries">🗂️</span>
    </div>
  </div>
</template>

<script>
import { useUiStore } from '../../stores/uiStore.js';

export default {
  name: 'QueriesPane',
  props: {
    tables: {
      type: Array,
      default: () => []
    }
  },
  emits: ['select-query', 'action'],
  data() {
    return {
      isCollapsed: false,
      searchQuery: '',
      activeContextMenu: null
    };
  },
  computed: {
    store() {
      try {
        return useUiStore();
      } catch (e) {
        return null;
      }
    },
    selectedTable() {
      if (this.store && this.store.selectedTable) {
        return this.store.selectedTable;
      }
      return this.$props.tables.length > 0 ? (this.$props.tables[0].name || this.$props.tables[0]) : null;
    },
    queriesList() {
      if (this.$props.tables && this.$props.tables.length > 0) {
        return this.$props.tables;
      }
      if (this.store && this.store.appliedStepsByTable) {
        return Object.keys(this.store.appliedStepsByTable);
      }
      return ['sales_data.csv'];
    },
    filteredQueries() {
      if (!this.searchQuery) return thisQueriesList(this);
      const q = this.searchQuery.toLowerCase();
      return thisQueriesList(this).filter(item => {
        const name = typeof item === 'string' ? item : (item.name || '');
        return name.toLowerCase().includes(q);
      });
    }
  },
  methods: {
    selectQuery(tableName) {
      this.activeContextMenu = null;
      if (this.store && typeof this.store.setSelectedTable === 'function') {
        this.store.setSelectedTable(tableName);
      }
      this.$emit('select-query', tableName);
    },
    toggleMenu(tableName) {
      if (this.activeContextMenu === tableName) {
        this.activeContextMenu = null;
      } else {
        this.activeContextMenu = tableName;
      }
    },
    openContextMenu(event, tableName) {
      this.activeContextMenu = tableName;
    },
    handleContextAction(actionName, tableName) {
      this.activeContextMenu = null;
      this.$emit('action', { action: actionName, table: tableName });
    }
  },
  mounted() {
    document.addEventListener('click', () => {
      this.activeContextMenu = null;
    });
  }
};

function thisQueriesList(vm) {
  return vm.queriesList;
}
</script>
