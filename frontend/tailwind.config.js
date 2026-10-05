/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        scada: {
          dark: '#0b0e14',
          panel: '#121722',
          border: '#1e293b',
        }
      },
      fontFamily: {
        // Both already loaded globally in index.html (Google Fonts). Wiring
        // them up here is what actually makes font-sans / font-mono use
        // them -- without this, those utilities fell back to each
        // browser's generic serif/monospace, which is what made text
        // across the app (docs headings especially, via font-serif) look
        // inconsistent and dated instead of using the typefaces already
        // being downloaded.
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
