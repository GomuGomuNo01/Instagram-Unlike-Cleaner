// Types de l'API, générés depuis son schéma OpenAPI (`npm run api`), donc alignés sur les
// schémas Pydantic du backend.
import type { components } from './schema'

type Schemas = components['schemas']

export type SessionStatus = Schemas['SessionStatusOut']
export type Job = Schemas['JobOut']
export type JobCreate = Schemas['JobCreate']
export type JobStatus = Schemas['JobStatus']
export type Item = Schemas['ItemOut']
export type ItemsPage = Schemas['ItemsPage']
export type ItemStatus = Schemas['ItemStatus']
export type MediaKind = Schemas['MediaKind']
export type SortOrder = Schemas['SortOrder']
export type UpdateInfo = Schemas['UpdateOut']

/** Rapport d'un nettoyage (GET /api/jobs/{id}/report), tel que produit par
 * `JobReport.to_dict()` côté backend : cette route renvoie un dictionnaire libre. */
export interface JobReport {
  nettoyage: number
  statut: JobStatus
  compte: string | null
  criteres: Job['filters']
  cree_le: string
  premiere_execution: string | null
  fin: string | null
  executions: number
  duree_active_secondes: number
  likes_cibles: number
  par_statut: Partial<Record<ItemStatus, number>>
  likes: ReportLine[]
}

export interface ReportLine {
  rang: number
  auteur: string | null
  type: string
  partagee_le: string
  statut: ItemStatus
  traite_le: string | null
  detail: string | null
  identifiant: string
}
