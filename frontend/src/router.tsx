import type { RouteObject } from 'react-router'

import { AppFallback, Layout } from './components/Layout'
import { RequireConsent } from './components/RequireConsent'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'

// Les écrans de l'application sont chargés à la demande : la page d'accueil reste légère.
// Le routeur attend l'écran avant de l'afficher, ce qui garde la transition fluide ; une
// fine barre signale l'attente si la connexion est lente.

/** Parcours : accueil, présentation, avertissement, connexion, critères, aperçu, suivi, rapport. */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    HydrateFallback: AppFallback,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: 'presentation',
        lazy: async () => ({
          Component: (await import('./pages/PresentationPage')).PresentationPage,
        }),
      },
      {
        path: 'commencer',
        lazy: async () => ({ Component: (await import('./pages/ConsentPage')).ConsentPage }),
      },
      {
        element: <RequireConsent />,
        children: [
          {
            path: 'connexion',
            lazy: async () => ({ Component: (await import('./pages/LoginPage')).LoginPage }),
          },
          {
            path: 'filtres',
            lazy: async () => ({ Component: (await import('./pages/FiltersPage')).FiltersPage }),
          },
          {
            path: 'nettoyages',
            lazy: async () => ({ Component: (await import('./pages/JobsPage')).JobsPage }),
          },
          {
            path: 'nettoyages/:jobId/apercu',
            lazy: async () => ({ Component: (await import('./pages/PreviewPage')).PreviewPage }),
          },
          {
            path: 'nettoyages/:jobId/suivi',
            lazy: async () => ({
              Component: (await import('./pages/TrackingPage')).TrackingPage,
            }),
          },
          {
            path: 'nettoyages/:jobId/rapport',
            lazy: async () => ({ Component: (await import('./pages/ReportPage')).ReportPage }),
          },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
