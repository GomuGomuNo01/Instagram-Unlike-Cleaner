import type { ContentFilter, JobCreate, SortOrder } from '../api/types'

/** Valeurs du formulaire des critères, telles que saisies. */
export interface FiltersForm {
  startDate: string // AAAA-MM-JJ, vide = depuis le début
  endDate: string // AAAA-MM-JJ, vide = jusqu'à aujourd'hui
  sort: SortOrder
  content: ContentFilter
  includeAuthors: string[]
  excludeAuthors: string[]
  maxScanned: string // vide = toute la grille
}

export const emptyFilters: FiltersForm = {
  startDate: '',
  endDate: '',
  sort: 'newest_first',
  content: 'all',
  includeAuthors: [],
  excludeAuthors: [],
  maxScanned: '',
}

const USERNAME = /^[a-z0-9._]{1,30}$/

/** « @Compte_A » → « compte_a » ; null si ce n'est pas un nom de compte Instagram valide. */
export function normalizeAuthor(raw: string): string | null {
  const author = raw.trim().replace(/^@/, '').toLowerCase()
  return USERNAME.test(author) ? author : null
}

/** Erreur affichée sous chaque champ concerné. */
export type FiltersErrors = Partial<Record<keyof FiltersForm, string>>

/** Erreurs de saisie, champ par champ, avec les mêmes règles que le backend.
 * `today` au format AAAA-MM-JJ. */
export function validateFilters(form: FiltersForm, today: string): FiltersErrors {
  const errors: FiltersErrors = {}
  if (form.startDate && form.startDate > today) {
    errors.startDate = 'Cette date est dans le futur.'
  }
  if (form.endDate && form.endDate > today) {
    errors.endDate = 'Cette date est dans le futur.'
  } else if (form.startDate && form.endDate && form.startDate > form.endDate) {
    errors.endDate = 'La date de fin doit suivre la date de début.'
  }
  const both = form.includeAuthors.filter((author) => form.excludeAuthors.includes(author))
  if (both.length) {
    errors.excludeAuthors = `Déjà dans les comptes ciblés : ${both.map((a) => `@${a}`).join(', ')}.`
  }
  if (
    form.maxScanned &&
    !(Number.isInteger(Number(form.maxScanned)) && Number(form.maxScanned) >= 1)
  ) {
    errors.maxScanned = 'Indique un nombre entier supérieur à 0, ou laisse vide.'
  }
  return errors
}

/** Corps de POST /api/jobs à partir du formulaire (champs vides omis). */
export function buildJobRequest(form: FiltersForm): JobCreate {
  return {
    sort: form.sort,
    content: form.content,
    start_date: form.startDate || null,
    end_date: form.endDate || null,
    include_authors: form.includeAuthors,
    exclude_authors: form.excludeAuthors,
    max_scanned: form.maxScanned ? Number(form.maxScanned) : null,
  }
}

/** Date du jour au format AAAA-MM-JJ, en heure locale. */
export function localToday(now = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}
