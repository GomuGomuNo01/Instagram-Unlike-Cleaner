// Jeton de l'API locale. L'interface compilée le reçoit dans une balise <meta> injectée
// par `iuc serve` ; en développement (`npm run dev`), il est saisi une fois et gardé pour
// l'onglet (sessionStorage).

export const TOKEN_HEADER = 'X-IUC-Token'
const TOKEN_META = 'iuc-token'
const STORAGE_KEY = 'iuc.token'

export function getToken(): string | null {
  const meta = document.querySelector<HTMLMetaElement>(`meta[name="${TOKEN_META}"]`)
  if (meta?.content) return meta.content
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function saveToken(token: string): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, token.trim())
  } catch {
    // Stockage indisponible (navigation privée stricte) : le jeton sera redemandé.
  }
}
