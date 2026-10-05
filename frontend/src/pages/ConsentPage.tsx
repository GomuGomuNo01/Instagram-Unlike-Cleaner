import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router'

import { AppPage } from '../components/Layout'
import { AlertIcon, ShieldIcon } from '../components/icons'
import { Button, ButtonLink, Card, PageHeader } from '../components/ui'
import { giveConsent, hasConsent } from '../lib/preferences'

/** Avertissement à accepter avant le premier nettoyage (consentement bloquant). */
export function ConsentPage() {
  const navigate = useNavigate()
  const [accepted, setAccepted] = useState(false)

  if (hasConsent()) return <Navigate to="/connexion" replace />

  const start = () => {
    giveConsent()
    navigate('/connexion')
  }

  return (
    <AppPage>
      <PageHeader
        eyebrow="Avant de commencer"
        title="Quelques points importants"
        description="Prends une minute pour les lire : ils conditionnent le bon usage d’IUC."
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="text-h3 flex items-center gap-3">
            <AlertIcon className="h-6 w-6 text-amber-700 dark:text-amber-300" />
            Les risques
          </h2>
          <ul className="text-body mt-4 list-disc space-y-2 pl-6">
            <li>
              Les conditions d’utilisation d’Instagram n’autorisent pas l’automatisation : un
              blocage temporaire de l’action « Je n’aime plus » est possible, une suspension plus
              rare.
            </li>
            <li>Teste d’abord sur un compte secondaire, avec de petits volumes.</li>
            <li>
              Retirer un like efface la trace visible, pas ce que l’algorithme a déjà appris de ton
              comportement passé.
            </li>
          </ul>
        </Card>
        <Card>
          <h2 className="text-h3 flex items-center gap-3">
            <ShieldIcon className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            Nos engagements
          </h2>
          <ul className="text-body mt-4 list-disc space-y-2 pl-6">
            <li>Aucun mot de passe lu, demandé ou stocké.</li>
            <li>Aucune donnée envoyée ailleurs que sur ton ordinateur.</li>
            <li>Aucun like retiré sans ta validation dans l’aperçu.</li>
            <li>Arrêt immédiat au moindre signal d’Instagram.</li>
          </ul>
        </Card>
      </div>

      <Card className="mt-6">
        <label className="flex min-h-11 cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(event) => setAccepted(event.target.checked)}
            className="mt-1 h-5 w-5 shrink-0 accent-indigo-600"
          />
          <span className="text-body">
            J’ai compris ces risques et j’utilise IUC uniquement sur mon propre compte Instagram.
          </span>
        </label>
        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <ButtonLink to="/" variant="secondary">
            Revenir à l’accueil
          </ButtonLink>
          <Button onClick={start} disabled={!accepted}>
            J’accepte et je me connecte
          </Button>
        </div>
      </Card>
    </AppPage>
  )
}
