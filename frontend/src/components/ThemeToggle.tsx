import { useEffect, useState } from 'react'

import { applyTheme, saveTheme, storedTheme, type ThemeChoice } from '../lib/preferences'
import { MonitorIcon, MoonIcon, SunIcon } from './icons'
import { Tooltip } from './ui'

const labels: Record<ThemeChoice, string> = {
  system: 'thème du système',
  light: 'thème clair',
  dark: 'thème sombre',
}
const next: Record<ThemeChoice, ThemeChoice> = { system: 'light', light: 'dark', dark: 'system' }
const icons = { system: MonitorIcon, light: SunIcon, dark: MoonIcon }

/** Bouton unique qui fait tourner les thèmes : système, clair, sombre. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeChoice>(storedTheme)

  useEffect(() => {
    applyTheme(theme)
    saveTheme(theme)
    const media = window.matchMedia?.('(prefers-color-scheme: dark)')
    const follow = () => applyTheme(theme)
    media?.addEventListener('change', follow)
    return () => media?.removeEventListener('change', follow)
  }, [theme])

  const Icon = icons[theme]
  return (
    <Tooltip label={`Affichage : ${labels[theme]}`} align="end">
      <button
        type="button"
        onClick={() => setTheme(next[theme])}
        aria-label={`Affichage : ${labels[theme]}. Passer au ${labels[next[theme]]}`}
        className="btn btn-ghost btn-icon"
      >
        <Icon key={theme} className="h-5 w-5 animate-pop" />
      </button>
    </Tooltip>
  )
}
