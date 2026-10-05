import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { api, describeError, errorMessage, unwrap } from '../api/client'
import { getToken, TOKEN_HEADER } from '../api/token'
import type { JobReport, ReportLine } from '../api/types'
import { parseJobId } from '../api/useJob'
import { Avatar } from '../components/Avatar'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { DownloadIcon } from '../components/icons'
import { ItemStatusBadge, JobStatusBadge } from '../components/StatusBadge'
import {
  Alert,
  Button,
  Card,
  ConfirmDialog,
  PageHeader,
  Skeleton,
  SkeletonBlock,
  Stat,
  Tabs,
  useToast,
} from '../components/ui'
import { formatDateTime, formatDuration, plural } from '../lib/format'
import { NotFoundPage } from './NotFoundPage'

const SHOWN_LINES = 100 // au-delà, le CSV contient la liste complète
const SUCCESS_MS = 2500 // durée de l'état « téléchargé » du bouton

export function ReportPage() {
  const jobId = parseJobId(useParams().jobId)
  return jobId === null ? <NotFoundPage /> : <Report key={jobId} jobId={jobId} />
}

type Danger = 'session' | 'data'

/** Rapport final : bilan, likes à vérifier ou retirés, export CSV et données locales. */
function Report({ jobId }: { jobId: number }) {
  const navigate = useNavigate()
  const toast = useToast()
  const [report, setReport] = useState<JobReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [danger, setDanger] = useState<Danger | null>(null)
  const [busy, setBusy] = useState<'csv' | Danger | null>(null)
  const [downloaded, setDownloaded] = useState(false)

  useEffect(() => {
    let active = true
    unwrap(api.GET('/api/jobs/{job_id}/report', { params: { path: { job_id: jobId } } })).then(
      (loaded) => {
        if (active) setReport(loaded as unknown as JobReport)
      },
      (failure: unknown) => {
        if (active) setError(errorMessage(failure))
      },
    )
    return () => {
      active = false
    }
  }, [jobId])

  useEffect(() => {
    if (!downloaded) return
    const timer = window.setTimeout(() => setDownloaded(false), SUCCESS_MS)
    return () => window.clearTimeout(timer)
  }, [downloaded])

  const downloadCsv = async () => {
    setBusy('csv')
    try {
      // Téléchargement par fetch : le jeton part dans l'en-tête, pas dans l'adresse.
      const response = await fetch(`/api/jobs/${jobId}/report?format=csv`, {
        headers: { [TOKEN_HEADER]: getToken() ?? '' },
      })
      if (!response.ok) {
        setError(describeError(response.status, await response.json().catch(() => undefined)))
        return
      }
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = `rapport-${jobId}.csv`
      link.click()
      URL.revokeObjectURL(url)
      setDownloaded(true)
      toast({ title: 'Rapport téléchargé', description: `Fichier rapport-${jobId}.csv` })
    } finally {
      setBusy(null)
    }
  }

  const deleteLocal = async (target: Danger) => {
    setBusy(target)
    try {
      if (target === 'session') {
        await unwrap(api.DELETE('/api/session'))
        toast({
          title: 'Déconnecté d’Instagram',
          description: 'Le profil du navigateur est supprimé. Tes nettoyages sont conservés.',
        })
      } else {
        await unwrap(api.DELETE('/api/data'))
        toast({ title: 'Données locales supprimées' })
        navigate('/', { replace: true, viewTransition: true })
      }
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setBusy(null)
      setDanger(null)
    }
  }

  if (!report) {
    return (
      <AppPage>
        <FlowSteps current={5} />
        {error ? (
          <Alert tone="danger">{error}</Alert>
        ) : (
          <SkeletonBlock label="Chargement du rapport…">
            <Skeleton className="h-10 w-2/3 max-w-text" />
            <Skeleton className="mt-4 h-5 w-1/2 max-w-text" />
            <Skeleton className="mt-8 h-40 w-full rounded-xl" />
          </SkeletonBlock>
        )}
      </AppPage>
    )
  }

  const counts = report.par_statut
  const toProcess = (counts.pending ?? 0) + (counts.selected ?? 0)
  const problems = report.likes.filter((line) => ['failed', 'skipped'].includes(line.statut))
  const removed = report.likes.filter((line) => line.statut === 'done')
  return (
    <AppPage>
      <FlowSteps current={5} />
      <PageHeader
        title={`Rapport du nettoyage n° ${report.nettoyage}`}
        description={
          report.premiere_execution
            ? `Du ${formatDateTime(report.premiere_execution)} au ${report.fin ? formatDateTime(report.fin) : 'jour'}, ${formatDuration(report.duree_active_secondes)} d’activité en ${plural(report.executions, 'exécution')}.`
            : 'Ce nettoyage n’a pas encore été lancé.'
        }
        actions={
          <Button
            variant="secondary"
            onClick={() => void downloadCsv()}
            loading={busy === 'csv'}
            success={downloaded}
            icon={<DownloadIcon className="h-4 w-4" />}
          >
            {downloaded ? 'CSV téléchargé' : 'Télécharger le CSV'}
          </Button>
        }
      />
      <div className="space-y-4">
        <Card padding="lg">
          <JobStatusBadge status={report.statut} />
          <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Stat label="Ciblés" value={report.likes_cibles} />
            <Stat label="Retirés" value={counts.done ?? 0} />
            <Stat label="Échecs" value={counts.failed ?? 0} />
            <Stat label="Introuvables" value={counts.skipped ?? 0} />
            <Stat label="Gardés" value={counts.excluded ?? 0} />
            <Stat label="À traiter" value={toProcess} />
          </dl>
        </Card>

        {error && <Alert tone="danger">{error}</Alert>}

        <Card padding="lg">
          <Tabs
            label="Détail des likes"
            items={[
              {
                id: 'verifier',
                label: 'À vérifier',
                count: problems.length,
                content: (
                  <ReportLines
                    lines={problems}
                    empty="Aucun : tous les likes traités ont été retirés."
                  />
                ),
              },
              {
                id: 'retires',
                label: 'Retirés',
                count: removed.length,
                content: <ReportLines lines={removed} empty="Aucun like n’a encore été retiré." />,
              },
            ]}
          />
        </Card>

        <Card padding="lg" className="border-danger-border">
          <h2 className="text-h3 text-fg">Données locales</h2>
          <p className="mt-1 text-small text-fg-muted">
            Tout est stocké sur ton ordinateur, dans le dossier de données d’IUC.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Button variant="secondary" onClick={() => setDanger('session')}>
              Se déconnecter d’Instagram
            </Button>
            <Button variant="danger" onClick={() => setDanger('data')}>
              Supprimer mes données locales
            </Button>
          </div>
        </Card>
      </div>

      <ConfirmDialog
        open={danger !== null}
        title={
          danger === 'data'
            ? 'Supprimer toutes tes données locales ?'
            : 'Se déconnecter d’Instagram ?'
        }
        confirmLabel={danger === 'data' ? 'Tout supprimer' : 'Se déconnecter'}
        danger
        busy={busy === danger}
        requireText={danger === 'data' ? 'SUPPRIMER' : undefined}
        onConfirm={() => danger && void deleteLocal(danger)}
        onCancel={() => setDanger(null)}
      >
        {danger === 'data'
          ? 'L’historique de tous tes nettoyages, les rapports, les diagnostics, les journaux et la session Instagram seront définitivement supprimés. Cette action est irréversible.'
          : 'Le profil du navigateur est supprimé : il faudra te reconnecter à Instagram. Tes nettoyages et rapports sont conservés.'}
      </ConfirmDialog>
    </AppPage>
  )
}

function ReportLines({ lines, empty }: { lines: ReportLine[]; empty: string }) {
  if (lines.length === 0) return <p className="text-small text-fg-muted">{empty}</p>
  return (
    <>
      <ul className="divide-y divide-border">
        {lines.slice(0, SHOWN_LINES).map((line) => (
          <li key={line.identifiant} className="flex flex-wrap items-center gap-3 py-3">
            <Avatar author={line.auteur} />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium text-fg">
                {line.auteur ? `@${line.auteur}` : 'Auteur inconnu'}
              </span>
              <span className="block text-small text-fg-muted">
                {line.type}
                {line.partagee_le && `, partagée le ${line.partagee_le}`}, n° {line.rang}
              </span>
              {line.detail && <span className="block text-small text-fg-muted">{line.detail}</span>}
            </span>
            <ItemStatusBadge status={line.statut} />
          </li>
        ))}
      </ul>
      {lines.length > SHOWN_LINES && (
        <p className="mt-4 text-small text-fg-muted">
          {SHOWN_LINES} premiers likes affichés sur {lines.length} : le CSV contient la liste
          complète.
        </p>
      )}
    </>
  )
}
