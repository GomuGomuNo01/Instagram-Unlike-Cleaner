/** Total retiré après un lot, et moment où l'événement a été reçu (ms). */
export interface BatchPoint {
  total: number
  at: number
}

/** Vitesse de retrait en likes par minute, depuis le début de l'exécution suivie.
 * Nulle tant qu'aucun lot n'est terminé. */
export function removalRate(points: BatchPoint[], startedAt: number): number | null {
  const last = points.at(-1)
  if (!last || last.total <= 0) return null
  const minutes = (last.at - startedAt) / 60_000
  return minutes > 0 ? last.total / minutes : null
}

/** Temps restant estimé, en secondes, au rythme observé (pauses entre lots comprises). */
export function estimateRemainingSeconds(
  remaining: number,
  ratePerMinute: number | null,
): number | null {
  if (!ratePerMinute || ratePerMinute <= 0) return null
  return remaining <= 0 ? 0 : (remaining / ratePerMinute) * 60
}

/** Part déjà traitée, entre 0 et 100. */
export function percent(done: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.round((done / total) * 100))
}
