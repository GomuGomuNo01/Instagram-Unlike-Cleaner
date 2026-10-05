import { Logo } from './Header'
import { ArrowUpIcon } from './icons'
import { jobsLink, REPOSITORY, sections } from './navigation'
import { AppLink } from './ui'

const linkClass =
  'inline-flex min-h-11 items-center text-small text-fg-muted transition-colors hover:text-fg sm:min-h-0 sm:py-1'

export function Footer() {
  return (
    <footer className="border-t border-border bg-canvas-subtle">
      <div className="mx-auto grid w-full max-w-page gap-12 px-4 py-16 sm:px-6 md:grid-cols-12 lg:px-8">
        <div className="md:col-span-5">
          <Logo />
          <p className="mt-4 max-w-text text-small text-fg-muted">
            Nettoie ton historique de « J’aime » Instagram en gardant la main sur chaque étape. Tout
            reste sur ton ordinateur, aucun mot de passe n’est lu ni stocké.
          </p>
        </div>
        <nav aria-label="Pied de page" className="grid gap-8 sm:grid-cols-3 md:col-span-7">
          <div>
            <h2 className="text-small font-semibold text-fg">Découvrir</h2>
            <ul className="mt-3">
              {sections.map((section) => (
                <li key={section.id}>
                  <AppLink to={`/#${section.id}`} className={linkClass}>
                    {section.label}
                  </AppLink>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="text-small font-semibold text-fg">Application</h2>
            <ul className="mt-3">
              <li>
                <AppLink to="/commencer" className={linkClass}>
                  Commencer un nettoyage
                </AppLink>
              </li>
              <li>
                <AppLink to={jobsLink.to} className={linkClass}>
                  {jobsLink.label}
                </AppLink>
              </li>
            </ul>
          </div>
          <div>
            <h2 className="text-small font-semibold text-fg">Contact et légal</h2>
            <ul className="mt-3">
              <li>
                <a href={REPOSITORY} target="_blank" rel="noreferrer" className={linkClass}>
                  Code source et contact (GitHub)
                </a>
              </li>
              <li className="py-1 text-small text-fg-muted">Données 100 % locales</li>
              <li className="py-1 text-small text-fg-muted">
                Projet indépendant, sans lien avec Instagram ni Meta
              </li>
            </ul>
          </div>
        </nav>
      </div>
      <div className="border-t border-border">
        <div className="mx-auto flex w-full max-w-page flex-col-reverse items-center justify-between gap-4 px-4 py-6 sm:flex-row sm:px-6 lg:px-8">
          <p className="text-caption text-fg-muted">
            © 2026 IUC. Instagram est une marque de Meta Platforms, Inc.
          </p>
          <button
            type="button"
            onClick={() => window.scrollTo({ top: 0 })}
            className="btn btn-ghost"
          >
            <ArrowUpIcon className="h-4 w-4" />
            Haut de page
          </button>
        </div>
      </div>
    </footer>
  )
}
