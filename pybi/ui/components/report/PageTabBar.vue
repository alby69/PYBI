<template>
  <div class="page-tab-bar flex h-8 shrink-0 items-stretch border-t border-pbi-pane-border bg-pbi-ribbon text-pbi-base">
    <div class="flex min-w-0 flex-1 items-stretch overflow-x-auto overflow-y-hidden">
      <div
        v-for="(page, index) in store.layout.pages"
        :key="page.id"
        class="group/tab relative flex min-w-[120px] max-w-[220px] cursor-pointer items-center gap-1 border-r border-pbi-pane-border px-2 text-pbi-xs transition-colors"
        :class="tabClass(page)"
        :draggable="editingPageId !== page.id"
        @click="selectPage(page)"
        @dblclick.stop="startRename(page)"
        @contextmenu.prevent.stop="openContextMenu(page, $event)"
        @dragstart="onDragStart(index, $event)"
        @dragover.prevent="onDragOver(index, $event)"
        @drop.prevent="onDrop(index, $event)"
        @dragend="dragIndex = null"
      >
        <span class="shrink-0 text-[11px]">{{ page.page_type === 'Tooltip' ? '👁️' : page.is_hidden ? '👁️‍🗨️' : '📄' }}</span>

        <input
          v-if="editingPageId === page.id"
          ref="renameInput"
          v-model="renameDraft"
          class="min-w-0 flex-1 rounded border border-pbi-accent px-1 text-pbi-xs outline-none"
          @click.stop
          @keydown.enter.prevent="commitRename"
          @keydown.esc.prevent="cancelRename"
          @blur="commitRename"
        />
        <span v-else class="min-w-0 flex-1 truncate" :class="{ 'font-bold': page.id === store.layout.active_page_id, 'italic text-pbi-text-muted': page.is_hidden }" :title="page.name">
          {{ page.name }}
        </span>

        <span v-if="page.page_type === 'Tooltip'" class="rounded bg-purple-100 px-1 text-[8px] uppercase text-purple-700">Tooltip</span>
        <span v-else-if="page.page_type === 'Drillthrough'" class="rounded bg-amber-100 px-1 text-[8px] uppercase text-amber-700">Drill</span>

        <button
          v-if="page.id === store.layout.active_page_id"
          class="ml-auto hidden shrink-0 rounded px-1 text-[10px] text-pbi-text-muted hover:bg-slate-200 hover:text-pbi-text group-hover/tab:block"
          title="Opzioni pagina"
          @click.stop="openContextMenu(page, $event)"
        >⋯</button>
      </div>

      <button
        class="flex w-8 shrink-0 items-center justify-center border-r border-pbi-pane-border text-base font-bold text-pbi-text-muted hover:bg-white hover:text-pbi-accent"
        title="Nuova pagina"
        @click="addPage"
      >＋</button>
    </div>

    <div class="flex shrink-0 items-center gap-2 border-l border-pbi-pane-border px-2 text-[10px] text-pbi-text-muted">
      <span>{{ store.layout.pages.length }} pagina/e</span>
      <span class="h-3 w-px bg-pbi-pane-border"></span>
      <span>{{ store.layout.pages.filter(page => page.is_hidden).length }} nascoste</span>
    </div>

    <!-- Context menu -->
    <div
      v-if="contextMenu.open"
      ref="contextMenuRef"
      class="fixed z-[100] w-52 rounded border border-pbi-pane-border bg-white py-1 text-pbi-base text-pbi-text shadow-pbi-dropdown"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      @mousedown.stop
    >
      <button class="page-menu-item" @click="renameFromMenu"><span>✏️</span> Rinomina</button>
      <button class="page-menu-item" @click="duplicateFromMenu"><span>⧉</span> Duplica pagina</button>
      <button class="page-menu-item" @click="toggleHiddenFromMenu">
        <span>{{ contextMenu.page?.is_hidden ? '👁️' : '👁️‍🗨️' }}</span>
        {{ contextMenu.page?.is_hidden ? 'Mostra pagina' : 'Nascondi pagina' }}
      </button>
      <div class="my-1 border-t border-pbi-pane-border"></div>
      <div class="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-pbi-text-muted">Tipo pagina</div>
      <button v-for="type in pageTypes" :key="type" class="page-menu-item pl-5" @click="setPageType(type)">
        <span>{{ type === 'Standard' ? '📄' : type === 'Tooltip' ? '👁️' : '🔎' }}</span> {{ type }}
      </button>
      <div class="my-1 border-t border-pbi-pane-border"></div>
      <button class="page-menu-item text-red-600" @click="deleteFromMenu"><span>🗑</span> Elimina pagina</button>
    </div>
  </div>
