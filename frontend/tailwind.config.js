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
      }
    },
  },
  plugins: [],
}
