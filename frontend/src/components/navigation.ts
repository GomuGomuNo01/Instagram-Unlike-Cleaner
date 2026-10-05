/** Menu principal : les sections de la page d'accueil. */
export const sections = [
  { id: 'fonctionnement', label: 'Fonctionnement' },
  { id: 'demo', label: 'Démo' },
  { id: 'securite', label: 'Sécurité' },
  { id: 'faq', label: 'FAQ' },
] as const

export const sectionIds = sections.map((section) => section.id)

/** Espace de l'utilisateur : l'historique de ses nettoyages. */
export const jobsLink = { to: '/nettoyages', label: 'Mes nettoyages' } as const

export const REPOSITORY = 'https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner'
