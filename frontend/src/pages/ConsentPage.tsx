import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router'

import { AppPage } from '../components/Layout'
import { AlertIcon, ArrowRightIcon, ShieldIcon } from '../components/icons'
import { Button, ButtonLink, Card, Checkbox, PageHeader } from '../components/ui'
import { giveConsent, hasConsent } from '../lib/preferences'

const risks = [
  'Les conditions d’utilisation d’Instagram n’autorisent pas l’automatisation : un blocage temporaire de l’action « Je n’aime plus » est possible, une suspension plus rare.',
  'Teste d’abord sur un compte secondaire, avec de petits volumes.',
  'Retirer un like efface la trace visible, pas ce que l’algorithme a déjà appris de ton comportement passé.',
]

const commitments = [
  'Aucun mot de passe lu, demandé ou stocké.',
  'Aucune donnée envoyée ailleurs que sur ton ordinateur.',
  'Aucun like retiré sans ta validation dans l’aperçu.',
  'Arrêt immédiat au moindre signal d’Instagram.',
]

/** Avertissement à accepter avant le premier nettoyage (consentement bloquant). */
export function ConsentPage() {
  const navigate = useNavigate()
  const [accepted, setAccepted] = useState(false)

  if (hasConsent()) return <Navigate to="/connexion" replace />

  const start = () => {
    giveConsent()
    navigate('/connexion', { viewTransition: true })
  }

  return (
    <AppPage>
      <PageHeader
        eyebrow="Avant de commencer"
        title="Quelques points importants"
        description="Prends une minute pour les lire : ils conditionnent le bon usage d’IUC."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-warning-border bg-warning-soft">
          <h2 className="flex items-center gap-3 text-h3 text-warning-fg">
            <AlertIcon className="h-6 w-6 text-warning-strong" />
            Les risques
          </h2>
          <ul className="mt-4 space-y-3 text-body text-warning-fg">
            {risks.map((risk) => (
              <li key={risk} className="flex gap-3">
                <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-warning-strong" />
                {risk}
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="flex items-center gap-3 text-h3 text-fg">
            <ShieldIcon className="h-6 w-6 text-success-strong" />
            Nos engagements
          </h2>
          <ul className="mt-4 space-y-3 text-body text-fg-muted">
            {commitments.map((commitment) => (
              <li key={commitment} className="flex gap-3">
                <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-success-strong" />
                {commitment}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="mt-4">
        <label className="flex min-h-11 cursor-pointer items-start gap-3">
          <Checkbox
            checked={accepted}
            onChange={(event) => setAccepted(event.target.checked)}
            className="mt-1"
          />
          <span className="text-body text-fg">
            J’ai compris ces risques et j’utilise IUC uniquement sur mon propre compte Instagram.
          </span>
        </label>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <ButtonLink to="/" variant="secondary">
            Revenir à l’accueil
          </ButtonLink>
          <Button onClick={start} disabled={!accepted} trailingIcon={<ArrowRightIcon />}>
            J’accepte et je me connecte
          </Button>
        </div>
      </Card>
    </AppPage>
  )
}
