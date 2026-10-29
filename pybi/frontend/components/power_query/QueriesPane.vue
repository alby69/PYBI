<template>
  <div :class="['queries-pane flex flex-col flex-nowrap shrink-0 bg-slate-50 border-r border-slate-300 transition-all duration-200 select-none h-full', isCollapsed ? 'w-10' : 'w-64']">
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
        <span v-else>◀</span>
      </button>
    </div>

    <div v-if="!isCollapsed" class="flex-grow flex flex-col p-2 overflow-y-auto gap-2">
      <div class="relative">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search queries..."
          class="w-full px-2 py-1 text-xs border border-slate-300 rounded bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <span v-if="searchQuery" @click="searchQuery = ''" class="absolute right-2 top-1 cursor-pointer text-slate-400 text-xs">×</span>
      </div>

      <button @click="createQuery" class="w-full px-2 py-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center justify-center gap-1">
        <span>＋</span><span>New Query</span>
      </button>

      <div class="flex flex-col gap-1 mt-1">
        <div v-for="group in filteredGroups" :key="group.name" class="flex flex-col">
          <button @click="toggleGroup(group.name)" class="flex items-center gap-1 px-1 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-slate-800">
            <span>{{ collapsedGroups.includes(group.name) ? '▸' : '▾' }}</span>
            <span>📁 {{ group.name }}</span>
            <span class="ml-auto font-mono text-slate-400">{{ group.queries.length }}</span>
          </button>

          <div v-if="!collapsedGroups.includes(group.name)" class="flex flex-col gap-1 pl-1">
            <div
              v-for="query in group.queries"
              :key="query.name"
              @click="selectQuery(query.name)"
              @dblclick="renameQuery(query.name)"
              @contextmenu.prevent="openContextMenu($event, query.name)"
              :class="[
                'group relative flex items-center justify-between px-2.5 py-1.5 rounded cursor-pointer text-xs border transition-colors',
                selectedTable === query.name
                  ? 'bg-blue-100 border-blue-400 text-blue-900 font-bold'
                  : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700'
              ]"
            >
              <div class="flex items-center gap-2 truncate flex-grow">
                <span>{{ query.name === selectedTable ? '📄' : '📃' }}</span>
                <span class="truncate">{{ query.name }}</span>
              </div>

              <div class="flex items-center gap-1">
                <span class="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-200 text-slate-600 font-mono" :title="`${query.steps} applied steps`">
                  {{ query.steps }}
                </span>
                <div class="relative">
                  <button @click.stop="toggleMenu(query.name)" class="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-slate-200 rounded text-slate-600 text-xs" title="Query actions">⋮</button>
                  <div v-if="activeContextMenu === query.name" class="absolute right-0 top-full mt-1 w-40 bg-white border border-slate-300 rounded shadow-lg z-30 py-1 text-xs font-normal">
                    <button @click.stop="handleContextAction('duplicate', query.name)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">📋 Duplicate</button>
                    <button @click.stop="handleContextAction('reference', query.name)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">🔗 Reference</button>
                    <button @click.stop="handleContextAction('rename', query.name)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">✏️ Rename</button>
                    <button @click.stop="handleContextAction('move-group', query.name)" class="w-full text-left px-3 py-1 hover:bg-blue-50 text-slate-700">📁 Move to Group</button>
                    <div class="border-t border-slate-200 my-0.5"></div>
                    <button @click.stop="handleContextAction('delete', query.name)" class="w-full text-left px-3 py-1 hover:bg-red-50 text-red-600">🗑️ Delete</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="filteredGroups.length === 0" class="text-xs text-slate-400 italic p-2 text-center">
          No queries found.
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center py-4 gap-4 text-slate-500 text-sm">
      <span title="Queries">🗂️</span>
    </div>
  </div>
</template>

