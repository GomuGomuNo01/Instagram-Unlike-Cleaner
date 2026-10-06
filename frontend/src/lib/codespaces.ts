// Vraie version dans GitHub Codespaces : `iuc serve` indique dans une balise <meta> l'adresse
// du bureau distant où s'affiche la fenêtre Chromium. Ailleurs, la balise est absente.

const DESKTOP_META = 'iuc-desktop'

/** Adresse du bureau distant du Codespace, ou null hors Codespaces. */
export function codespaceDesktopUrl(): string | null {
  const content = document.querySelector<HTMLMetaElement>(`meta[name="${DESKTOP_META}"]`)?.content
  return content?.startsWith('https://') ? content : null
}
