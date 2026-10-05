import { lazy } from 'react'

// Écrans de l'application chargés à la demande : la page d'accueil reste légère.
export const ConsentPage = lazy(() =>
  import('./ConsentPage').then((m) => ({ default: m.ConsentPage })),
)
export const LoginPage = lazy(() => import('./LoginPage').then((m) => ({ default: m.LoginPage })))
export const FiltersPage = lazy(() =>
  import('./FiltersPage').then((m) => ({ default: m.FiltersPage })),
)
export const JobsPage = lazy(() => import('./JobsPage').then((m) => ({ default: m.JobsPage })))
export const PreviewPage = lazy(() =>
  import('./PreviewPage').then((m) => ({ default: m.PreviewPage })),
)
export const TrackingPage = lazy(() =>
  import('./TrackingPage').then((m) => ({ default: m.TrackingPage })),
)
export const ReportPage = lazy(() =>
  import('./ReportPage').then((m) => ({ default: m.ReportPage })),
)
