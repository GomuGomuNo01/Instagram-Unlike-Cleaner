import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { api, errorMessage, unwrap } from '../api/client'
import { useJobEvents } from '../api/events'
import type { Item, ItemsPage, Job } from '../api/types'
import { parseJobId, useJob } from '../api/useJob'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { ItemStatusBadge, JobStatusBadge } from '../components/StatusBadge'
import { Alert, Button, ButtonLink, Card, inputClass, PageHeader, Spinner } from '../components/ui'
import { mediaKindLabels } from '../i18n/fr'
import { formatDay, plural } from '../lib/format'
import { NotFoundPage } from './NotFoundPage'

const PAGE_SIZE = 50
const ALL_PAGE_SIZE = 500 // maximum accepté par l'API
const TOGGLEABLE = new Set(['pending', 'selected', 'excluded'])

export function PreviewPage() {
  const jobId = parseJobId(useParams().jobId)
  return jobId === null ? <NotFoundPage /> : <Preview key={jobId} jobId={jobId} />
}

/** Aperçu : suit la collecte, puis liste les likes ciblés à cocher ou décocher. */
function Preview({ jobId }: { jobId: number }) {
  const { job, setJob, error, reload } = useJob(jobId)
  const collecting = job?.status === 'collecting'
  const { events, ended } = useJobEvents(jobId, collecting)

  useEffect(() => {
    if (ended) void reload()
  }, [ended, reload])

  const scanned = events.reduce(
    (count, event) => (event.type === 'progress' ? event.data.scanned : count),
    0,
  )
  const end = events.find((event) => event.type === 'end')

  return (
    <AppPage>
      <FlowSteps current={3} />
      {!job ? (
        error ? (
          <Alert tone="danger">{error}</Alert>
        ) : (
          <Spinner label="Chargement de l’aperçu…" />
        )
      ) : collecting ? (
        <>
          <PageHeader
            title="Collecte de tes likes"
            description="IUC parcourt ta page des likes. Ne clique pas dans la fenêtre Chromium pendant ce temps."
          />
          <Card>
            <div aria-live="polite">
              <Spinner label={`${plural(scanned, 'like lu', 'likes lus')} pour l’instant…`} />
            </div>
          </Card>
        </>
      ) : job.status === 'failed' ? (
        <>
          <PageHeader title="La collecte n’a pas abouti" />
          <Alert tone="danger">
            {end?.type === 'end' ? end.data.message : 'La collecte n’a pas pu aller au bout.'}
          </Alert>
          <ButtonLink to="/filtres" className="mt-6">
            Modifier les critères
          </ButtonLink>
        </>
      ) : (
        <ItemsReview job={job} onJobChange={setJob} />
      )}
    </AppPage>
  )
}

