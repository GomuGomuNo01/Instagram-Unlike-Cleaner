import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

import { api, errorMessage, unwrap } from '../api/client'
import { useJobEvents, type JobEvent } from '../api/events'
import type { Job } from '../api/types'
import { parseJobId, useJob } from '../api/useJob'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { ArrowRightIcon, PauseIcon, PlayIcon } from '../components/icons'
import { JobStatusBadge } from '../components/StatusBadge'
import {
  Alert,
  Button,
  ButtonLink,
  Card,
  ConfirmDialog,
  LiveDot,
  PageHeader,
  ProgressBar,
  Skeleton,
  SkeletonBlock,
  Stat,
  useToast,
} from '../components/ui'
import { stopAdvice } from '../i18n/fr'
import { formatDuration, plural } from '../lib/format'
import { estimateRemainingSeconds, percent, removalRate } from '../lib/progress'
import { NotFoundPage } from './NotFoundPage'

export function TrackingPage() {
  const jobId = parseJobId(useParams().jobId)
  return jobId === null ? <NotFoundPage /> : <Tracking key={jobId} jobId={jobId} />
}

const titles: Partial<Record<Job['status'], string>> = {
  ready: 'Nettoyage prêt à démarrer',
  running: 'Nettoyage en cours',
  paused: 'Nettoyage en pause',
  completed: 'Nettoyage terminé',
  stopped: 'Nettoyage arrêté',
  failed: 'Nettoyage en échec',
}

