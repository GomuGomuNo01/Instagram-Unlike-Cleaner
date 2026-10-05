import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'

// Police Inter servie avec l'application (aucune requête vers un service externe).
import '@fontsource-variable/inter'
import './index.css'
import { getToken } from './api/token'
import { applyTheme, storedTheme } from './lib/preferences'
import { TokenPage } from './pages/TokenPage'
import { routes } from './router'

applyTheme(storedTheme())

const root = document.getElementById('root')
if (!root) throw new Error('Élément #root introuvable dans index.html')

createRoot(root).render(
  <StrictMode>
    {getToken() ? <RouterProvider router={createBrowserRouter(routes)} /> : <TokenPage />}
  </StrictMode>,
)
