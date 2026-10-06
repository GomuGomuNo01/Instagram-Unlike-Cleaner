import { useEffect, useState } from 'react'

import { api, errorMessage, unwrap } from '../api/client'
import type { Job } from '../api/types'
import { AppPage } from '../components/Layout'
import { ArrowRightIcon, HeartOffIcon } from '../components/icons'
import { JobStatusBadge } from '../components/StatusBadge'
import {
  Alert,
  AppLink,
  ButtonLink,
  Card,
  PageHeader,
  Skeleton,
  SkeletonBlock,
} from '../components/ui'
import { describeFilters } from '../lib/filters'
import { formatDateTime, plural } from '../lib/format'

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
          <ButtonLink to="/commencer" size="lg" trailingIcon={<ArrowRightIcon />}>
            Nouveau nettoyage
          </ButtonLink>
        }
      />
      {error && <Alert tone="danger">{error}</Alert>}
      {!jobs && !error && (
        <SkeletonBlock label="Chargement de tes nettoyages…">
          <div className="space-y-4">
            {[0, 1, 2].map((index) => (
              <div key={index} className="card p-6">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="mt-3 h-4 w-72 max-w-full" />
                <Skeleton className="mt-4 h-4 w-56 max-w-full" />
              </div>
            ))}
          </div>
        </SkeletonBlock>
      )}
      {jobs?.length === 0 && (
        <Card padding="lg" className="animate-fade-up text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-primary-soft text-primary-strong">
            <HeartOffIcon className="h-6 w-6" />
          </span>
          <h2 className="mt-4 text-h3 text-fg">Aucun nettoyage pour l’instant</h2>
          <p className="mx-auto mt-2 max-w-text text-small text-fg-muted">
            Prépare ton premier aperçu : rien n’est retiré sans ta validation.
          </p>
          <ButtonLink to="/commencer" className="mt-6">
            Préparer un premier nettoyage
          </ButtonLink>
        </Card>
      )}
      {jobs && jobs.length > 0 && (
        <ul className="space-y-4">
          {jobs.map((job) => (
            <li key={job.id} className="animate-fade-up">
              <JobCard job={job} />
            </li>
          ))}
        </ul>
      )}
    </AppPage>
  )
}

/** Carte entièrement cliquable : le lien de l'action principale couvre toute la carte. */
function JobCard({ job }: { job: Job }) {
  const next = nextStep(job)
  return (
    <Card as="article" interactive>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-h3 text-fg">Nettoyage n° {job.id}</h2>
            <JobStatusBadge status={job.status} />
          </div>
          <p className="mt-1 text-small text-fg-muted">
            Créé le {formatDateTime(job.created_at)}, {describeFilters(job.filters)}
          </p>
          <p className="mt-3 text-small text-fg">
            {plural(job.counts.done ?? 0, 'retiré', 'retirés')},{' '}
            {plural(job.to_process, 'à traiter', 'à traiter')},{' '}
            {plural(job.counts.excluded ?? 0, 'gardé', 'gardés')}
            {(job.counts.failed ?? 0) > 0 && `, ${plural(job.counts.failed ?? 0, 'échec')}`}
          </p>
        </div>
        <AppLink
          to={next.to}
          className={`btn ${next.primary ? 'btn-primary' : 'btn-secondary'} shrink-0 after:absolute after:inset-0 after:rounded-xl`}
        >
          {next.label}
          <span data-icon="trailing" className="inline-flex">
            <ArrowRightIcon />
          </span>
        </AppLink>
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
