import { useEffect, useState } from 'react'

import { api, errorMessage, unwrap } from '../api/client'
import type { Job } from '../api/types'
import { AppPage } from '../components/Layout'
import { JobStatusBadge } from '../components/StatusBadge'
import { Alert, ButtonLink, Card, PageHeader, Spinner } from '../components/ui'
import { contentFilterLabels } from '../i18n/fr'
import { formatDateTime, formatDay, plural } from '../lib/format'

/** Historique des nettoyages, avec l'action utile selon l'état de chacun. */
export function JobsPage() {
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    unwrap(api.GET('/api/jobs')).then(
      (loaded) => {
        if (active) setJobs([...loaded].reverse())
      },
      (failure: unknown) => {
        if (active) setError(errorMessage(failure))
      },
    )
    return () => {
      active = false
    }
  }, [])

  return (
    <AppPage>
      <PageHeader
        title="Mes nettoyages"
        description="Retrouve tes nettoyages, du plus récent au plus ancien."
        actions={
          <ButtonLink to="/commencer" size="lg">
            Nouveau nettoyage
          </ButtonLink>
        }
      />
      {error && <Alert tone="danger">{error}</Alert>}
      {!jobs && !error && <Spinner label="Chargement de tes nettoyages…" />}
      {jobs?.length === 0 && (
        <Card className="text-center">
          <h2 className="text-h3">Aucun nettoyage pour l’instant</h2>
          <p className="text-small mt-2">
            Prépare ton premier aperçu : rien n’est retiré sans ta validation.
          </p>
          <ButtonLink to="/commencer" className="mt-6">
            Préparer un premier nettoyage
          </ButtonLink>
        </Card>
      )}
      <ul className="space-y-4">
        {jobs?.map((job) => (
          <li key={job.id}>
            <JobCard job={job} />
          </li>
        ))}
      </ul>
    </AppPage>
  )
}

function JobCard({ job }: { job: Job }) {
  const next = nextStep(job)
  return (
    <Card>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-h3">Nettoyage n° {job.id}</h2>
            <JobStatusBadge status={job.status} />
          </div>
          <p className="text-small mt-1">
            Créé le {formatDateTime(job.created_at)}, {describeCriteria(job)}
          </p>
          <p className="mt-3 text-sm">
            {plural(job.counts.done ?? 0, 'retiré', 'retirés')},{' '}
            {plural(job.to_process, 'à traiter', 'à traiter')},{' '}
            {plural(job.counts.excluded ?? 0, 'gardé', 'gardés')}
            {(job.counts.failed ?? 0) > 0 && `, ${plural(job.counts.failed ?? 0, 'échec')}`}
          </p>
        </div>
        <ButtonLink to={next.to} variant={next.primary ? 'primary' : 'secondary'}>
          {next.label}
        </ButtonLink>
      </div>
    </Card>
  )
}

function nextStep(job: Job): { to: string; label: string; primary: boolean } {
  const base = `/nettoyages/${job.id}`
  switch (job.status) {
    case 'collecting':
    case 'ready':
      return { to: `${base}/apercu`, label: 'Vérifier l’aperçu', primary: true }
    case 'running':
      return { to: `${base}/suivi`, label: 'Suivre le nettoyage', primary: true }
    case 'paused':
      return { to: `${base}/suivi`, label: 'Reprendre', primary: true }
    default:
      return { to: `${base}/rapport`, label: 'Voir le rapport', primary: false }
  }
}

function describeCriteria(job: Job): string {
  const { start_date: start, end_date: end, content } = job.filters
  const period =
    start || end
      ? `likes du ${start ? formatDay(start) : 'début'} au ${end ? formatDay(end) : 'jour'}`
      : 'tout l’historique'
  return `${period}, ${contentFilterLabels[content ?? 'all'].toLowerCase()}`
}
