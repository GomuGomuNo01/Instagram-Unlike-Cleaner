import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

// Police Inter servie avec l'application (aucune requête vers un service externe).
import '@fontsource-variable/inter/wght.css'
import './index.css'
import { getToken } from './api/token'
import { initMotion } from './lib/motion'
import { applyTheme, storedTheme } from './lib/preferences'
import { TokenPage } from './pages/TokenPage'
import { routes } from './router'

// Démo en ligne (npm run build:demo) : la fausse API est branchée avant le premier appel.
// Ailleurs, VITE_DEMO est absent et ce code disparaît de la compilation.
if (import.meta.env.VITE_DEMO === 'true') {
  const { installDemo } = await import('./demo/install')
  installDemo()
}

// Publiée dans un sous-dossier (GitHub Pages), l'interface garde ce préfixe dans ses adresses.
const basename = import.meta.env.BASE_URL.replace(/\/+$/, '') || '/'

applyTheme(storedTheme())
initMotion()

const root = document.getElementById('root')
if (!root) throw new Error('Élément #root introuvable dans index.html')

createRoot(root).render(
  <StrictMode>
    {getToken() ? (
      <RouterProvider router={createBrowserRouter(routes, { basename })} />
    ) : (
      <TokenPage />
    )}
  </StrictMode>,
)