<script>
import { useUiStore } from 'pybi-store';

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
      activeContextMenu: null,
      collapsedGroups: [],
      groupOverrides: {}
    };
  },
  computed: {
    store() {
      return useUiStore();
    },
    selectedTable() {
      return this.store.selectedTable || (this.tables.length > 0 ? this.tableName(this.tables[0]) : null);
    },
    queriesList() {
      const source = this.tables.length > 0 ? this.tables : (this.store.tables || []);
      const names = source.map(item => this.tableName(item)).filter(Boolean);
      return Array.from(new Set(names)).map(name => ({
        name,
        folder: this.groupOverrides[name] || this.groupName(name),
        steps: this.store.getStepsForTable(name).length
      }));
    },
    groups() {
      const map = new Map();
      this.queriesList.forEach(query => {
        if (!map.has(query.folder)) map.set(query.folder, []);
        map.get(query.folder).push(query);
      });
      return Array.from(map, ([name, queries]) => ({ name, queries: queries.sort((a, b) => a.name.localeCompare(b.name)) }));
    },
    filteredGroups() {
      const needle = this.searchQuery.trim().toLowerCase();
      if (!needle) return this.groups;
      return this.groups
        .map(group => ({ ...group, queries: group.queries.filter(query => query.name.toLowerCase().includes(needle)) }))
        .filter(group => group.queries.length > 0);
    }
  },
  methods: {
    tableName(table) {
      return typeof table === 'string' ? table : (table?.name || table?.table_name || null);
    },
    groupName(name) {
      if (name.startsWith('Staging')) return 'Staging';
      if (name.startsWith('Model')) return 'Model';
      return 'Queries';
    },
    selectQuery(tableName) {
      this.activeContextMenu = null;
      this.store.setSelectedTable(tableName, { force: true });
      this.$emit('select-query', tableName);
    },
    toggleGroup(name) {
      const index = this.collapsedGroups.indexOf(name);
      if (index >= 0) this.collapsedGroups.splice(index, 1);
      else this.collapsedGroups.push(name);
    },
    toggleMenu(tableName) {
      this.activeContextMenu = this.activeContextMenu === tableName ? null : tableName;
    },
    openContextMenu(event, tableName) {
      this.activeContextMenu = tableName;
    },
    createQuery() {
      const name = window.prompt('New query name', `Query${this.queriesList.length + 1}`);
      if (!name) return;
      this.store.setStepsForTable(name, []);
      this.store.setSelectedTable(name, { force: true });
      this.$emit('select-query', name);
    },
    renameQuery(tableName) {
      const newName = window.prompt('Rename query', tableName);
      if (!newName || newName === tableName) return;
      this.store.renameTable(tableName, newName);
      this.groupOverrides[newName] = this.groupOverrides[tableName] || this.groupName(tableName);
      delete this.groupOverrides[tableName];
      this.$emit('action', { action: 'renamed', table: newName });
    },
    handleContextAction(actionName, tableName) {
      this.activeContextMenu = null;
      if (actionName === 'duplicate') {
        const newName = this.store.duplicateTable(tableName);
        if (newName) this.$emit('action', { action: 'duplicated', table: newName });
      } else if (actionName === 'reference') {
        const newName = this.store.referenceTable(tableName);
        if (newName) this.$emit('action', { action: 'referenced', table: newName });
      } else if (actionName === 'rename') {
        this.renameQuery(tableName);
      } else if (actionName === 'move-group') {
        const group = window.prompt('Move query to group', this.groupOverrides[tableName] || this.groupName(tableName));
        if (group) {
          this.groupOverrides[tableName] = group;
          this.$emit('action', { action: 'moved', table: tableName, group });
        }
      } else if (actionName === 'delete') {
        if (window.confirm(`Delete query "${tableName}"?`)) {
          this.store.removeTable(tableName);
          this.$emit('action', { action: 'deleted', table: tableName });
        }
      }
    }
  },
  mounted() {
    document.addEventListener('click', () => {
      this.activeContextMenu = null;
    });
  }
};
</script>
