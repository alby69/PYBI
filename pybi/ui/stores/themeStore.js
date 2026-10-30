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

export const THEMES = {
  classic: {
    key: 'classic',
    name: 'Classic',
    layoutTheme: 'PowerBI_Classic',
    colors: ['#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7', '#744EC2', '#D9B200', '#D64550'],
    background: '#FFFFFF',
    foreground: '#252423',
    tableHeader: '#F0F0F0',
    canvas: '#eaeaea',
  },
  dark: {
    key: 'dark',
    name: 'Dark',
    layoutTheme: 'PowerBI_Dark',
    colors: ['#31B6FD', '#4584FF', '#FF6B6B', '#FFC83B', '#2DE2A6', '#B263FF', '#F88379', '#00E5FF'],
    background: '#1A1918',
    foreground: '#F3F2F1',
    tableHeader: '#323130',
    canvas: '#111111',
  },
  cityPark: {
    key: 'city-park',
    name: 'City Park',
    layoutTheme: 'PowerBI_CityPark',
    colors: ['#5F6B6D', '#A8B6BF', '#D8E1E8', '#4B5859', '#8A9B9E', '#2E3B3D', '#C4D1D9', '#1E2829'],
    background: '#F4F6F7',
    foreground: '#1E2829',
    tableHeader: '#E2E7EA',
    canvas: '#f4f6f7',
  },
};

const ALIASES = {
  PowerBI_Classic: 'classic',
  PowerBI_Dark: 'dark',
  PowerBI_CityPark: 'cityPark',
  'city-park': 'cityPark',
  cityPark: 'cityPark',
  classic: 'classic',
  dark: 'dark',
};

function resolveKey(value) {
  return ALIASES[value] || 'classic';
}

export const useThemeStore = defineStore('pbiTheme', {
  state: () => ({
    theme: 'classic',
  }),

  getters: {
    currentTheme(state) {
      return THEMES[state.theme] || THEMES.classic;
    },
    dataColors() {
      return this.currentTheme.colors;
    },
    layoutTheme() {
      return this.currentTheme.layoutTheme;
    },
    availableThemes() {
      return Object.values(THEMES).map(theme => ({ key: theme.key, name: theme.name }));
    },
  },

  actions: {
    initialize() {
      let stored = null;
      try {
        stored = window.localStorage.getItem('pybi-theme');
      } catch (error) {
        stored = null;
      }
      this.applyTheme(stored || 'classic');
    },

    applyTheme(value) {
      this.theme = resolveKey(value);
      if (typeof document !== 'undefined') {
        document.documentElement.dataset.theme = this.currentTheme.key;
        document.documentElement.style.setProperty('--pbi-bg-canvas', this.currentTheme.canvas);
        document.documentElement.style.setProperty('--pbi-bg-visual', this.currentTheme.background);
        document.documentElement.style.setProperty('--pbi-text-main', this.currentTheme.foreground);
        this.currentTheme.colors.forEach((color, index) => {
          document.documentElement.style.setProperty(`--pbi-color-${index + 1}`, color);
        });
      }
      try {
        window.localStorage.setItem('pybi-theme', this.theme);
      } catch (error) {
        // localStorage may be unavailable in private/embedded contexts.
      }
      return this.theme;
    },

    applyFromLayout(layoutTheme) {
      this.applyTheme(layoutTheme);
    },

    toggleDarkMode() {
      this.applyTheme(this.theme === 'dark' ? 'classic' : 'dark');
    },
  },
});

export { resolveKey };
