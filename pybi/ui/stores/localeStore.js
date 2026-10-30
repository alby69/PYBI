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

function detectLocale() {
  try {
    const savedLocale = window.localStorage.getItem('pybi_locale');
    if (savedLocale === 'it' || savedLocale === 'en') return savedLocale;
  } catch (error) {
    // localStorage may be unavailable in private or embedded contexts.
  }
  return typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('it')
    ? 'it'
    : 'en';
}

function applyLocale(locale) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', locale);
  }
  try {
    window.localStorage.setItem('pybi_locale', locale);
    document.cookie = `pybi_locale=${locale}; Path=/; Max-Age=31536000; SameSite=Lax`;
  } catch (error) {
    // Browser storage may be unavailable in private or embedded contexts.
  }
}

export const useLocaleStore = defineStore('locale', {
  state: () => ({
    currentLocale: detectLocale(),
    availableLocales: [
      { code: 'it', label: 'Italiano' },
      { code: 'en', label: 'English' },
    ],
    messages: {},
    isLoading: false,
  }),

  actions: {
    async initialize() {
      applyLocale(this.currentLocale);
      await this.loadMessages();
    },

    async setLocale(newLocale) {
      if (!['it', 'en'].includes(newLocale)) return;
      this.currentLocale = newLocale;
      applyLocale(newLocale);
      await this.loadMessages();
    },

    async loadMessages() {
      const requestedLocale = this.currentLocale;
      this.isLoading = true;
      try {
        const response = await fetch(`/api/v1/locales/${requestedLocale}`, {
          headers: { 'Accept-Language': requestedLocale },
        });
        if (!response.ok) throw new Error(`Unable to load locale ${requestedLocale}`);
        const messages = await response.json();
        if (this.currentLocale === requestedLocale) this.messages = messages;
      } catch (error) {
        if (this.currentLocale === requestedLocale) this.messages = {};
      } finally {
        if (this.currentLocale === requestedLocale) this.isLoading = false;
      }
    },

    t(key, values = {}) {
      const message = key.split('.').reduce((value, part) => value?.[part], this.messages);
      if (typeof message !== 'string') return key;
      return message.replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match);
    },
  },
});