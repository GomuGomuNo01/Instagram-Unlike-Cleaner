import { useEffect, useState } from 'react'

import { api, errorMessage, unwrap } from '../api/client'
import type { UpdateInfo } from '../api/types'
import { CloseIcon, DownloadIcon } from './icons'
import { Button } from './ui'

type Step = 'idle' | 'installing' | 'restarting'

const TEXT = 'min-w-0 basis-full sm:flex-1 sm:basis-0'
const Icon = () => (
  <DownloadIcon className="mr-2 inline-block h-4 w-4 align-text-bottom text-info-strong" />
)

/** Bandeau de l'application Windows quand une version plus récente est publiée sur GitHub.
 * Version installée : mise à jour en un clic (téléchargement vérifié, installation, relance) ;
 * version portable : lien vers la nouvelle archive. */
export function UpdateBanner() {
  const [info, setInfo] = useState<UpdateInfo | null>(null)
  const [step, setStep] = useState<Step>('idle')
  const [error, setError] = useState<string | null>(null)
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    let active = true
    unwrap(api.GET('/api/update')).then(
      (result) => active && setInfo(result),
      () => {
        // Pas de jeton ou GitHub injoignable : rien à signaler, IUC fonctionne normalement.
      },
    )
    return () => {
      active = false
    }
  }, [])

  if (!info?.available || hidden) return null

  const install = async () => {
    setStep('installing')
    setError(null)
    try {
      await unwrap(api.POST('/api/update/install'))
      setStep('restarting')
    } catch (failure) {
      setError(errorMessage(failure))
      setStep('idle')
    }
  }

  return (
    // Au-dessus de la page, comme le bandeau de la démo (le haut de l'accueil remonte dessous).
    <div className="relative z-10 border-b border-info-border bg-info-soft text-info-fg">
      <div className="mx-auto flex max-w-app flex-wrap items-center gap-3 px-4 py-3 text-small sm:px-6 lg:px-8">
        {step === 'restarting' ? (
          <p role="status" className={TEXT}>
            <Icon />
            <strong className="font-semibold">Installation d’IUC {info.latest}</strong> : IUC se
            ferme puis se rouvre tout seul dans un nouvel onglet, d’ici une minute. Tu peux fermer
            celui-ci.
          </p>
        ) : (
          <>
            {/* Sur mobile, le texte prend toute la largeur et les boutons passent dessous. */}
            <p className={TEXT}>
              <Icon />
              <strong className="font-semibold">IUC {info.latest} est disponible</strong> (tu as la{' '}
              {info.current}).{' '}
              {info.mode === 'installer' &&
                'Un nettoyage en cours passe en pause ; tes données sont gardées. '}
              {info.mode === 'source' && 'Mets à jour le code avec `git pull`. '}
              <a className="link" href={info.release_url} target="_blank" rel="noreferrer">
                Voir les nouveautés
              </a>
            </p>
            {info.mode === 'installer' && (
              <Button onClick={install} loading={step === 'installing'}>
                {step === 'installing' ? 'Téléchargement et vérification…' : 'Mettre à jour'}
              </Button>
            )}
            {info.mode === 'portable' && info.download_url && (
              <a href={info.download_url} download className="btn btn-primary">
                Télécharger la version portable
              </a>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setHidden(true)}
              disabled={step === 'installing'}
              aria-label="Masquer jusqu’au prochain démarrage"
              title="Plus tard"
            >
              <CloseIcon />
            </Button>
            {error && (
              <p role="alert" className="w-full text-danger-strong">
                {error}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
