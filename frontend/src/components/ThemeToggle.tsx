import { useEffect, useState } from 'react'

import { applyTheme, saveTheme, storedTheme, type ThemeChoice } from '../lib/preferences'
import { MonitorIcon, MoonIcon, SunIcon } from './icons'

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
  const label = `Affichage : ${labels[theme]}. Passer au ${labels[next[theme]]}`
  return (
    <button
      type="button"
      onClick={() => setTheme(next[theme])}
      aria-label={label}
      title={label}
      className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-zinc-700 transition-colors hover:bg-zinc-100 active:bg-zinc-200 dark:text-zinc-300 dark:hover:bg-zinc-800"
    >
      <Icon />
    </button>
  )
}