/** Suivi en direct : progression, vitesse, temps restant, contrôle et journal. */
function Tracking({ jobId }: { jobId: number }) {
  const toast = useToast()
  const { job, error, reload } = useJob(jobId)
  const { events, restart } = useJobEvents(jobId)
  const [action, setAction] = useState<'pause' | 'resume' | 'stop' | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [confirmStop, setConfirmStop] = useState(false)

  // L'état du nettoyage est relu après chaque étape annoncée par le flux.
  const lastEvent = events.at(-1)
  useEffect(() => {
    if (lastEvent && lastEvent.type !== 'progress') void reload()
  }, [lastEvent, reload])

  const run = useMemo(() => currentRun(events), [events])
  if (!job) {
    return (
      <AppPage>
        <FlowSteps current={4} />
        {error ? (
          <Alert tone="danger">{error}</Alert>
        ) : (
          <SkeletonBlock label="Chargement du suivi…">
            <Skeleton className="h-10 w-2/3 max-w-text" />
            <Skeleton className="mt-8 h-56 w-full rounded-xl" />
            <Skeleton className="mt-4 h-40 w-full rounded-xl" />
          </SkeletonBlock>
        )}
      </AppPage>
    )
  }

  const done = job.counts.done ?? 0
  const failed = job.counts.failed ?? 0
  const skipped = job.counts.skipped ?? 0
  const handled = done + failed + skipped
  const rate = removalRate(run.batches, run.startedAt)
  const remaining = estimateRemainingSeconds(job.to_process, rate)

  const call = async (
    kind: 'pause' | 'resume' | 'stop',
    request: () => Promise<unknown>,
    reopen = false,
  ) => {
    setAction(kind)
    setActionError(null)
    try {
      await request()
      if (reopen) restart()
      await reload()
      if (kind === 'pause') {
        toast({
          tone: 'info',
          title: 'Pause demandée',
          description: 'Elle prend effet à la fin du lot en cours.',
        })
      }
      if (kind === 'resume') toast({ title: 'Nettoyage repris' })
    } catch (failure) {
      setActionError(errorMessage(failure))
    } finally {
      setAction(null)
      setConfirmStop(false)
    }
  }
  const params = { params: { path: { job_id: jobId } } }
  const pause = () => call('pause', () => unwrap(api.POST('/api/jobs/{job_id}/pause', params)))
  const resume = () =>
    call(
      'resume',
      () => unwrap(api.POST('/api/jobs/{job_id}/resume', { ...params, body: {} })),
      true,
    )
  const stop = () => call('stop', () => unwrap(api.POST('/api/jobs/{job_id}/stop', params)))

  const finished = job.status === 'completed' || job.status === 'stopped'
  const actions = (
    <>
      {job.running && (
        <Button
          variant="secondary"
          onClick={() => void pause()}
          loading={action === 'pause'}
          icon={<PauseIcon className="h-4 w-4" />}
        >
          {action === 'pause' ? 'Pause demandée' : 'Mettre en pause'}
        </Button>
      )}
      {!job.running && job.status === 'paused' && (
        <Button
          size="lg"
          onClick={() => void resume()}
          loading={action === 'resume'}
          icon={<PlayIcon className="h-4 w-4" />}
        >
          Reprendre le nettoyage
        </Button>
      )}
      {['ready', 'paused', 'running'].includes(job.status) && (
        <Button variant="ghost" onClick={() => setConfirmStop(true)} disabled={action !== null}>
          Arrêter définitivement
        </Button>
      )}
      {finished && (
        <ButtonLink
          to={`/nettoyages/${job.id}/rapport`}
          size="lg"
          trailingIcon={<ArrowRightIcon />}
        >
          Voir le rapport
        </ButtonLink>
      )}
    </>
  )

  return (
    <AppPage>
      <FlowSteps current={finished ? 5 : 4} />
      <PageHeader
        title={titles[job.status] ?? `Nettoyage n° ${job.id}`}
        description={
          job.running
            ? 'Ne clique pas dans la fenêtre Chromium pendant le nettoyage.'
            : `Nettoyage n° ${job.id}`
        }
        actions={actions}
      />
      <div className="space-y-4">
        <Card padding="lg">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <JobStatusBadge status={job.status} />
            {job.running && (
              <span className="flex items-center gap-2 text-small text-fg-muted">
                <LiveDot />
                Lot en cours de traitement
              </span>
            )}
          </div>
          <div className="mt-6" aria-live="polite">
            <div className="flex items-baseline justify-between gap-4">
              <p className="text-small text-fg-muted">
                {plural(handled, 'like traité', 'likes traités')} sur {handled + job.to_process}
              </p>
              <p className="text-h3 text-fg tabular-nums">
                {percent(handled, handled + job.to_process)} %
              </p>
            </div>
            <div className="mt-3">
              <ProgressBar
                value={percent(handled, handled + job.to_process)}
                label="Likes traités"
              />
            </div>
          </div>
          <dl className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Retirés" value={done} />
            <Stat label="Échecs" value={failed} />
            <Stat label="Introuvables" value={skipped} />
            <Stat label="Vitesse" value={rate ? `${rate.toFixed(1)} par min` : 'En attente'} />
            <Stat
              label="Temps restant"
              value={remaining === null ? 'En attente' : `≈ ${formatDuration(remaining)}`}
            />
          </dl>
          <p className="mt-4 text-small text-fg-muted">
            Vitesse et temps restant sont calculés après le premier lot, pauses comprises. La limite
            quotidienne peut interrompre le nettoyage avant la fin.
          </p>
        </Card>

        {actionError && <Alert tone="danger">{actionError}</Alert>}
        {run.end?.data.result ? (
          <EndMessage event={run.end} />
        ) : (
          !job.running &&
          job.status === 'paused' && <Alert tone="warning">{stopAdvice.user_pause}</Alert>
        )}

        <Card padding="lg">
          <h2 className="text-h3 text-fg">Journal</h2>
          {run.log.length === 0 ? (
            <p className="mt-2 text-small text-fg-muted">
              Aucune exécution suivie depuis l’ouverture de cette page.
            </p>
          ) : (
            <ol className="mt-4 space-y-2" aria-live="polite">
              {run.log.map((line) => (
                <li key={line.key} className="flex animate-fade-up gap-4 text-small">
                  <time className="text-fg-muted tabular-nums">{line.time}</time>
                  <span className="text-fg">{line.text}</span>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>

      <ConfirmDialog
        open={confirmStop}
        title="Arrêter définitivement ce nettoyage ?"
        confirmLabel="Arrêter le nettoyage"
        danger
        busy={action === 'stop'}
        onConfirm={() => void stop()}
        onCancel={() => setConfirmStop(false)}
      >
        Les likes non encore traités ne seront jamais retirés, et ce nettoyage ne pourra pas être
        repris. Pour une simple interruption, préfère « Mettre en pause ».
      </ConfirmDialog>
    </AppPage>
  )
}

function EndMessage({ event }: { event: Extract<JobEvent, { type: 'end' }> }) {
  const reason = event.data.result?.reason
  const advice = reason ? stopAdvice[reason] : undefined
  return (
    <Alert tone={event.data.ok ? 'success' : 'warning'} title={event.data.message}>
      {advice && <p>{advice}</p>}
      {event.data.result?.detail && <p className="mt-1">Détail : {event.data.result.detail}</p>}
    </Alert>
  )
}

interface LogLine {
  key: string
  time: string
  text: string
}

const timeFormat = new Intl.DateTimeFormat('fr-FR', { timeStyle: 'medium' })

/** Événements de l'exécution suivie : lots, fin et lignes de journal (plus récentes en haut). */
function currentRun(events: JobEvent[]) {
  const startedAt =
    events.find((event) => event.type === 'status')?.at ?? events[0]?.at ?? Date.now()
  const batches: { total: number; at: number }[] = []
  const log: LogLine[] = []
  let end: Extract<JobEvent, { type: 'end' }> | undefined
  events.forEach((event, index) => {
    const time = timeFormat.format(event.at)
    if (event.type === 'status') log.push({ key: `${index}`, time, text: 'Exécution lancée.' })
    if (event.type === 'batch') {
      batches.push({ total: event.data.total, at: event.at })
      log.push({
        key: `${index}`,
        time,
        text: `Lot retiré : ${plural(event.data.removed, 'like')} (total ${event.data.total}).`,
      })
    }
    if (event.type === 'end') {
      end = event
      // Sans résultat, « end » décrit seulement l'état : ce n'est pas une étape du journal.
      if (event.data.result) log.push({ key: `${index}`, time, text: event.data.message })
    }
  })
  return { startedAt, batches, end, log: log.reverse() }
}
