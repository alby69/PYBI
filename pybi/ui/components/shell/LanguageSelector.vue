<template>
  <select
    :value="localeStore.currentLocale"
    :aria-label="localeStore.t('shell.language')"
    :title="localeStore.t('shell.language')"
    class="language-selector"
    @change="selectLocale"
  >
    <option v-for="locale in localeStore.availableLocales" :key="locale.code" :value="locale.code">
      {{ locale.code.toUpperCase() }}
    </option>
  </select>
</template>

<script>
import { useLocaleStore } from 'pybi-locale-store';

export default {
  name: 'LanguageSelector',
  setup() {
    const localeStore = useLocaleStore();

    async function selectLocale(event) {
      await localeStore.setLocale(event.target.value);
    }

    return { localeStore, selectLocale };
  },
};
</script>

<style scoped>
.language-selector {
  min-width: 48px;
  border: 1px solid var(--pbi-pane-border, #d2d0ce);
  border-radius: 3px;
  background: white;
  padding: 2px 4px;
  color: var(--pbi-text-main, #252423);
  font-size: 10px;
}
</style>