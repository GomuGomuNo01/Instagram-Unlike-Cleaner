const dateTime = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' })

/** « 05/10/2026 13:06 » à partir d'une date ISO. */
export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : 'date inconnue'
}

/** « 03/10/2026 » à partir de « 2026-10-03 ». */
export function formatDay(day: string | null | undefined): string {
  if (!day) return 'date inconnue'
  const [year, month, date] = day.split('-')
  return year && month && date ? `${date}/${month}/${year}` : day
}

/** « 42 s », « 1 min 17 s », « 2 h 03 min ». */
export function formatDuration(totalSeconds: number): string {
  const seconds = Math.round(totalSeconds)
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  if (hours) return `${hours} h ${String(minutes).padStart(2, '0')} min`
  if (minutes) return `${minutes} min ${String(rest).padStart(2, '0')} s`
  return `${rest} s`
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count > 1 ? pluralForm : singular}`
}
