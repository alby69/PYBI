/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pybi/ui/**/*.vue',
    './pybi/ui/**/*.js',
    './pybi/ui/**/*.py',
    './pybi/frontend/**/*.vue',
    './pybi/frontend/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        pbi: {
          accent: 'var(--pbi-accent)',
          'accent-hover': 'var(--pbi-accent-hover)',
          'accent-soft': 'var(--pbi-accent-soft)',
          canvas: 'var(--pbi-bg-canvas)',
          visual: 'var(--pbi-bg-visual)',
          pane: 'var(--pbi-bg-pane)',
          header: 'var(--pbi-bg-header)',
          ribbon: 'var(--pbi-bg-ribbon)',
          'pane-border': 'var(--pbi-pane-border)',
          text: 'var(--pbi-text-main)',
          'text-muted': 'var(--pbi-text-muted)',
        },
      },
      fontSize: {
        'pbi-xs': ['10px', { lineHeight: '1.25' }],
        'pbi-sm': ['11px', { lineHeight: '1.3' }],
        'pbi-base': ['12px', { lineHeight: '1.35' }],
        'pbi-md': ['13px', { lineHeight: '1.35' }],
        'pbi-lg': ['16px', { lineHeight: '1.3' }],
        'pbi-kpi': ['24px', { lineHeight: '1.1' }],
      },
      boxShadow: {
        'pbi-card': 'var(--pbi-shadow-visual)',
        'pbi-dropdown': 'var(--pbi-shadow-dropdown)',
        'pbi-modal': 'var(--pbi-shadow-modal)',
      },
      fontFamily: {
        pbi: ['Segoe UI', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
