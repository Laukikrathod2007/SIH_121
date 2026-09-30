import { useEffect, useState, useCallback } from 'react';

export type Theme = 'dark' | 'light';
const STORAGE_KEY = 'drillwise-theme';

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
  } catch {
    /* localStorage unavailable (private mode, etc.) -- fall through to default */
  }
  return 'dark';
}

// App-wide light/dark toggle. Applies via a `data-theme` attribute on
// <html>, which index.css's [data-theme='light'] overrides key off of --
// see index.css for why this is attribute-scoped CSS overrides on the
// existing Tailwind classes rather than a full component rewrite.
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch {
      /* non-fatal -- theme just won't persist across reloads */
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }, [theme, setTheme]);

  return { theme, setTheme, toggleTheme };
}