</template>

<script>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useReportStore } from 'pybi-report-store';

export default {
  name: 'PageTabBar',
  setup() {
const store = useReportStore();
const dragIndex = ref(null);
const editingPageId = ref(null);
const renameDraft = ref('');
const renameInput = ref(null);
const contextMenuRef = ref(null);
const pageTypes = ['Standard', 'Tooltip', 'Drillthrough'];

const contextMenu = reactive({
  open: false,
  x: 0,
  y: 0,
  page: null,
});

function tabClass(page) {
  const active = page.id === store.layout.active_page_id;
  return {
    'bg-white text-pbi-text shadow-[inset_0_2px_0_#118dff]': active,
    'bg-pbi-ribbon text-pbi-text hover:bg-white/70': !active,
    'border-t-2 border-t-pbi-accent': active,
    'opacity-75': page.is_hidden && !active,
  };
}

function selectPage(page) {
  if (page.id !== store.layout.active_page_id) store.setActivePage(page.id);
}

function addPage() {
  const page = store.addPage();
  nextTick(() => {
    editingPageId.value = page.id;
    renameDraft.value = page.name;
    nextTick(() => renameInput.value?.[0]?.select?.() || renameInput.value?.select?.());
  });
}

function startRename(page) {
  editingPageId.value = page.id;
  renameDraft.value = page.name;
  nextTick(() => {
    const input = Array.isArray(renameInput.value) ? renameInput.value[0] : renameInput.value;
    input?.focus();
    input?.select?.();
  });
}

function commitRename() {
  if (!editingPageId.value) return;
  store.renamePage(editingPageId.value, renameDraft.value);
  editingPageId.value = null;
}

function cancelRename() {
  editingPageId.value = null;
}

function onDragStart(index, event) {
  dragIndex.value = index;
  event.dataTransfer.effectAllowed = 'move';
  try {
    event.dataTransfer.setData('text/plain', String(index));
  } catch (error) {
    // Some browsers require data to be set for dragging; ignore failures.
  }
}

function onDragOver(index, event) {
  if (dragIndex.value === null) return;
  event.dataTransfer.dropEffect = 'move';
}

function onDrop(index) {
  if (dragIndex.value === null || dragIndex.value === index) return;
  store.reorderPages(dragIndex.value, index);
  dragIndex.value = null;
}

function openContextMenu(page, event) {
  event.preventDefault();
  event.stopPropagation();
  const width = 208;
  const height = 260;
  contextMenu.page = page;
  contextMenu.x = Math.min(window.innerWidth - width - 8, Math.max(4, event.clientX));
  contextMenu.y = Math.min(window.innerHeight - height - 8, Math.max(4, event.clientY - 12));
  contextMenu.open = true;
}

function closeContextMenu(event) {
  if (contextMenuRef.value && !contextMenuRef.value.contains(event.target)) {
    contextMenu.open = false;
  }
}

function renameFromMenu() {
  const page = contextMenu.page;
  contextMenu.open = false;
  if (page) startRename(page);
}

function duplicateFromMenu() {
  const page = contextMenu.page;
  contextMenu.open = false;
  if (page) store.duplicatePage(page.id);
}

function toggleHiddenFromMenu() {
  const page = contextMenu.page;
  contextMenu.open = false;
  if (page) store.togglePageHidden(page.id);
}

function deleteFromMenu() {
  const page = contextMenu.page;
  contextMenu.open = false;
  if (!page) return;
  const confirmed = typeof window === 'undefined' ? true : window.confirm(`Eliminare la pagina "${page.name}"?`);
  if (confirmed) store.deletePage(page.id);
}

function setPageType(type) {
  const page = contextMenu.page;
  contextMenu.open = false;
  if (page) store.updatePageSettings(page.id, { page_type: type });
}

onMounted(() => document.addEventListener('mousedown', closeContextMenu));
onBeforeUnmount(() => document.removeEventListener('mousedown', closeContextMenu));

    return {
      store,
      dragIndex,
      editingPageId,
      renameDraft,
      renameInput,
      contextMenuRef,
      pageTypes,
      contextMenu,
      tabClass,
      selectPage,
      addPage,
      startRename,
      commitRename,
      cancelRename,
      onDragStart,
      onDragOver,
      onDrop,
      openContextMenu,
      renameFromMenu,
      duplicateFromMenu,
      toggleHiddenFromMenu,
      deleteFromMenu,
      setPageType,
    };
  },
};
</script>

<style scoped>
.page-menu-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  text-align: left;
  font-size: 11px;
  white-space: nowrap;
}
.page-menu-item:hover {
  background-color: #f3f2f1;
}
</style>
