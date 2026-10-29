import { defineStore } from 'pinia';

export const useDaxStore = defineStore('dax', {
  state: () => ({
    currentExpression: 'Total Sales = SUM(Sales[Amount])',
    isValid: true,
    validationErrors: [],
    measureName: 'New Measure',
    referencedTables: [],
    referencedColumns: []
  }),
  actions: {
    async validateExpression(expression, projectId = 'default', currentTable = 'Sales') {
      this.currentExpression = expression;
      try {
        const response = await fetch(`/api/v1/projects/${projectId}/dax/validate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            expression,
            current_table: currentTable,
            project_id: projectId
          })
        });
        if (response.ok) {
          const data = await response.json();
          this.isValid = data.is_valid;
          this.measureName = data.measure_name || 'New Measure';
          this.validationErrors = data.errors || [];
          this.referencedTables = data.referenced_tables || [];
          this.referencedColumns = data.referenced_columns || [];
          return data;
        }
      } catch (err) {
        console.error('DAX validation error:', err);
      }
      return { is_valid: false, errors: [] };
    },

    async getAutocompleteSuggestions(expression, cursorPosition, projectId = 'default') {
      try {
        const response = await fetch(`/api/v1/projects/${projectId}/dax/autocomplete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            expression,
            cursor_position: cursorPosition,
            project_id: projectId
          })
        });
        if (response.ok) {
          const data = await response.json();
          return data.suggestions || [];
        }
      } catch (err) {
        console.error('DAX autocomplete error:', err);
      }
      return [];
    },

    async saveMeasure(measure, projectId = 'default') {
      let payload = typeof measure === 'string' ? {
        id: `m_${Date.now()}`,
        name: this.measureName || 'New Measure',
        table_name: 'Sales',
        expression: measure,
        format_string: '#,##0.00 €',
        is_hidden: false,
        dependencies: [...this.referencedTables, ...this.referencedColumns]
      } : measure;

      try {
        const response = await fetch(`/api/v1/projects/${projectId}/dax/measures`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (response.ok) {
          return await response.json();
        }
      } catch (err) {
        console.error('Error saving measure:', err);
      }
      return null;
    }
  }
});
