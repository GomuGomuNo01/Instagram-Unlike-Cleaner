import { InfoIcon } from './icons'
import { WINDOWS_DOWNLOAD } from './navigation'

/** Bandeau de la démo en ligne : l'interface est la vraie, les données sont fictives. */
export function DemoBanner() {
  return (
    <div className="border-b border-info-border bg-info-soft text-info-fg">
      <p className="mx-auto flex max-w-app items-start gap-3 px-4 py-3 text-small sm:px-6 lg:px-8">
        <InfoIcon className="mt-1 h-4 w-4 shrink-0 text-info-strong" />
        <span>
          <strong className="font-semibold">Démo en ligne</strong> : la vraie interface d’IUC, sur
          des likes fictifs et en accéléré. Aucune connexion à Instagram, rien n’est enregistré.{' '}
          {/* Téléchargement direct de l'installeur Windows (Release la plus récente). */}
          <a className="link" href={WINDOWS_DOWNLOAD} download>
            Installer la vraie version
          </a>
        </span>
      </p>
    </div>
  )
}
