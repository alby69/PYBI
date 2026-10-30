import { reactive } from 'vue';

function defineStore(_id, options) {
  const store = reactive(options.state());
  Object.entries(options.getters || {}).forEach(([key, getter]) => {
    Object.defineProperty(store, key, {
      enumerable: true,
      configurable: true,
      get() { return getter.call(this, store); },
    });
  });
  Object.assign(store, options.actions || {});
  return () => store;
}

const DEFAULT_COLORS = ['#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7', '#744EC2', '#D9B200', '#D64550'];

const VISUAL_LABELS = {
  bar_chart: 'Istogramma a barre',
  column_chart: 'Istogramma a colonne',
  stacked_bar_chart: 'Barre in pila',
  stacked_column_100: 'Colonne 100% in pila',
  line_chart: 'Grafico a linee',
  area_chart: 'Grafico ad area',
  combo_chart: 'Linee e colonne',
  pie_chart: 'Grafico a torta',
  donut_chart: 'Grafico ad anello',
  treemap: 'Treemap',
  scatter_chart: 'Grafico a dispersione',
  table: 'Tabella',
  matrix: 'Matrice',
  card: 'Scheda',
  multi_row_card: 'Scheda a più righe',
  kpi: 'KPI',
  gauge: 'Indicatore',
  slicer: 'Slicer',
  text: 'Casella di testo',
  shape: 'Forma',
  image: 'Immagine',
};

function uid(prefix) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

function clone(value) {
  return value === undefined ? value : JSON.parse(JSON.stringify(value));
}

function deepMerge(target, patch) {
  const output = { ...(target || {}) };
  Object.entries(patch || {}).forEach(([key, value]) => {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      output[key] = deepMerge(output[key] || {}, value);
    } else {
      output[key] = value;
    }
  });
  return output;
}

function defaultBuckets(type) {
  const map = {
    table: ['values'],
    matrix: ['rows', 'columns', 'values'],
    card: ['values'],
    multi_row_card: ['values'],
    kpi: ['values'],
    gauge: ['values'],
    slicer: ['values'],
    scatter_chart: ['x_axis', 'y_axis', 'legend'],
    combo_chart: ['x_axis', 'y_axis', 'secondary_y_axis'],
  };
  return (map[type] || ['x_axis', 'y_axis', 'legend']).reduce((acc, bucket) => {
    acc[bucket] = [];
    return acc;
  }, {});
}

function defaultProperties(type, title) {
  return {
    title: title || VISUAL_LABELS[type] || 'Visual',
    titleVisible: true,
    titleFontSize: 14,
    titleColor: '#252423',
    titleAlign: 'left',
    titleBackground: null,
    background: '#ffffff',
    backgroundTransparency: 0,
    border: { show: false, color: '#d2d0ce', radius: 4, width: 1 },
    shadow: { show: false, color: '#000000', blur: 8, angle: 45, distance: 2, transparency: 80 },
    dataColors: [...DEFAULT_COLORS],
    dataLabels: { show: false, position: 'auto', units: 'none', decimals: 0, color: '#252423', fontSize: 10 },
    legend: { show: true, position: 'bottom', title: '', color: '#605e5c', fontSize: 10 },
    xAxis: { show: true, title: '', color: '#605e5c', fontSize: 10, logScale: false, interval: null },
    yAxis: { show: true, title: '', color: '#605e5c', fontSize: 10, logScale: false, interval: null },
    gridlines: { show: true, horizontal: true, vertical: false, color: '#e1dfdd', stroke: 'solid', width: 1 },
    header: { show: true, icons: ['focus', 'filters', 'menu'] },
    sort_by: null,
    sort_dir: 'DESC',
    showAs: 'none',
    conditionalFormatting: null,
  };
}

function defaultSize(type) {
  if (type === 'card' || type === 'kpi' || type === 'gauge') return { width: 280, height: 180 };
  if (type === 'slicer') return { width: 260, height: 300 };
  if (type === 'table' || type === 'matrix') return { width: 640, height: 360 };
  return { width: 480, height: 300 };
}

function normaliseField(field, tableName = '') {
  if (!field) return null;
  if (typeof field === 'string') {
    return {
      table: tableName,
      column: field,
      name: field,
      kind: 'column',
      data_type: 'string',
      aggregation: 'SUM',
      display_name: field,
    };
  }
  const column = field.column || field.name || '';
  const kind = field.kind || (field.is_measure ? 'measure' : 'column');
  return {
    ...clone(field),
    table: field.table || field.table_name || tableName,
    column,
    name: field.name || column,
    kind,
    data_type: field.data_type || (kind === 'measure' ? 'number' : 'string'),
    aggregation: field.aggregation || field.agg_func || (kind === 'measure' ? 'SUM' : 'SUM'),
    display_name: field.display_name || field.label || field.name || column,
  };
}

