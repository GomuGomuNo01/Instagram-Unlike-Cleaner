import { useEffect, useState } from 'react'

import { api, errorMessage, unwrap } from '../api/client'
import type { SessionStatus } from '../api/types'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { ArrowRightIcon } from '../components/icons'
import { Alert, Button, ButtonLink, Card, PageHeader, Spinner } from '../components/ui'

const POLL_MS = 2000

/** Connexion : ouvre le navigateur piloté et suit la connexion faite par l'utilisateur. */
export function LoginPage() {
  const [status, setStatus] = useState<SessionStatus | null>(null)
  const [opening, setOpening] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const poll = () =>
      unwrap(api.GET('/api/session/status')).then(
        (loaded) => {
          if (!active) return
          setStatus(loaded)
          setError(null)
        },
        (failure: unknown) => {
          if (active) setError(errorMessage(failure))
        },
      )
    void poll()
    const timer = window.setInterval(() => void poll(), POLL_MS)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const open = async () => {
    setOpening(true)
    try {
      setStatus(await unwrap(api.POST('/api/session/start')))
      setError(null)
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setOpening(false)
    }
  }

  const action = status?.logged_in ? (
    <ButtonLink to="/filtres" size="lg">
      Choisir les critères
      <ArrowRightIcon />
    </ButtonLink>
  ) : !status?.browser_open ? (
    <Button size="lg" onClick={() => void open()} loading={opening} disabled={!status}>
      {opening ? 'Ouverture d’Instagram…' : 'Ouvrir Instagram'}
    </Button>
  ) : null

  return (
    <AppPage>
      <FlowSteps current={1} />
      <PageHeader
        title="Connecte-toi à Instagram"
        description="IUC ouvre une fenêtre Chromium dédiée. Tu t’y connectes toi-même : aucun champ du formulaire n’est lu."
        actions={action}
      />
      <Card>
        <div aria-live="polite" className="space-y-4">
          <SessionMessage status={status} />
          {error && <Alert tone="danger">{error}</Alert>}
        </div>
      </Card>
    </AppPage>
  )
}

function SessionMessage({ status }: { status: SessionStatus | null }) {
  if (!status) return <Spinner label="Vérification de la session…" />
  if (!status.browser_open) {
    return (
      <Alert title="La fenêtre Instagram n’est pas ouverte">
        Clique sur « Ouvrir Instagram ». Si tu t’es déjà connecté avec IUC, ta session est reprise
        automatiquement.
      </Alert>
    )
  }
  if (status.challenge_required) {
    return (
      <Alert tone="warning" title="Vérification de sécurité demandée">
        Termine-la toi-même dans la fenêtre Chromium : IUC ne la contourne jamais.
      </Alert>
    )
  }
  if (status.consent_required) {
    return (
      <Alert tone="warning" title="Instagram attend un choix de ta part">
        Un écran de consentement (abonnement ou publicités) est affiché. Fais ton choix dans la
        fenêtre Chromium.
      </Alert>
    )
  }
  if (status.logged_in) {
    return (
      <Alert tone="success" title="Tu es connecté">
        Compte n° {status.account_id ?? 'inconnu'}. Garde la fenêtre Chromium ouverte : IUC s’en
        sert pour la suite.
        {status.busy && ' Une tâche est déjà en cours.'}
      </Alert>
    )
  }
  return (
    <div className="space-y-4">
      <Spinner label="En attente de ta connexion…" />
      <Alert title="Connecte-toi dans la fenêtre Chromium">
        Saisis tes identifiants directement sur la page d’Instagram, double authentification
        comprise. Cette page se met à jour toute seule.
      </Alert>
    </div>
  )
}