function ItemsReview({ job, onJobChange }: { job: Job; onJobChange: (job: Job) => void }) {
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const [version, setVersion] = useState(0)
  const [page, setPage] = useState<ItemsPage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState<'all' | 'item' | 'launch' | null>(null)
  const [limit, setLimit] = useState('')
  const [confirming, setConfirming] = useState(false)
  const editable = job.status === 'ready' || job.status === 'paused'

  useEffect(() => {
    let active = true
    unwrap(
      api.GET('/api/jobs/{job_id}/items', {
        params: { path: { job_id: job.id }, query: { offset, limit: PAGE_SIZE } },
      }),
    ).then(
      (items) => {
        if (active) setPage(items)
      },
      (failure: unknown) => {
        if (active) setError(errorMessage(failure))
      },
    )
    return () => {
      active = false
    }
  }, [job.id, offset, version])

  const setExcluded = async (itemIds: number[], excluded: boolean) => {
    for (let start = 0; start < itemIds.length; start += ALL_PAGE_SIZE) {
      const result = await unwrap(
        api.PATCH('/api/jobs/{job_id}/items', {
          params: { path: { job_id: job.id } },
          body: { item_ids: itemIds.slice(start, start + ALL_PAGE_SIZE), excluded },
        }),
      )
      onJobChange(result.job)
    }
    setVersion((value) => value + 1)
  }

  const run = async (kind: 'all' | 'item', task: () => Promise<void>) => {
    setWorking(kind)
    try {
      await task()
      setError(null)
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setWorking(null)
    }
  }

  const setAll = (excluded: boolean) =>
    run('all', async () => {
      const ids: number[] = []
      for (let start = 0; ; start += ALL_PAGE_SIZE) {
        const batch = await unwrap(
          api.GET('/api/jobs/{job_id}/items', {
            params: { path: { job_id: job.id }, query: { offset: start, limit: ALL_PAGE_SIZE } },
          }),
        )
        ids.push(...batch.items.filter((i) => TOGGLEABLE.has(i.status)).map((i) => i.id))
        if (start + ALL_PAGE_SIZE >= batch.total) break
      }
      await setExcluded(ids, excluded)
    })

  const launch = async () => {
    setWorking('launch')
    try {
      const body = limit ? { limit: Number(limit) } : {}
      const params = { path: { job_id: job.id } }
      if (job.status === 'paused') {
        await unwrap(api.POST('/api/jobs/{job_id}/resume', { params, body }))
      } else {
        await unwrap(api.POST('/api/jobs/{job_id}/start', { params, body }))
      }
      navigate(`/nettoyages/${job.id}/suivi`)
    } catch (failure) {
      setError(errorMessage(failure))
      setConfirming(false)
    } finally {
      setWorking(null)
    }
  }

  const planned = limit ? Math.min(Number(limit), job.to_process) : job.to_process
  const total = page?.total ?? 0
  const kept = job.counts.excluded ?? 0
  const action = editable ? (
    <Button size="lg" onClick={() => setConfirming(true)} disabled={job.to_process === 0}>
      {job.status === 'paused' ? 'Reprendre le nettoyage' : 'Lancer le nettoyage'}
    </Button>
  ) : job.running ? (
    <ButtonLink to={`/nettoyages/${job.id}/suivi`} size="lg">
      Suivre le nettoyage
    </ButtonLink>
  ) : (
    <ButtonLink to={`/nettoyages/${job.id}/rapport`} size="lg">
      Voir le rapport
    </ButtonLink>
  )

  return (
    <>
      <PageHeader
        title="Vérifie la liste avant le nettoyage"
        description="Décoche les likes que tu veux garder. Rien n’est retiré avant ton lancement."
        actions={action}
      />
      <div className="space-y-6">
        <Card>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div aria-live="polite">
              <div className="flex items-center gap-3">
                <JobStatusBadge status={job.status} />
                <span className="text-small">Nettoyage n° {job.id}</span>
              </div>
              <p className="mt-3 text-2xl font-semibold tracking-tight">
                {plural(job.to_process, 'like sera retiré', 'likes seront retirés')}
              </p>
              <p className="text-small mt-1">
                sur {plural(total, 'like collecté', 'likes collectés')},{' '}
                {plural(kept, 'gardé', 'gardés')}
              </p>
            </div>
            {editable && (
              <div className="flex flex-col gap-3 sm:flex-row">
                <Button
                  variant="secondary"
                  onClick={() => void setAll(false)}
                  loading={working === 'all'}
                  disabled={working !== null}
                >
                  Tout cocher
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => void setAll(true)}
                  disabled={working !== null}
                >
                  Tout décocher
                </Button>
              </div>
            )}
          </div>
          {editable && (
            <details className="mt-6 border-t border-zinc-200 pt-4 dark:border-zinc-800">
              <summary className="min-h-11 cursor-pointer py-2 text-sm font-medium">
                Options du lancement
              </summary>
              <label htmlFor="limite" className="mt-3 block text-sm font-medium">
                Retirer au maximum (facultatif)
              </label>
              <p className="text-small mt-1">
                Utile pour un premier essai : seuls les premiers likes de la liste seront retirés.
              </p>
              <input
                id="limite"
                type="number"
                min={1}
                inputMode="numeric"
                value={limit}
                onChange={(event) => setLimit(event.target.value)}
                className={`${inputClass} mt-2 sm:max-w-48`}
              />
            </details>
          )}
        </Card>

        {error && <Alert tone="danger">{error}</Alert>}

        {page ? (
          <Card className="p-0">
            <ul
              aria-label="Likes collectés"
              className="divide-y divide-zinc-200 dark:divide-zinc-800"
            >
              {page.items.map((item) => (
                <ItemRow
                  key={item.id}
                  item={item}
                  editable={editable && working === null}
                  onToggle={(excluded) => void run('item', () => setExcluded([item.id], excluded))}
                />
              ))}
            </ul>
            <nav
              aria-label="Pages de la liste"
              className="flex items-center justify-between gap-4 border-t border-zinc-200 p-4 dark:border-zinc-800"
            >
              <Button
                variant="secondary"
                onClick={() => setOffset(offset - PAGE_SIZE)}
                disabled={offset === 0}
              >
                Précédent
              </Button>
              <span className="text-small tabular-nums">
                {total === 0 ? 0 : offset + 1} à {Math.min(offset + PAGE_SIZE, total)} sur {total}
              </span>
              <Button
                variant="secondary"
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
              >
                Suivant
              </Button>
            </nav>
          </Card>
        ) : (
          <Spinner label="Chargement de la liste…" />
        )}

        {job.status === 'completed' || job.status === 'stopped' ? (
          <p className="text-small">
            Ce nettoyage est terminé.{' '}
            <Link to={`/nettoyages/${job.id}/rapport`} className="font-medium underline">
              Voir le rapport
            </Link>
          </p>
        ) : null}
      </div>

      <ConfirmDialog
        open={confirming}
        title={job.status === 'paused' ? 'Reprendre le nettoyage ?' : 'Lancer le nettoyage ?'}
        confirmLabel={`Retirer ${plural(planned, 'like')}`}
        danger
        busy={working === 'launch'}
        onConfirm={() => void launch()}
        onCancel={() => setConfirming(false)}
      >
        <p>
          IUC va retirer jusqu’à {plural(planned, 'like')} de ton compte Instagram, par lots et avec
          des pauses. Cette action modifie ton compte.
        </p>
        <p className="mt-2">Ne clique pas dans la fenêtre Chromium pendant le nettoyage.</p>
      </ConfirmDialog>
    </>
  )
}

