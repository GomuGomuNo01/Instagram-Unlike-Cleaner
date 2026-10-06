import type { Job, JobCreate, SortOrder } from '../api/types'
import { sortOrderLabels } from '../i18n/fr'
import { formatDay } from './format'

/** Valeurs du formulaire des critères, telles que saisies : le filtre d'Instagram (panneau
 * « Trier et filtrer »), et la limite facultative d'un essai. */
export interface FiltersForm {
  sort: SortOrder
  startDate: string // AAAA-MM-JJ, vide = depuis le début
  endDate: string // AAAA-MM-JJ, vide = jusqu'à aujourd'hui
  maxScanned: string // vide = toute la grille
}

export const emptyFilters: FiltersForm = {
  sort: 'newest_first',
  startDate: '',
  endDate: '',
  maxScanned: '',
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
    start_date: form.startDate || null,
    end_date: form.endDate || null,
    max_scanned: form.maxScanned ? Number(form.maxScanned) : null,
  }
}

/** Résumé du filtre d'Instagram d'un nettoyage : « likes du 01/01/2019 au 31/12/2021, du
 * plus récent au plus ancien ». */
export function describeFilters(filters: Job['filters']): string {
  const { start_date: start, end_date: end, sort } = filters
  const period =
    start || end
      ? `likes du ${start ? formatDay(start) : 'début'} au ${end ? formatDay(end) : 'jour'}`
      : 'tout l’historique'
  return `${period}, ${sortOrderLabels[sort ?? 'newest_first'].toLowerCase()}`
}

/** Date du jour au format AAAA-MM-JJ, en heure locale. */
export function localToday(now = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}
