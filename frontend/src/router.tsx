import type { RouteObject } from 'react-router'

import { Layout } from './components/Layout'
import { RequireConsent } from './components/RequireConsent'
import { HomePage } from './pages/HomePage'
import {
  ConsentPage,
  FiltersPage,
  JobsPage,
  LoginPage,
  PreviewPage,
  ReportPage,
  TrackingPage,
} from './pages/lazyPages'
import { NotFoundPage } from './pages/NotFoundPage'

/** Parcours : accueil, avertissement, connexion, critères, aperçu, suivi, rapport. */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'commencer', element: <ConsentPage /> },
      {
        element: <RequireConsent />,
        children: [
          { path: 'connexion', element: <LoginPage /> },
          { path: 'filtres', element: <FiltersPage /> },
          { path: 'nettoyages', element: <JobsPage /> },
          { path: 'nettoyages/:jobId/apercu', element: <PreviewPage /> },
          { path: 'nettoyages/:jobId/suivi', element: <TrackingPage /> },
          { path: 'nettoyages/:jobId/rapport', element: <ReportPage /> },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
