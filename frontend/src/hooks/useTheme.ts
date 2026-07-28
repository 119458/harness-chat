import { useEffect, useState } from 'react'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'theme'

/** Read the current theme from the <html> class (set pre-paint by index.html). */
function readTheme(): Theme {
  if (typeof document === 'undefined') return 'dark'
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

/**
 * Theme controller (constitution Principle V). Toggles the `dark` class on
 * <html> and persists the choice to localStorage. Default is dark; the initial
 * class is applied pre-paint by the inline script in index.html, so this hook
 * only keeps state in sync after mount.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readTheme)

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', theme === 'dark')
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      /* localStorage unavailable (e.g. privacy mode) - keep in-memory only */
    }
  }, [theme])

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  return { theme, toggle }
}