function makeDefaultLayout(projectId) {
  const pageId = uid('page');
  return {
    project_id: projectId,
    active_page_id: pageId,
    pages: [
      {
        id: pageId,
        name: 'Pagina 1',
        is_hidden: false,
        page_type: 'Standard',
        width: 1280,
        height: 720,
        visuals: [],
        page_filters: [],
      },
    ],
    report_filters: [],
    theme: 'PowerBI_Classic',
  };
}

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : payload;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return payload;
}

export const useReportStore = defineStore('report', {
  state: () => ({
    projectId: 'default',
    layout: makeDefaultLayout('default'),
    selectedVisualIds: [],
    primarySelectedId: null,
    focusedVisualId: null,
    seeDataVisualId: null,
    hoveredVisualId: null,
    visualData: {},
    visualLoading: {},
    tables: [],
    activeDataTable: '',
    tableData: { columns: [], rows: [], total_rows: 0, filtered_rows: 0 },
    tableLoading: false,
    tableSort: { by: null, dir: 'asc' },
    tableSearch: '',
    crossFilters: [],
    layoutLoading: false,
    isSaving: false,
    isDirty: false,
    lastSavedAt: null,
    zoom: 1,
    gridSize: 8,
    snapToGrid: true,
    showSmartGuides: true,
    guides: [],
    clipboard: null,
    searchFilter: '',
    activeView: 'report',
    activePanel: 'visuals',
    panelOpen: { filters: true, visuals: true, data: true },
    messages: [],
  }),

  getters: {
    activePage(state) {
      return state.layout.pages.find(page => page.id === state.layout.active_page_id) || state.layout.pages[0] || null;
    },
    activePageIndex(state) {
      return Math.max(0, state.layout.pages.findIndex(page => page.id === state.layout.active_page_id));
    },
    pageCount(state) {
      return state.layout.pages.length;
    },
    visiblePages(state) {
      return state.layout.pages.filter(page => !page.is_hidden);
    },
    selectedVisual(state) {
      if (!state.primarySelectedId) return null;
      const page = state.layout.pages.find(p => p.id === state.layout.active_page_id);
      return (page?.visuals || []).find(visual => visual.id === state.primarySelectedId) || null;
    },
    selectedVisuals(state) {
      const page = state.layout.pages.find(p => p.id === state.layout.active_page_id);
      const ids = new Set(state.selectedVisualIds);
      return (page?.visuals || []).filter(visual => ids.has(visual.id));
    },
    focusedVisual(state) {
      if (!state.focusedVisualId) return null;
      const page = state.layout.pages.find(p => p.id === state.layout.active_page_id);
      return (page?.visuals || []).find(visual => visual.id === state.focusedVisualId) || null;
    },
    seeDataVisual(state) {
      if (!state.seeDataVisualId) return null;
      const page = state.layout.pages.find(p => p.id === state.layout.active_page_id);
      return (page?.visuals || []).find(visual => visual.id === state.seeDataVisualId) || null;
    },
    pageSizeLabel(state) {
      const page = this.activePage;
      return page ? `${page.width} x ${page.height}` : '1280 x 720';
    },
    activeTableMeta(state) {
      return state.tables.find(table => table.name === state.activeDataTable) || state.tables[0] || null;
    },
    filteredTables(state) {
      const query = (state.searchFilter || '').toLowerCase().trim();
      if (!query) return state.tables;
      return state.tables.filter(table => {
        const tableMatch = (table.name || '').toLowerCase().includes(query);
        const columnMatch = (table.columns || []).some(column => (column.name || '').toLowerCase().includes(query));
        const measureMatch = (table.measures || []).some(measure => (measure.name || '').toLowerCase().includes(query));
        return tableMatch || columnMatch || measureMatch;
      });
    },
    hasSelection(state) {
      return state.selectedVisualIds.length > 0;
    },
    canUndo() {
      return false;
    },
  },

  actions: {
    visualLabel(type) {
      return VISUAL_LABELS[type] || type || 'Visual';
    },

    markDirty() {
      this.isDirty = true;
    },

    notify(message, level = 'info') {
      this.messages.push({ id: uid('msg'), message, level, time: new Date().toLocaleTimeString() });
      if (this.messages.length > 50) this.messages.shift();
    },

    getPage(pageId = null) {
      const target = pageId || this.layout.active_page_id;
      return this.layout.pages.find(page => page.id === target) || this.layout.pages[0] || null;
    },

    getVisual(visualId, pageId = null) {
      const page = this.getPage(pageId);
      return (page?.visuals || []).find(visual => visual.id === visualId) || null;
    },

    async fetchLayout(projectId = null) {
      if (projectId) this.projectId = projectId;
      this.layoutLoading = true;
      try {
        const payload = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/report`);
        this.layout = payload && payload.pages ? payload : makeDefaultLayout(this.projectId);
      } catch (error) {
        this.layout = makeDefaultLayout(this.projectId);
        this.notify(`Report layout non disponibile: ${error.message}`, 'warning');
      } finally {
        if (!this.layout.pages || !this.layout.pages.length) this.layout = makeDefaultLayout(this.projectId);
        if (!this.layout.pages.some(page => page.id === this.layout.active_page_id)) {
          this.layout.active_page_id = this.layout.pages[0].id;
        }
        this.layoutLoading = false;
        this.isDirty = false;
        await this.fetchTables();
        await this.fetchAllVisualData();
      }
    },

    async saveLayout() {
      this.isSaving = true;
      try {
        const payload = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/report`, {
          method: 'PUT',
          body: JSON.stringify(this.layout),
        });
        this.layout = payload;
        this.isDirty = false;
        this.lastSavedAt = new Date().toISOString();
        this.notify('Report salvato', 'success');
        return payload;
      } catch (error) {
        this.notify(`Errore salvataggio report: ${error.message}`, 'error');
        throw error;
      } finally {
        this.isSaving = false;
      }
    },

    setActiveView(view) {
      this.activeView = view;
    },

    setActivePanel(panel) {
      this.activePanel = panel;
      if (panel in this.panelOpen) this.panelOpen[panel] = true;
    },

    togglePanel(panel) {
      if (panel in this.panelOpen) this.panelOpen[panel] = !this.panelOpen[panel];
    },

    setZoom(value) {
      this.zoom = Math.min(3, Math.max(0.2, Number(value) || 1));
    },

    zoomIn() {
      this.setZoom(this.zoom + 0.1);
    },

    zoomOut() {
      this.setZoom(this.zoom - 0.1);
    },

    resetZoom() {
      this.setZoom(1);
    },

    setSearchFilter(value) {
      this.searchFilter = value || '';
    },

    // -----------------------------------------------------------------
    // Pages
    // -----------------------------------------------------------------
    setActivePage(pageId) {
      if (!pageId || pageId === this.layout.active_page_id) return;
      if (!this.layout.pages.some(page => page.id === pageId)) return;
      this.layout.active_page_id = pageId;
      this.layout.pages = [...this.layout.pages];
      this.clearSelection();
      this.focusedVisualId = null;
      this.seeDataVisualId = null;
      this.markDirty();
      this.fetchAllVisualData();
    },

    nextPage() {
      const index = this.activePageIndex;
      const next = this.layout.pages[(index + 1) % this.layout.pages.length];
      if (next) this.setActivePage(next.id);
    },

    previousPage() {
      const index = this.activePageIndex;
      const prev = this.layout.pages[(index - 1 + this.layout.pages.length) % this.layout.pages.length];
      if (prev) this.setActivePage(prev.id);
    },

    addPage(name = null) {
      const number = this.layout.pages.length + 1;
      const page = {
        id: uid('page'),
        name: name || `Pagina ${number}`,
        is_hidden: false,
        page_type: 'Standard',
        width: 1280,
        height: 720,
        visuals: [],
        page_filters: [],
      };
      this.layout.pages.push(page);
      this.layout.active_page_id = page.id;
      this.clearSelection();
      this.markDirty();
      return page;
    },

    renamePage(pageId, name) {
      const page = this.getPage(pageId);
      if (!page) return;
      page.name = (name || '').trim() || page.name;
      this.layout.pages = [...this.layout.pages];
      this.markDirty();
    },

    duplicatePage(pageId) {
      const source = this.getPage(pageId);
      if (!source) return null;
      const clonePage = clone(source);
      clonePage.id = uid('page');
      clonePage.name = `${source.name} (copia)`;
      clonePage.visuals = (clonePage.visuals || []).map(visual => {
        const copy = clone(visual);
        copy.id = uid('vis');
        return copy;
      });
      const index = this.layout.pages.findIndex(page => page.id === pageId);
      this.layout.pages.splice(index + 1, 0, clonePage);
      this.layout.active_page_id = clonePage.id;
      this.clearSelection();
      this.markDirty();
      this.fetchAllVisualData();
      return clonePage;
    },

    deletePage(pageId) {
      const index = this.layout.pages.findIndex(page => page.id === pageId);
      if (index < 0) return;
      this.layout.pages.splice(index, 1);
      if (!this.layout.pages.length) {
        const page = makeDefaultLayout(this.projectId).pages[0];
        this.layout.pages.push(page);
      }
      if (!this.layout.pages.some(page => page.id === this.layout.active_page_id)) {
        const fallback = this.layout.pages[Math.max(0, Math.min(index, this.layout.pages.length - 1))];
        this.layout.active_page_id = fallback.id;
      }
      this.clearSelection();
      this.markDirty();
      this.fetchAllVisualData();
    },

    togglePageHidden(pageId) {
      const page = this.getPage(pageId);
      if (!page) return;
      page.is_hidden = !page.is_hidden;
      this.layout.pages = [...this.layout.pages];
      this.markDirty();
    },

    reorderPages(fromIndex, toIndex) {
      if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
      if (fromIndex >= this.layout.pages.length || toIndex >= this.layout.pages.length) return;
      const [moved] = this.layout.pages.splice(fromIndex, 1);
      this.layout.pages.splice(toIndex, 0, moved);
      this.layout.pages = [...this.layout.pages];
      this.markDirty();
    },

    updatePageSettings(pageId, patch) {
      const page = this.getPage(pageId);
      if (!page) return;
      Object.assign(page, patch);
      this.layout.pages = [...this.layout.pages];
      this.markDirty();
    },

    setPageSize(pageId, preset) {
      const sizes = { '16:9': [1280, 720], '4:3': [960, 720], tooltip: [320, 240] };
      const page = this.getPage(pageId);
      if (!page) return;
      if (preset === 'custom') return;
      const size = sizes[preset] || sizes['16:9'];
      page.width = size[0];
      page.height = size[1];
      this.markDirty();
    },

    // -----------------------------------------------------------------
    // Visuals
    // -----------------------------------------------------------------
    selectVisual(visualId, additive = false) {
      if (!visualId) {
        this.clearSelection();
        return;
      }
      if (additive) {
        const index = this.selectedVisualIds.indexOf(visualId);
        if (index >= 0) {
          this.selectedVisualIds.splice(index, 1);
          if (this.primarySelectedId === visualId) {
            this.primarySelectedId = this.selectedVisualIds[this.selectedVisualIds.length - 1] || null;
          }
        } else {
          this.selectedVisualIds.push(visualId);
          this.primarySelectedId = visualId;
        }
      } else {
        this.selectedVisualIds = [visualId];
        this.primarySelectedId = visualId;
      }
    },

    clearSelection() {
      this.selectedVisualIds = [];
      this.primarySelectedId = null;
    },

    selectAllVisuals() {
      const page = this.activePage;
      if (!page) return;
      this.selectedVisualIds = page.visuals.map(visual => visual.id);
      this.primarySelectedId = this.selectedVisualIds[this.selectedVisualIds.length - 1] || null;
    },

    setFocusedVisual(visualId) {
      this.focusedVisualId = visualId;
      if (visualId) this.selectVisual(visualId);
    },

    setSeeDataVisual(visualId) {
      this.seeDataVisualId = visualId;
      if (visualId) this.selectVisual(visualId);
    },

    addVisual(type = 'bar_chart', options = {}) {
      const page = this.activePage;
      if (!page) return null;
      const size = defaultSize(type);
      const offset = (page.visuals.length % 8) * 24;
      const visual = {
        id: uid('vis'),
        type,
        title: options.title || this.visualLabel(type),
        position: {
          x: options.x ?? 40 + offset,
          y: options.y ?? 40 + offset,
          width: options.width ?? size.width,
          height: options.height ?? size.height,
          z_index: (page.visuals.reduce((max, item) => Math.max(max, item.position?.z_index || 1), 0) || 1) + 1,
        },
        data_buckets: options.data_buckets || defaultBuckets(type),
        properties: deepMerge(defaultProperties(type, options.title || this.visualLabel(type)), options.properties || {}),
        filters: options.filters || [],
      };
      if (options.field) {
        const bucket = type === 'table' ? 'values' : type === 'card' || type === 'kpi' || type === 'gauge' ? 'values' : 'y_axis';
        visual.data_buckets[bucket] = [normaliseField(options.field)];
      }
      page.visuals.push(visual);
      this.selectVisual(visual.id);
      this.markDirty();
      this.fetchVisualData(visual);
      return visual;
    },

    addVisualFromField(field, type = null) {
      const visualType = type || 'bar_chart';
      return this.addVisual(visualType, { field });
    },

    updateVisual(visualId, patch) {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      Object.assign(visual, clone(patch));
      this.markDirty();
      if (patch.data_buckets || patch.properties) this.fetchVisualData(visual);
    },

    updateVisualPosition(visualId, position) {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      visual.position = { ...visual.position, ...position };
      this.markDirty();
    },

    updateVisualProperties(visualId, patch) {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      visual.properties = deepMerge(visual.properties, patch);
      this.markDirty();
      if (patch.dataColors || patch.sort_by || patch.sort_dir || patch.showAs) this.fetchVisualData(visual);
    },

    setVisualType(visualId, type) {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      visual.type = type;
      visual.data_buckets = deepMerge(defaultBuckets(type), visual.data_buckets || {});
      if (!visual.properties?.title || visual.properties.title === visual.title || visual.properties.title === this.visualLabel(visual.type)) {
        visual.properties = deepMerge(defaultProperties(type, this.visualLabel(type)), visual.properties || {});
      }
      this.markDirty();
      this.fetchVisualData(visual);
    },

    setVisualTitle(visualId, title) {
      this.updateVisualProperties(visualId, { title });
    },

    removeVisual(visualId) {
      const page = this.getPage();
      if (!page) return;
      page.visuals = page.visuals.filter(visual => visual.id !== visualId);
      this.selectedVisualIds = this.selectedVisualIds.filter(id => id !== visualId);
      if (this.primarySelectedId === visualId) this.primarySelectedId = this.selectedVisualIds[0] || null;
      if (this.focusedVisualId === visualId) this.focusedVisualId = null;
      if (this.seeDataVisualId === visualId) this.seeDataVisualId = null;
      delete this.visualData[visualId];
      this.markDirty();
    },

    removeSelectedVisuals() {
      [...this.selectedVisualIds].forEach(visualId => this.removeVisual(visualId));
    },

    duplicateVisual(visualId) {
      const visual = this.getVisual(visualId);
      const page = this.getPage();
      if (!visual || !page) return null;
      const copy = clone(visual);
      copy.id = uid('vis');
      copy.title = `${visual.title || this.visualLabel(visual.type)} (copia)`;
      copy.properties = { ...(copy.properties || {}), title: copy.title };
      copy.position.x = Math.min(page.width - 80, (visual.position?.x || 0) + 24);
      copy.position.y = Math.min(page.height - 80, (visual.position?.y || 0) + 24);
      page.visuals.push(copy);
      this.selectVisual(copy.id);
      this.markDirty();
      this.fetchVisualData(copy);
      return copy;
    },

    bringToFront(visualId) {
      const page = this.getPage();
      const visual = this.getVisual(visualId);
      if (!page || !visual) return;
      const maxZ = page.visuals.reduce((max, item) => Math.max(max, item.position?.z_index || 1), 0);
      visual.position.z_index = maxZ + 1;
      this.markDirty();
    },

    sendToBack(visualId) {
      const page = this.getPage();
      const visual = this.getVisual(visualId);
      if (!page || !visual) return;
      const minZ = page.visuals.reduce((min, item) => Math.min(min, item.position?.z_index || 1), Infinity);
      visual.position.z_index = Math.max(1, (Number.isFinite(minZ) ? minZ : 1) - 1);
      this.markDirty();
    },

    setSort(visualId, sortBy, sortDir = 'ASC') {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      visual.properties.sort_by = sortBy;
      visual.properties.sort_dir = String(sortDir).toUpperCase();
      this.markDirty();
      this.fetchVisualData(visual);
    },

    getBucketFields(visualId, bucket) {
      const visual = this.getVisual(visualId);
      if (!visual) return [];
      const value = visual.data_buckets?.[bucket];
      if (!value) return [];
      return Array.isArray(value) ? value : [value];
    },

    addFieldToBucket(visualId, bucket, field, atIndex = null) {
      const visual = this.getVisual(visualId);
      if (!visual || !field) return;
      const normalised = normaliseField(field);
      if (!visual.data_buckets) visual.data_buckets = {};
      const current = visual.data_buckets[bucket];
      const list = Array.isArray(current) ? current : current ? [current] : [];
      if (list.some(item => normaliseField(item).column === normalised.column && normaliseField(item).table === normalised.table)) return;
      if (atIndex === null || atIndex === undefined || atIndex > list.length) list.push(normalised);
      else list.splice(Math.max(0, atIndex), 0, normalised);
      visual.data_buckets[bucket] = list;
      if (!visual.properties?.table_name && normalised.table) {
        visual.properties = { ...(visual.properties || {}), table_name: normalised.table };
      }
      this.markDirty();
      this.fetchVisualData(visual);
    },

    removeFieldFromBucket(visualId, bucket, index) {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      const current = visual.data_buckets?.[bucket];
      const list = Array.isArray(current) ? current : current ? [current] : [];
      list.splice(index, 1);
      visual.data_buckets[bucket] = list;
      this.markDirty();
      this.fetchVisualData(visual);
    },

    updateBucketField(visualId, bucket, index, patch) {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      const current = visual.data_buckets?.[bucket];
      const list = Array.isArray(current) ? current : current ? [current] : [];
      if (!list[index]) return;
      list[index] = deepMerge(normaliseField(list[index]), patch);
      visual.data_buckets[bucket] = list;
      this.markDirty();
      this.fetchVisualData(visual);
    },

    reorderBucketFields(visualId, bucket, fromIndex, toIndex) {
      const visual = this.getVisual(visualId);
      if (!visual) return;
      const current = visual.data_buckets?.[bucket];
      const list = Array.isArray(current) ? [...current] : current ? [current] : [];
      if (fromIndex < 0 || toIndex < 0 || fromIndex >= list.length || toIndex >= list.length) return;
      const [moved] = list.splice(fromIndex, 1);
      list.splice(toIndex, 0, moved);
      visual.data_buckets[bucket] = list;
      this.markDirty();
      this.fetchVisualData(visual);
    },

    // -----------------------------------------------------------------
    // Filters (visual / page / report)
    // -----------------------------------------------------------------
    getFilterList(scope = 'page', visualId = null) {
      if (scope === 'visual') {
        const visual = this.getVisual(visualId || this.primarySelectedId);
        return visual?.filters || [];
      }
      if (scope === 'report') return this.layout.report_filters || [];
      return this.activePage?.page_filters || [];
    },

    setFilterList(scope = 'page', filters = [], visualId = null) {
      if (scope === 'visual') {
        const visual = this.getVisual(visualId || this.primarySelectedId);
        if (visual) visual.filters = filters;
      } else if (scope === 'report') {
        this.layout.report_filters = filters;
      } else if (this.activePage) {
        this.activePage.page_filters = filters;
      }
      this.markDirty();
      this.fetchAllVisualData();
    },

    addFilter(scope = 'page', filter = null, visualId = null) {
      const newFilter = {
        id: uid('filter'),
        title: '',
        field: null,
        mode: 'basic',
        values: [],
        value: null,
        operator: 'eq',
        conditions: [{ operator: 'eq', value: '', value2: '' }],
        logic: 'AND',
        top_n: 5,
        top_direction: 'top',
        by: null,
        is_locked: false,
        is_hidden: false,
        is_active: true,
        ...(filter || {}),
      };
      const list = [...this.getFilterList(scope, visualId), newFilter];
      this.setFilterList(scope, list, visualId);
      return newFilter;
    },

    updateFilter(scope, filterId, patch, visualId = null) {
      const list = this.getFilterList(scope, visualId).map(filter => (
        filter.id === filterId ? deepMerge(filter, patch) : filter
      ));
      this.setFilterList(scope, list, visualId);
    },

    removeFilter(scope, filterId, visualId = null) {
      const list = this.getFilterList(scope, visualId).filter(filter => filter.id !== filterId);
      this.setFilterList(scope, list, visualId);
    },

    resetFilter(scope, filterId, visualId = null) {
      this.updateFilter(scope, filterId, {
        values: [],
        value: null,
        conditions: [{ operator: 'eq', value: '', value2: '' }],
        is_active: true,
      }, visualId);
    },

    toggleFilterLock(scope, filterId, visualId = null) {
      const filter = this.getFilterList(scope, visualId).find(item => item.id === filterId);
      if (filter) this.updateFilter(scope, filterId, { is_locked: !filter.is_locked }, visualId);
    },

    toggleFilterHidden(scope, filterId, visualId = null) {
      const filter = this.getFilterList(scope, visualId).find(item => item.id === filterId);
      if (filter) this.updateFilter(scope, filterId, { is_hidden: !filter.is_hidden }, visualId);
    },

    filtersForVisual(visual) {
      const visible = list => (list || []).filter(filter => !filter.disabled && filter.is_active !== false);
      return [
        ...visible(visual?.filters || []),
        ...visible(this.activePage?.page_filters || []),
        ...visible(this.layout.report_filters || []),
        ...visible(this.crossFilters || []),
      ];
    },

    // -----------------------------------------------------------------
    // Data loading
    // -----------------------------------------------------------------
    async fetchTables() {
      try {
        const tables = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/report/tables`);
        this.tables = Array.isArray(tables) ? tables : [];
        if (!this.activeDataTable && this.tables.length) {
          this.activeDataTable = this.tables[0].name;
        }
      } catch (error) {
        this.tables = [];
      }
    },

    async fetchTableData(options = {}) {
      const table = options.table || this.activeDataTable;
      if (!table) return;
      this.activeDataTable = table;
      this.tableLoading = true;
      try {
        const params = new URLSearchParams({
          limit: String(options.limit || 5000),
          offset: String(options.offset || 0),
          sort_dir: (options.sortDir || this.tableSort.dir || 'asc').toLowerCase(),
        });
        const sortBy = options.sortBy ?? this.tableSort.by;
        const search = options.search ?? this.tableSearch;
        if (sortBy) params.set('sort_by', sortBy);
        if (search) params.set('search', search);
        const payload = await jsonRequest(
          `/api/v1/projects/${encodeURIComponent(this.projectId)}/report/tables/${encodeURIComponent(table)}/data?${params.toString()}`
        );
        this.tableData = payload;
      } catch (error) {
        this.tableData = { columns: [], rows: [], total_rows: 0, filtered_rows: 0, error: error.message };
        this.notify(`Impossibile caricare la tabella ${table}: ${error.message}`, 'error');
      } finally {
        this.tableLoading = false;
      }
    },

    async setActiveDataTable(tableName) {
      if (!tableName) return;
      this.activeDataTable = tableName;
      this.tableSort = { by: null, dir: 'asc' };
      this.tableSearch = '';
      await this.fetchTableData({ table: tableName });
    },

    async loadMoreTableData(limit = 2000) {
      const table = this.activeDataTable;
      if (!table) return;
      const offset = this.tableData.rows?.length || 0;
      const available = Number(this.tableData.filtered_rows || 0);
      if (available && offset >= available) return;
      this.tableLoading = true;
      try {
        const params = new URLSearchParams({
          limit: String(limit),
          offset: String(offset),
          sort_dir: (this.tableSort.dir || 'asc').toLowerCase(),
        });
        if (this.tableSort.by) params.set('sort_by', this.tableSort.by);
        if (this.tableSearch) params.set('search', this.tableSearch);
        const payload = await jsonRequest(
          `/api/v1/projects/${encodeURIComponent(this.projectId)}/report/tables/${encodeURIComponent(table)}/data?${params.toString()}`
        );
        this.tableData = {
          ...payload,
          rows: [...(this.tableData.rows || []), ...(payload.rows || [])],
        };
      } catch (error) {
        this.notify(`Impossibile caricare altre righe: ${error.message}`, 'error');
      } finally {
        this.tableLoading = false;
      }
    },

    async sortTable(column, direction = null) {
      const nextDirection = direction || (this.tableSort.by === column && this.tableSort.dir === 'asc' ? 'desc' : 'asc');
      this.tableSort = { by: column, dir: nextDirection };
      await this.fetchTableData({ sortBy: column, sortDir: nextDirection });
    },

    async searchTable(value) {
      this.tableSearch = value || '';
      await this.fetchTableData({ search: this.tableSearch });
    },

    async fetchDistinctValues(tableName, column, search = '') {
      if (!tableName || !column) return [];
      try {
        const params = new URLSearchParams({ column, limit: '500' });
        if (search) params.set('search', search);
        return await jsonRequest(
          `/api/v1/projects/${encodeURIComponent(this.projectId)}/report/tables/${encodeURIComponent(tableName)}/values?${params.toString()}`
        );
      } catch (error) {
        return [];
      }
    },

    async fetchVisualData(visualOrId) {
      const visual = typeof visualOrId === 'string' ? this.getVisual(visualOrId) : visualOrId;
      if (!visual) return;
      const filters = this.filtersForVisual(visual);
      this.visualLoading[visual.id] = true;
      try {
        const payload = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/report/visual-data`, {
          method: 'POST',
          body: JSON.stringify({ widget: clone(visual), filters: clone(filters) }),
        });
        this.visualData[visual.id] = payload;
      } catch (error) {
        this.visualData[visual.id] = { columns: [], rows: [], row_count: 0, error: error.message };
      } finally {
        this.visualLoading[visual.id] = false;
      }
    },

    async fetchAllVisualData() {
      const page = this.activePage;
      if (!page) return;
      await Promise.all((page.visuals || []).map(visual => this.fetchVisualData(visual)));
    },

    visualRows(visualId) {
      return this.visualData[visualId]?.rows || [];
    },

    async exportVisualData(visualOrId, format = 'csv') {
      const visual = typeof visualOrId === 'string' ? this.getVisual(visualOrId) : visualOrId;
      if (!visual) return;
      const data = this.visualData[visual.id] || {};
      const columns = data.columns || [];
      const rows = data.rows || [];
      const fileBase = (visual.title || 'report_visual').replace(/[^A-Za-z0-9_-]+/g, '_');
      try {
        const response = await fetch(`/api/v1/projects/${encodeURIComponent(this.projectId)}/report/export`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ columns, rows, format, filename: fileBase }),
        });
        if (!response.ok) throw new Error(`Export failed (${response.status})`);
        const blob = await response.blob();
        if (typeof document !== 'undefined') {
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = `${fileBase}.${format === 'xlsx' ? 'xlsx' : 'csv'}`;
          document.body.appendChild(anchor);
          anchor.click();
          document.body.removeChild(anchor);
          URL.revokeObjectURL(url);
        }
        this.notify(`Esportazione ${format.toUpperCase()} completata`, 'success');
      } catch (error) {
        this.notify(`Errore esportazione: ${error.message}`, 'error');
      }
    },

    // -----------------------------------------------------------------
    // Semantic model editing (Data Pane)
    // -----------------------------------------------------------------
    async saveMeasure(measure) {
      const payload = await jsonRequest(
        `/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic/measures`,
        { method: 'POST', body: JSON.stringify(measure) }
      );
      await this.fetchTables();
      this.notify(`Misura "${payload.name}" salvata`, 'success');
      return payload;
    },

    async createCalculatedColumn(tableName, column) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      const table = (model.tables || []).find(item => item.name === tableName);
      if (!table) throw new Error(`Table '${tableName}' not found`);
      table.columns = [...(table.columns || []), column];
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
      this.notify(`Colonna calcolata "${column.name}" creata`, 'success');
      return column;
    },

    async renameTable(tableName, newName) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      const table = (model.tables || []).find(item => item.name === tableName);
      if (!table) return;
      table.name = newName;
      (table.measures || []).forEach(measure => { measure.table_name = newName; });
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
    },

    async hideTable(tableName, hidden = true) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      const table = (model.tables || []).find(item => item.name === tableName);
      if (!table) return;
      table.is_hidden = hidden;
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
    },

    async renameColumn(tableName, columnName, newName) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      const table = (model.tables || []).find(item => item.name === tableName);
      const column = (table?.columns || []).find(item => item.name === columnName);
      if (!column) return;
      column.name = newName;
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
    },

    async hideColumn(tableName, columnName, hidden = true) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      const table = (model.tables || []).find(item => item.name === tableName);
      const column = (table?.columns || []).find(item => item.name === columnName);
      if (!column) return;
      column.is_hidden = hidden;
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
    },

    async renameMeasure(tableName, measureName, newName) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      const measure = (model.measures || []).find(
        item => item.table_name === tableName && (item.name === measureName || item.id === measureName)
      );
      if (!measure) return;
      measure.name = newName;
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
    },

    async hideMeasure(tableName, measureName, hidden = true) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      const measure = (model.measures || []).find(
        item => item.table_name === tableName && (item.name === measureName || item.id === measureName)
      );
      if (!measure) return;
      measure.is_hidden = hidden;
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
    },

    async deleteMeasure(tableName, measureName) {
      const model = await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`);
      model.measures = (model.measures || []).filter(
        item => !(item.table_name === tableName && (item.name === measureName || item.id === measureName))
      );
      (model.tables || []).forEach(table => {
        if (table.name === tableName) {
          table.measures = (table.measures || []).filter(
            item => !(item.name === measureName || item.id === measureName)
          );
        }
      });
      await jsonRequest(`/api/v1/projects/${encodeURIComponent(this.projectId)}/semantic`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
      await this.fetchTables();
    },

    fieldFromModel(field, tableName) {
      return normaliseField(field, tableName);
    },

    fieldDragPayload(field, tableName) {
      return JSON.stringify(normaliseField(field, tableName));
    },
  },
});

export { DEFAULT_COLORS, VISUAL_LABELS, normaliseField, defaultProperties, defaultBuckets };
