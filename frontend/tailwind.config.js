/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        paper: 'var(--paper)',
        surface: 'var(--surface)',
        sunken: 'var(--sunken)',
        line: 'var(--line)',
        'line-strong': 'var(--line-strong)',
        ink: { DEFAULT: 'var(--ink)', 2: 'var(--ink-2)', 3: 'var(--ink-3)' },
        accent: { DEFAULT: 'var(--accent)', soft: 'var(--accent-soft)', ink: 'var(--accent-ink)' },
        sev: {
          critical: 'var(--sev-critical)',
          high: 'var(--sev-high)',
          medium: 'var(--sev-medium)',
          low: 'var(--sev-low)',
        },
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        card: '0 1px 0 rgba(22,24,29,0.04), 0 1px 2px rgba(22,24,29,0.06)',
        pop: '0 12px 32px -8px rgba(22,24,29,0.18), 0 2px 6px rgba(22,24,29,0.08)',
      },
      keyframes: {
        pulseRing: { '0%': { transform: 'scale(0.6)', opacity: '0.7' }, '100%': { transform: 'scale(2.2)', opacity: '0' } },
        slideIn: { '0%': { transform: 'translateX(16px)', opacity: '0' }, '100%': { transform: 'none', opacity: '1' } },
        fadeUp: { '0%': { transform: 'translateY(6px)', opacity: '0' }, '100%': { transform: 'none', opacity: '1' } },
      },
      animation: {
        'pulse-ring': 'pulseRing 1.8s cubic-bezier(0.2,0.6,0.4,1) infinite',
        'slide-in': 'slideIn 220ms cubic-bezier(0.2,0.7,0.2,1)',
        'fade-up': 'fadeUp 260ms cubic-bezier(0.2,0.7,0.2,1) both',
      },
    },
  },
  plugins: [],
};
