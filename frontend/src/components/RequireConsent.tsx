import { Navigate, Outlet } from 'react-router'

import { hasConsent } from '../lib/preferences'

/** Les écrans de nettoyage ne s'ouvrent qu'après l'acceptation de l'avertissement. */
export function RequireConsent() {
  return hasConsent() ? <Outlet /> : <Navigate to="/commencer" replace />
}
