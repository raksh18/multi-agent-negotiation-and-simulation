/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#EEF1F4',
        ink: { DEFAULT: '#14202B', soft: '#4A5967', faint: '#8795A3' },
        line: '#D5DCE3',
        teal: { DEFAULT: '#0F766E', dark: '#0B5A54', tint: '#DDF1EE' },
        brass: { DEFAULT: '#B7791F', tint: '#F8EBD3' },
        brick: { DEFAULT: '#B4332E', tint: '#F8E1DF' },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
