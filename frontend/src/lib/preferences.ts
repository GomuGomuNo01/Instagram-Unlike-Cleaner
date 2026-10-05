// Préférences de ce navigateur (consentement, thème). Le stockage peut être indisponible
// (navigation privée stricte) : l'interface fonctionne alors sans les mémoriser.

const CONSENT_KEY = 'iuc.consent'
const CONSENT_VERSION = 'v1' // à changer si l'avertissement évolue, pour le faire relire
const THEME_KEY = 'iuc.theme'

export type ThemeChoice = 'system' | 'light' | 'dark'

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Préférence non mémorisée : sans conséquence.
  }
}

export function hasConsent(): boolean {
  return read(CONSENT_KEY) === CONSENT_VERSION
}

export function giveConsent(): void {
  write(CONSENT_KEY, CONSENT_VERSION)
}

export function storedTheme(): ThemeChoice {
  const value = read(THEME_KEY)
  return value === 'light' || value === 'dark' ? value : 'system'
}

export function saveTheme(choice: ThemeChoice): void {
  write(THEME_KEY, choice)
}

/** Applique le thème : classe « dark » sur <html> si choisi, ou si le système est sombre. */
export function applyTheme(choice: ThemeChoice): void {
  const systemDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  const dark = choice === 'dark' || (choice === 'system' && systemDark)
  document.documentElement.classList.toggle('dark', dark)
}
