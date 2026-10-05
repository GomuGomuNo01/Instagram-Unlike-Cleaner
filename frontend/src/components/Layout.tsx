import { Suspense, useEffect, type ReactNode } from 'react'
import { Outlet, useLocation } from 'react-router'

import { Footer } from './Footer'
import { Header } from './Header'
import { Spinner } from './ui'

export function Layout() {
  const { pathname, hash } = useLocation()

  // Ancre (« /#faq ») : défile jusqu'à la section ; nouvelle page : revient en haut.
  useEffect(() => {
    if (hash) {
      document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth' })
    } else {
      window.scrollTo(0, 0)
    }
  }, [pathname, hash])

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#contenu"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-3 focus:shadow-lg dark:focus:bg-zinc-900"
      >
        Aller au contenu
      </a>
      <Header />
      <main id="contenu" className="flex-1">
        <Suspense
          fallback={
            <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
              <Spinner label="Chargement…" />
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <Footer />
    </div>
  )
}

/** Conteneur des écrans de l'application (hors page d'accueil). */
export function AppPage({ children }: { children: ReactNode }) {
  return <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">{children}</div>
}
