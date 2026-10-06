import { useEffect, useRef, useState } from 'react'

import { api, errorMessage, unwrap } from '../api/client'
import type { SessionStatus } from '../api/types'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { ArrowRightIcon, LockIcon } from '../components/icons'
import {
  Alert,
  Button,
  ButtonLink,
  Card,
  LiveDot,
  PageHeader,
  Skeleton,
  SkeletonBlock,
  useToast,
} from '../components/ui'
import { codespaceDesktopUrl } from '../lib/codespaces'

const POLL_MS = 2000

/** Connexion : ouvre le navigateur piloté et suit la connexion faite par l'utilisateur. */
export function LoginPage() {
  const toast = useToast()
  const [status, setStatus] = useState<SessionStatus | null>(null)
  const [opening, setOpening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wasLoggedIn = useRef<boolean | null>(null)
  const desktop = codespaceDesktopUrl()

  useEffect(() => {
    let active = true
    const poll = () =>
      unwrap(api.GET('/api/session/status')).then(
        (loaded) => {
          if (!active) return
          // Connexion détectée pendant que l'écran était ouvert : on le signale.
          if (wasLoggedIn.current === false && loaded.logged_in) {
            toast({ title: 'Connexion détectée', description: 'Tu peux choisir tes critères.' })
          }
          wasLoggedIn.current = loaded.logged_in
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
  }, [toast])

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
    <ButtonLink to="/filtres" size="lg" trailingIcon={<ArrowRightIcon />}>
      Choisir les critères
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
      {desktop && (
        <Alert title="Tu utilises IUC dans GitHub Codespaces" className="mb-4">
          <p>
            La fenêtre Chromium s’affiche dans le bureau distant de ton Codespace. Ouvre-le dans un
            autre onglet, clique ici sur « Ouvrir Instagram », puis connecte-toi dans ce bureau.
          </p>
          <p className="mt-2">
            <a className="link" href={desktop} target="_blank" rel="noreferrer">
              Ouvrir le bureau distant
            </a>
          </p>
        </Alert>
      )}
      <Card padding="lg">
        <div aria-live="polite" className="space-y-4">
          <SessionMessage status={status} />
          {error && <Alert tone="danger">{error}</Alert>}
        </div>
        <p className="mt-6 flex items-center gap-3 border-t border-border pt-6 text-small text-fg-muted">
          <LockIcon className="h-5 w-5 text-primary-strong" />
          Ton mot de passe ne passe jamais par IUC. La session reste dans le dossier d’IUC,
          {desktop ? ' dans ton Codespace, que toi seul contrôles.' : ' sur ton ordinateur.'}
        </p>
      </Card>
    </AppPage>
  )
}

function SessionMessage({ status }: { status: SessionStatus | null }) {
  if (!status) {
    return (
      <SkeletonBlock label="Vérification de la session…">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="mt-3 h-12 w-full" />
      </SkeletonBlock>
    )
  }
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
      <p className="flex items-center gap-3 text-small font-medium text-fg">
        <LiveDot tone="primary" />
        En attente de ta connexion…
      </p>
      <Alert title="Connecte-toi dans la fenêtre Chromium">
        Saisis tes identifiants directement sur la page d’Instagram, double authentification
        comprise. Cette page se met à jour toute seule.
      </Alert>
    </div>
  )
}