function ItemRow({
  item,
  editable,
  onToggle,
}: {
  item: Item
  editable: boolean
  onToggle: (excluded: boolean) => void
}) {
  const toggleable = TOGGLEABLE.has(item.status)
  const checked = item.status === 'pending' || item.status === 'selected'
  const author = item.author ? `@${item.author}` : 'Auteur inconnu'
  const kind = item.media_kind ? mediaKindLabels[item.media_kind] : 'Type inconnu'
  return (
    <li>
      <label
        className={`flex min-h-16 items-center gap-4 px-4 py-3 sm:px-6 ${
          editable && toggleable
            ? 'cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/60'
            : 'cursor-default'
        }`}
      >
        <input
          type="checkbox"
          checked={checked}
          disabled={!editable || !toggleable}
          onChange={(event) => onToggle(!event.target.checked)}
          aria-label={`Retirer le like n° ${item.rank} (${author})`}
          className="h-5 w-5 shrink-0 accent-indigo-600"
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium">{author}</span>
          <span className="text-small block truncate">
            {kind}, partagée le {formatDay(item.shared_on)}, n° {item.rank}
          </span>
          {item.error && <span className="text-small block">{item.error}</span>}
        </span>
        {(!checked || !toggleable) && <ItemStatusBadge status={item.status} />}
      </label>
    </li>
  )
}
