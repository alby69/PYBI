<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
      <!-- Modal Header -->
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800">
          <span>✨</span>
          <span>Add Custom Column</span>
        </div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 font-bold text-lg focus:outline-none">×</button>
      </div>

      <!-- Modal Body (Two Column Split) -->
      <div class="p-4 overflow-y-auto flex-grow flex flex-col md:flex-row gap-4 text-xs">
        <!-- Left Side: Inputs & Formula Area -->
        <div class="flex-grow flex flex-col gap-3 md:w-3/5">
          <!-- Column Name Input -->
          <div class="flex flex-col gap-1">
            <label class="font-bold text-slate-700">New Column Name</label>
            <input
              v-model="newColumnName"
              type="text"
              placeholder="Custom"
              class="w-full px-3 py-1.5 border border-slate-300 rounded bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium"
            />
          </div>

          <!-- Practical Examples Banner -->
          <div class="bg-blue-50 border border-blue-200 rounded p-2 text-blue-900 flex flex-col gap-1">
            <span class="font-bold text-[11px] flex items-center gap-1">
              <span>💡</span> Practical Expression Examples:
            </span>
            <div class="flex flex-col gap-0.5 text-[10px] text-blue-800 font-mono">
              <span>• String: <code>CONCAT(customer_name, '_', city)</code> or <code>customer_name || '_' || city</code></span>
              <span>• Math: <code>amount * 1.22</code></span>
              <span>• Logic: <code>CASE WHEN score >= 60 THEN 'Pass' ELSE 'Fail' END</code></span>
            </div>
          </div>

          <!-- Formula Editor Area -->
          <div class="flex flex-col gap-1 flex-grow">
            <div class="flex items-center justify-between">
              <label class="font-bold text-slate-700">Custom Column Formula (=)</label>
              <button @click="clearExpression" class="text-[10px] text-slate-400 hover:text-red-600">Clear</button>
            </div>
            <textarea
              ref="exprInput"
              v-model="expression"
              rows="6"
              placeholder="e.g. CONCAT(first_name, ' ', last_name)"
              class="w-full p-2.5 font-mono text-xs border border-slate-300 rounded bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
            ></textarea>
            <span class="text-[10px] text-slate-400">Syntax error checking enabled. Uses standard DuckDB / SQL expressions.</span>
          </div>
        </div>

        <!-- Right Side: Function Helper Prontuario & Columns List -->
        <div class="md:w-2/5 flex flex-col gap-3 border-l border-slate-200 pl-4 bg-slate-50/50 p-2 rounded">
          <!-- Available Columns -->
          <div class="flex flex-col gap-1">
            <span class="font-bold text-slate-700 text-[11px] uppercase tracking-wider">Available Columns</span>
            <div class="flex flex-wrap gap-1 max-h-32 overflow-y-auto bg-white p-2 border border-slate-200 rounded">
              <button
                v-for="col in availableColumns"
                :key="col"
                @click="insertToken(`[${col}]`)"
                class="px-2 py-0.5 rounded bg-slate-100 hover:bg-blue-100 text-slate-800 hover:text-blue-900 border border-slate-300 font-mono text-[10px] truncate"
                :title="`Insert ${col}`"
              >
                + {{ col }}
              </button>
              <span v-if="!availableColumns.length" class="text-[10px] text-slate-400 italic">No columns available</span>
            </div>
          </div>

          <!-- Function Category Helper Prontuario -->
          <div class="flex flex-col gap-1 flex-grow">
            <span class="font-bold text-slate-700 text-[11px] uppercase tracking-wider">Supported Functions</span>
            <div class="flex flex-col gap-1.5 overflow-y-auto max-h-48 bg-white p-2 border border-slate-200 rounded">
              <div v-for="fn in functionCatalog" :key="fn.name" class="flex flex-col border-b border-slate-100 pb-1 last:border-b-0">
                <div class="flex items-center justify-between">
                  <button
                    @click="insertToken(fn.syntax)"
                    class="font-mono font-bold text-blue-700 hover:underline text-[11px]"
                  >
                    {{ fn.name }}
                  </button>
                  <span class="text-[9px] px-1 bg-slate-100 text-slate-500 rounded">{{ fn.category }}</span>
                </div>
                <span class="text-[9px] text-slate-500">{{ fn.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">
          Cancel
        </button>
        <button
          @click="submit"
          :disabled="!newColumnName || !expression"
          class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-bold rounded text-xs transition-colors"
        >
          Add Column
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { useUiStore } from 'pybi-store';

export default {
  name: 'CustomColumnModal',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'add-column'],
  data() {
    return {
      newColumnName: 'Custom',
      expression: '',
      functionCatalog: [
        { name: 'CONCAT()', syntax: 'CONCAT(colA, colB)', category: 'Text', desc: 'Concatenates two or more text values.' },
        { name: 'UPPER()', syntax: 'UPPER(column_name)', category: 'Text', desc: 'Converts text to uppercase.' },
        { name: 'LOWER()', syntax: 'LOWER(column_name)', category: 'Text', desc: 'Converts text to lowercase.' },
        { name: 'TRIM()', syntax: 'TRIM(column_name)', category: 'Text', desc: 'Removes leading and trailing spaces.' },
        { name: 'SUBSTRING()', syntax: 'SUBSTRING(column_name, 1, 5)', category: 'Text', desc: 'Extracts substring from text.' },
        { name: 'ROUND()', syntax: 'ROUND(column_name, 2)', category: 'Math', desc: 'Rounds numeric value to N decimals.' },
        { name: 'ABS()', syntax: 'ABS(column_name)', category: 'Math', desc: 'Absolute value.' },
        { name: 'COALESCE()', syntax: 'COALESCE(column_name, default_val)', category: 'Logic', desc: 'Returns first non-null value.' },
        { name: 'CASE WHEN', syntax: 'CASE WHEN condition THEN val1 ELSE val2 END', category: 'Logic', desc: 'Conditional branch.' }
      ]
    };
  },
  computed: {
    isOpen: {
      get() { return this.modelValue; },
      set(val) { this.$emit('update:modelValue', val); }
    },
    store() {
      try { return useUiStore(); } catch (e) { return null; }
    },
    availableColumns() {
      if (this.store && this.store.previewData && this.store.previewData.columns) {
        return this.store.previewData.columns.map(c => typeof c === 'string' ? c : c.name);
      }
      return ['amount', 'region', 'customer_name', 'status'];
    }
  },
  methods: {
    close() {
      this.isOpen = false;
    },
    clearExpression() {
      this.expression = '';
    },
    insertToken(token) {
      this.expression = (this.expression ? this.expression + ' ' : '') + token;
    },
    submit() {
      if (!this.newColumnName || !this.expression) return;
      this.$emit('add-column', {
        new_column: this.newColumnName,
        expression: this.expression
      });
      this.close();
    }
  }
};
</script>
