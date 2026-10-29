<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 select-none">
    <div class="bg-white border border-slate-300 rounded-lg shadow-2xl w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
      <div class="flex items-center justify-between px-4 py-3 bg-slate-100 border-b border-slate-200">
        <div class="flex items-center gap-2 font-bold text-sm text-slate-800"><span>📜</span><span>Advanced Editor</span></div>
        <button @click="close" class="text-slate-400 hover:text-slate-600 font-bold text-lg">×</button>
      </div>
      <div class="p-4 flex-grow overflow-hidden flex flex-col gap-2 text-xs">
        <div class="flex items-center gap-2 text-[11px] text-slate-600">
          <span>Edit the query JSON. The <code class="font-mono bg-slate-100 px-1 rounded">steps</code> array is applied top to bottom.</span>
          <button @click="reset" class="ml-auto text-blue-600 hover:underline font-semibold">Reset</button>
        </div>
        <textarea
          v-model="jsonText"
          spellcheck="false"
          class="flex-grow w-full min-h-[360px] p-3 font-mono text-[11px] border border-slate-300 rounded bg-slate-50 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
        ></textarea>
        <div v-if="parseError" class="text-red-600 font-mono text-[11px]">⚠ {{ parseError }}</div>
      </div>
      <div class="flex items-center justify-end gap-2 px-4 py-2.5 bg-slate-100 border-t border-slate-200">
        <button @click="close" class="px-3 py-1.5 rounded hover:bg-slate-200 text-slate-700 text-xs font-semibold">Cancel</button>
        <button @click="submit" :disabled="!parsedQuery" class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold rounded text-xs">Apply JSON</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AdvancedEditorModal',
  props: {
    modelValue: { type: Boolean, default: false },
    query: { type: Object, default: () => ({}) }
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return { jsonText: '' };
  },
  computed: {
    isOpen: {
      get() { return this.modelValue; },
      set(value) { this.$emit('update:modelValue', value); }
    },
    parsedQuery() {
      if (!this.jsonText.trim()) return null;
      try {
        const parsed = JSON.parse(this.jsonText);
        if (Array.isArray(parsed)) return { steps: parsed };
        if (parsed && typeof parsed === 'object') return parsed;
        return null;
      } catch (err) {
        return null;
      }
    },
    parseError() {
      if (!this.jsonText.trim()) return '';
      try {
        JSON.parse(this.jsonText);
        return '';
      } catch (err) {
        return err.message;
      }
    }
  },
  watch: {
    isOpen(value) {
      if (value) this.reset();
    }
  },
  methods: {
    close() { this.isOpen = false; },
    reset() {
      this.jsonText = JSON.stringify(this.query || {}, null, 2);
    },
    submit() {
      if (!this.parsedQuery) return;
      this.$emit('apply', this.parsedQuery);
      this.close();
    }
  }
};
</script>
