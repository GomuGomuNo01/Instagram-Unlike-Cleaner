import { Link } from 'react-router'

import { Logo } from './Header'
import { navigation } from './navigation'

const REPOSITORY = 'https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner'

export function Footer() {
  return (
    <footer className="border-t border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo />
          <p className="text-small mt-4 max-w-sm">
            Nettoie ton historique de « J’aime » Instagram en gardant la main sur chaque étape. Tout
            reste sur ton ordinateur, aucun mot de passe n’est lu ni stocké.
          </p>
        </div>
        <nav aria-label="Liens du pied de page">
          <h2 className="text-sm font-semibold">Navigation</h2>
          <ul className="mt-4 space-y-2">
            {[{ to: '/', label: 'Accueil' }, ...navigation].map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="text-small hover:text-zinc-900 dark:hover:text-white">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div>
          <h2 className="text-sm font-semibold">Informations</h2>
          <ul className="text-small mt-4 space-y-2">
            <li>Projet indépendant, sans lien avec Instagram ni Meta.</li>
            <li>Données 100 % locales.</li>
            <li>
              <a
                href={REPOSITORY}
                target="_blank"
                rel="noreferrer"
                className="underline hover:text-zinc-900 dark:hover:text-white"
              >
                Code source et contact sur GitHub
              </a>
            </li>
          </ul>
        </div>
      </div>
      <p className="border-t border-zinc-200 px-4 py-6 text-center text-xs text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
        © 2026 IUC. Instagram est une marque de Meta Platforms, Inc.
      </p>
    </footer>
  )
}
