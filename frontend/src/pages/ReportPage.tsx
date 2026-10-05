import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { api, describeError, errorMessage, unwrap } from '../api/client'
import { getToken, TOKEN_HEADER } from '../api/token'
import type { JobReport } from '../api/types'
import { parseJobId } from '../api/useJob'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { DownloadIcon } from '../components/icons'
import { ItemStatusBadge, JobStatusBadge } from '../components/StatusBadge'
import { Alert, Button, Card, PageHeader, Spinner, Stat } from '../components/ui'
import { formatDateTime, formatDuration, plural } from '../lib/format'
import { NotFoundPage } from './NotFoundPage'

export function ReportPage() {
  const jobId = parseJobId(useParams().jobId)
  return jobId === null ? <NotFoundPage /> : <Report key={jobId} jobId={jobId} />
}

type Danger = 'session' | 'data'

/** Rapport final : bilan, échecs, export CSV et suppression des données locales. */
function Report({ jobId }: { jobId: number }) {
  const navigate = useNavigate()
  const [report, setReport] = useState<JobReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [danger, setDanger] = useState<Danger | null>(null)
  const [busy, setBusy] = useState<'csv' | Danger | null>(null)

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
    } finally {
      setBusy(null)
    }
  }

  const deleteLocal = async (target: Danger) => {
    setBusy(target)
    try {
      if (target === 'session') {
        await unwrap(api.DELETE('/api/session'))
        setNotice('Profil du navigateur supprimé : IUC n’est plus connecté à Instagram.')
      } else {
        await unwrap(api.DELETE('/api/data'))
        navigate('/', { replace: true })
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
        {error ? <Alert tone="danger">{error}</Alert> : <Spinner label="Chargement du rapport…" />}
      </AppPage>
    )
  }

  const counts = report.par_statut
  const toProcess = (counts.pending ?? 0) + (counts.selected ?? 0)
  const problems = report.likes.filter((line) => ['failed', 'skipped'].includes(line.statut))
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
          <Button variant="secondary" onClick={() => void downloadCsv()} loading={busy === 'csv'}>
            <DownloadIcon />
            Télécharger le CSV
          </Button>
        }
      />
      <div className="space-y-6">
        <Card>
          <JobStatusBadge status={report.statut} />
          <dl className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-6">
            <Stat label="Ciblés" value={report.likes_cibles} />
            <Stat label="Retirés" value={counts.done ?? 0} />
            <Stat label="Échecs" value={counts.failed ?? 0} />
            <Stat label="Introuvables" value={counts.skipped ?? 0} />
            <Stat label="Gardés" value={counts.excluded ?? 0} />
            <Stat label="À traiter" value={toProcess} />
          </dl>
        </Card>

        {error && <Alert tone="danger">{error}</Alert>}
        {notice && <Alert tone="success">{notice}</Alert>}

        <Card>
          <h2 className="text-h3">Échecs et likes introuvables</h2>
          {problems.length === 0 ? (
            <p className="text-small mt-2">Aucun : tous les likes traités ont été retirés.</p>
          ) : (
            <ul className="mt-4 divide-y divide-zinc-200 dark:divide-zinc-800">
              {problems.map((line) => (
                <li key={line.identifiant} className="flex flex-wrap items-center gap-3 py-3">
                  <span className="font-medium">
                    {line.auteur ? `@${line.auteur}` : 'Auteur inconnu'}
                  </span>
                  <span className="text-small">
                    {line.type}
                    {line.partagee_le && `, partagée le ${line.partagee_le}`}, n° {line.rang}
                  </span>
                  <ItemStatusBadge status={line.statut} />
                  {line.detail && <span className="text-small w-full">{line.detail}</span>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="border-red-200 dark:border-red-900/60">
          <h2 className="text-h3">Données locales</h2>
          <p className="text-small mt-1">
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
