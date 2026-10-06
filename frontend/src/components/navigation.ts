/** Menu principal : les sections de la page d'accueil. */
export const sections = [
  { id: 'fonctionnement', label: 'Fonctionnement' },
  { id: 'demo', label: 'Démo' },
  { id: 'securite', label: 'Sécurité' },
  { id: 'faq', label: 'FAQ' },
] as const

export const sectionIds = sections.map((section) => section.id)

/** Présentation vidéo de l'application, en tête du menu. */
export const presentationLink = { to: '/presentation', label: 'Présentation' } as const

/** Espace de l'utilisateur : l'historique de ses nettoyages. */
export const jobsLink = { to: '/nettoyages', label: 'Mes nettoyages' } as const

export const REPOSITORY = 'https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner'

/** Installeur Windows de la dernière version publiée (nom de fichier stable). */
export const WINDOWS_DOWNLOAD = `${REPOSITORY}/releases/latest/download/IUC-Setup.exe`
