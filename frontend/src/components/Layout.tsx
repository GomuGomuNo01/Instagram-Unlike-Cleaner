import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react'
import { Outlet, useLocation, useNavigation } from 'react-router'

import { prefersReducedMotion } from '../lib/motion'
import { Footer } from './Footer'
import { Header } from './Header'
import { Loading, ToastProvider } from './ui'

export function Layout() {
  const { pathname, hash } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const firstRender = useRef(true)

  // Avant l'affichage du nouvel écran (et donc avant sa transition) : une ancre défile
  // jusqu'à sa section, un nouvel écran repart du haut.
  useLayoutEffect(() => {
    if (hash) {
      document
        .getElementById(hash.slice(1))
        ?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
    } else {
      window.scrollTo({ top: 0, behavior: 'instant' })
    }
  }, [pathname, hash])

  // Après un changement d'écran, le focus revient au début du contenu (lecteurs d'écran).
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    if (!hash) mainRef.current?.focus({ preventScroll: true })
  }, [pathname, hash])

  return (
    <ToastProvider>
      <div className="flex min-h-dvh flex-col">
        <a
          href="#contenu"
          className="sr-only rounded-full bg-surface px-4 py-3 text-small font-semibold elevation-md focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-90"
        >
          Aller au contenu
        </a>
        <RouteProgress />
        <Header />
        <main id="contenu" ref={mainRef} tabIndex={-1} className="flex-1 pt-16 outline-none">
          <Outlet />
        </main>
        <Footer />
      </div>
    </ToastProvider>
  )
}

/** Fine barre en haut de l'écran pendant le chargement d'un écran (connexion lente). */
function RouteProgress() {
  const navigation = useNavigation()
  return (
    <div
      aria-hidden="true"
      data-active={navigation.state !== 'idle' || undefined}
      className="route-progress"
    />
  )
}

/** Affiché le temps de charger le premier écran demandé. */
export function AppFallback() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <Loading label="Chargement d’IUC…" />
    </div>
  )
}

/** Conteneur des écrans de l'application (hors page d'accueil). */
export function AppPage({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-app px-4 pt-8 pb-16 sm:px-6 sm:pt-12 sm:pb-24 lg:px-8">
      {children}
    </div>
  )
}
