import { defineStore } from 'pinia';
import axios from 'axios';

export const useModelStore = defineStore('modelStore', {
  state: () => ({
    projectId: null,
    tables: [],
    relationships: [],
    measures: [],
    hierarchies: [],
    selectedItem: null, // { type: 'table'|'column'|'relationship'|'measure', data: ... }
    isAutodetectLoading: false,
    showManageRelationshipsModal: false,
    showMeasureEditorModal: false,
    editingMeasure: null,
    zoomLevel: 1.0,
    searchFilter: '',
  }),

  actions: {
    async fetchSemanticModel(projectId) {
      this.projectId = projectId;
      const res = await axios.get(`/api/v1/projects/${projectId}/semantic`);
      this.tables = res.data.tables || [];
      this.relationships = res.data.relationships || [];
      this.measures = res.data.measures || [];
      this.hierarchies = res.data.hierarchies || [];
    },

    async saveModelPositions(nodePositions) {
      // Aggiorna le posizioni x,y dei nodi tabella
      this.tables.forEach(table => {
        if (nodePositions[table.name]) {
          table.position_x = nodePositions[table.name].x;
          table.position_y = nodePositions[table.name].y;
        }
      });
      await this.persistModel();
    },

    async addOrUpdateRelationship(relData) {
      const res = await axios.post(`/api/v1/projects/${this.projectId}/semantic/relationships`, relData);
      const idx = this.relationships.findIndex(r => r.id === res.data.id);
      if (idx >= 0) this.relationships[idx] = res.data;
      else this.relationships.push(res.data);
    },

    async deleteRelationship(relId) {
      await axios.delete(`/api/v1/projects/${this.projectId}/semantic/relationships/${relId}`);
      this.relationships = this.relationships.filter(r => r.id !== relId);
      if (this.selectedItem?.type === 'relationship' && this.selectedItem?.data?.id === relId) {
        this.selectedItem = null;
      }
    },

    async runAutodetect() {
      this.isAutodetectLoading = true;
      try {
        const res = await axios.post(`/api/v1/projects/${this.projectId}/semantic/relationships/autodetect`);
        const newRels = res.data;
        newRels.forEach(rel => {
          if (!this.relationships.some(r => r.from_table === rel.from_table && r.from_column === rel.from_column && r.to_table === rel.to_table && r.to_column === rel.to_column)) {
            this.relationships.push(rel);
          }
        });
        await this.persistModel();
      } finally {
        this.isAutodetectLoading = false;
      }
    },

    async saveMeasure(measureData) {
      const res = await axios.post(`/api/v1/projects/${this.projectId}/semantic/measures`, measureData);
      const saved = res.data;
      const idx = this.measures.findIndex(m => m.id === saved.id);
      if (idx >= 0) this.measures[idx] = saved;
      else this.measures.push(saved);

      const tbl = this.tables.find(t => t.name === saved.table_name);
      if (tbl) {
        if (!tbl.measures) tbl.measures = [];
        const tIdx = tbl.measures.findIndex(m => m.id === saved.id);
        if (tIdx >= 0) tbl.measures[tIdx] = saved;
        else tbl.measures.push(saved);
      }
    },

    async persistModel() {
      await axios.put(`/api/v1/projects/${this.projectId}/semantic`, {
        project_id: this.projectId,
        tables: this.tables,
        relationships: this.relationships,
        measures: this.measures,
        hierarchies: this.hierarchies
      });
    },

    selectEntity(type, data) {
      this.selectedItem = { type, data };
    }
  }
});
