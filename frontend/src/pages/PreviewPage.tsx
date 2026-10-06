import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { api, errorMessage, unwrap } from '../api/client'
import { useJobEvents } from '../api/events'
import type { Item, ItemsPage, Job } from '../api/types'
import { parseJobId, useJob } from '../api/useJob'
import { Avatar } from '../components/Avatar'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { ArrowRightIcon } from '../components/icons'
import { ItemStatusBadge, JobStatusBadge } from '../components/StatusBadge'
import {
  Alert,
  Button,
  ButtonLink,
  Card,
  Checkbox,
  ConfirmDialog,
  Field,
  LiveDot,
  PageHeader,
  ProgressBar,
  Skeleton,
  SkeletonBlock,
  Switch,
  TextLink,
  useToast,
} from '../components/ui'
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
          <PreviewSkeleton />
        )
      ) : collecting ? (
        <>
          <PageHeader
            title="Collecte de tes likes"
            description="IUC parcourt ta page des likes. Ne clique pas dans la fenêtre Chromium pendant ce temps."
          />
          <Card padding="lg">
            <p aria-live="polite" className="flex items-center gap-3 text-body font-medium text-fg">
              <LiveDot tone="primary" />
              {plural(scanned, 'like lu', 'likes lus')} pour l’instant…
            </p>
            <div className="mt-4">
              <ProgressBar value={0} indeterminate label="Collecte en cours" />
            </div>
            <p className="mt-4 text-small text-fg-muted">
              La liste s’affichera ici dès la fin de la collecte. Compte environ une minute pour
              cent likes.
            </p>
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

function PreviewSkeleton() {
  return (
    <SkeletonBlock label="Chargement de l’aperçu…">
      <Skeleton className="h-10 w-3/4 max-w-text" />
      <Skeleton className="mt-4 h-5 w-1/2 max-w-text" />
      <Skeleton className="mt-8 h-32 w-full rounded-xl" />
      <RowsSkeleton />
    </SkeletonBlock>
  )
}

function RowsSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="mt-4 space-y-3">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-center gap-4 px-4 py-2">
          <Skeleton className="h-5 w-5 rounded-xs" />
          <Skeleton className="h-9 w-9 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-64 max-w-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

function ItemsReview({ job, onJobChange }: { job: Job; onJobChange: (job: Job) => void }) {
  const navigate = useNavigate()
  const toast = useToast()
  const [offset, setOffset] = useState(0)
  const [version, setVersion] = useState(0)
  const [page, setPage] = useState<ItemsPage | null>(null)
  const [loadingPage, setLoadingPage] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState<'check' | 'uncheck' | 'item' | 'launch' | null>(null)
  const [limited, setLimited] = useState(false)
  const [limit, setLimit] = useState('')
  const [confirming, setConfirming] = useState(false)
  const editable = job.status === 'ready' || job.status === 'paused'

  useEffect(() => {
    let active = true
    unwrap(
      api.GET('/api/jobs/{job_id}/items', {
        params: { path: { job_id: job.id }, query: { offset, limit: PAGE_SIZE } },
      }),
    )
      .then(
        (items) => {
          if (active) setPage(items)
        },
        (failure: unknown) => {
          if (active) setError(errorMessage(failure))
        },
      )
      .finally(() => {
        if (active) setLoadingPage(false)
      })
    return () => {
      active = false
    }
  }, [job.id, offset, version])

  const changePage = (next: number) => {
    setLoadingPage(true)
    setOffset(next)
  }

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

  const run = async (kind: 'check' | 'uncheck' | 'item', task: () => Promise<void>) => {
    setWorking(kind)
    try {
      await task()
      setError(null)
      return true
    } catch (failure) {
      setError(errorMessage(failure))
      return false
    } finally {
      setWorking(null)
    }
  }

  const setAll = async (excluded: boolean) => {
    const ok = await run(excluded ? 'uncheck' : 'check', async () => {
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
    if (ok) {
      toast({
        title: excluded ? 'Tous les likes sont décochés' : 'Tous les likes sont cochés',
        description: excluded
          ? 'Coche ceux que tu veux retirer.'
          : 'Décoche ceux que tu veux garder.',
      })
    }
  }

  const launch = async () => {
    setWorking('launch')
    try {
      const body = limited && limit ? { limit: Number(limit) } : {}
      const params = { path: { job_id: job.id } }
      if (job.status === 'paused') {
        await unwrap(api.POST('/api/jobs/{job_id}/resume', { params, body }))
      } else {
        await unwrap(api.POST('/api/jobs/{job_id}/start', { params, body }))
      }
      navigate(`/nettoyages/${job.id}/suivi`, { viewTransition: true })
    } catch (failure) {
      setError(errorMessage(failure))
      setConfirming(false)
    } finally {
      setWorking(null)
    }
  }

  const limitInvalid =
    limited && limit !== '' && !(Number.isInteger(Number(limit)) && Number(limit) >= 1)
  const planned =
    limited && limit && !limitInvalid ? Math.min(Number(limit), job.to_process) : job.to_process
  const total = page?.total ?? 0
  const kept = job.counts.excluded ?? 0
  const action = editable ? (
    <Button
      size="lg"
      onClick={() => setConfirming(true)}
      disabled={job.to_process === 0 || limitInvalid}
      trailingIcon={<ArrowRightIcon />}
    >
      {job.status === 'paused' ? 'Reprendre le nettoyage' : 'Lancer le nettoyage'}
    </Button>
  ) : job.running ? (
    <ButtonLink to={`/nettoyages/${job.id}/suivi`} size="lg" trailingIcon={<ArrowRightIcon />}>
      Suivre le nettoyage
    </ButtonLink>
  ) : (
    <ButtonLink to={`/nettoyages/${job.id}/rapport`} size="lg" trailingIcon={<ArrowRightIcon />}>
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
      <div className="space-y-4">
        <Card padding="lg">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div aria-live="polite">
              <div className="flex items-center gap-3">
                <JobStatusBadge status={job.status} />
                <span className="text-small text-fg-muted">Nettoyage n° {job.id}</span>
              </div>
              <p className="mt-3 text-h2 text-fg">
                <span key={job.to_process} className="inline-block animate-value tabular-nums">
                  {job.to_process}
                </span>{' '}
                <span className="text-h3 text-fg-muted">
                  {job.to_process > 1 ? 'likes seront retirés' : 'like sera retiré'}
                </span>
              </p>
              <p className="mt-1 text-small text-fg-muted">
                sur {plural(total, 'like collecté', 'likes collectés')},{' '}
                {plural(kept, 'gardé', 'gardés')}
              </p>
            </div>
            {editable && (
              <div className="flex flex-col gap-3 sm:flex-row">
                <Button
                  variant="secondary"
                  onClick={() => void setAll(false)}
                  loading={working === 'check'}
                  disabled={working !== null}
                >
                  Tout cocher
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => void setAll(true)}
                  loading={working === 'uncheck'}
                  disabled={working !== null}
                >
                  Tout décocher
                </Button>
              </div>
            )}
          </div>
          {editable && (
            <div className="mt-6 border-t border-border pt-6">
              <Switch
                checked={limited}
                onChange={setLimited}
                label="Limiter ce lancement"
                description="Utile pour un premier essai : seuls les premiers likes de la liste seront retirés."
              />
              {limited && (
                <Field
                  id="limite"
                  label="Retirer au maximum"
                  error={
                    limitInvalid
                      ? 'Indique un nombre entier supérieur à 0, ou laisse vide.'
                      : undefined
                  }
                  className="mt-4 animate-fade-up"
                >
                  {(aria) => (
                    <input
                      {...aria}
                      type="number"
                      min={1}
                      inputMode="numeric"
                      placeholder="Par exemple 25"
                      value={limit}
                      onChange={(event) => setLimit(event.target.value)}
                      className="input sm:max-w-48"
                    />
                  )}
                </Field>
              )}
            </div>
          )}
        </Card>

        {error && <Alert tone="danger">{error}</Alert>}

        {page ? (
          <Card padding="none" className="overflow-hidden">
            <ul
              aria-label="Likes collectés"
              aria-busy={loadingPage || undefined}
              className={`divide-y divide-border transition-opacity duration-component ${
                loadingPage ? 'opacity-50' : ''
              }`}
            >
              {page.items.map((item) => (
                <ItemRow
                  key={item.id}
                  item={item}
                  editable={editable && working === null}
                  onToggle={(excluded) => void run('item', () => setExcluded([item.id], excluded))}
                />
              ))}
              {page.items.length === 0 && (
                <li className="px-6 py-12 text-center text-small text-fg-muted">
                  Instagram n’affiche aucun like avec ce filtre.
                </li>
              )}
            </ul>
            <nav
              aria-label="Pages de la liste"
              className="flex items-center justify-between gap-4 border-t border-border bg-surface-muted p-4"
            >
              <Button
                variant="secondary"
                onClick={() => changePage(offset - PAGE_SIZE)}
                disabled={offset === 0 || loadingPage}
              >
                Précédent
              </Button>
              <span className="text-small text-fg-muted tabular-nums">
                {total === 0 ? 0 : offset + 1} à {Math.min(offset + PAGE_SIZE, total)} sur {total}
              </span>
              <Button
                variant="secondary"
                onClick={() => changePage(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total || loadingPage}
              >
                Suivant
              </Button>
            </nav>
          </Card>
        ) : (
          !error && (
            <Card padding="none">
              <SkeletonBlock label="Chargement de la liste…">
                <RowsSkeleton />
              </SkeletonBlock>
            </Card>
          )
        )}

        {job.status === 'completed' || job.status === 'stopped' ? (
          <p className="text-small text-fg-muted">
            Ce nettoyage est terminé.{' '}
            <TextLink to={`/nettoyages/${job.id}/rapport`}>Voir le rapport</TextLink>
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
        className={`flex min-h-16 items-center gap-4 px-4 py-3 transition-colors sm:px-6 ${
          editable && toggleable ? 'cursor-pointer hover:bg-fill' : 'cursor-default'
        } ${item.status === 'excluded' ? 'bg-surface-muted' : ''}`}
      >
        <Checkbox
          checked={checked}
          disabled={!editable || !toggleable}
          onChange={(event) => onToggle(!event.target.checked)}
          aria-label={`Retirer le like n° ${item.rank} (${author})`}
        />
        <Avatar author={item.author} />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium text-fg">{author}</span>
          <span className="block truncate text-small text-fg-muted">
            {kind}, partagée le {formatDay(item.shared_on)}, n° {item.rank}
          </span>
          {item.error && <span className="block text-small text-danger-strong">{item.error}</span>}
        </span>
        {(!checked || !toggleable) && (
          <span className="animate-fade-in">
            <ItemStatusBadge status={item.status} />
          </span>
        )}
      </label>
    </li>
  )
}
