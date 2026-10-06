import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

// Le client d'API lit fetch à chaque appel : une session fermée suffit à afficher l'écran.
vi.hoisted(() => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        browser_open: false,
        logged_in: false,
        account_id: null,
        page: null,
        challenge_required: false,
        consent_required: false,
        busy: false,
      }),
      { headers: { 'Content-Type': 'application/json' } },
    )
})

import { giveConsent } from '../lib/preferences'
import { routes } from '../router'

const DESKTOP = 'https://fictif-iuc-6080.app.github.dev/vnc.html?autoconnect=true&resize=scale'

beforeEach(() => giveConsent())
afterEach(() => document.querySelector('meta[name="iuc-desktop"]')?.remove())

function openLogin() {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/connexion'] })} />)
  return screen.findByRole('heading', { name: 'Connecte-toi à Instagram' })
}

it('hors Codespaces, ne parle pas de bureau distant', async () => {
  await openLogin()

  expect(screen.queryByRole('link', { name: 'Ouvrir le bureau distant' })).not.toBeInTheDocument()
  expect(
    screen.getByText(/La session reste dans le dossier d’IUC, sur ton ordinateur/),
  ).toBeInTheDocument()
})

it('dans Codespaces, mène au bureau distant où s’affiche la fenêtre Chromium', async () => {
  document.head.insertAdjacentHTML('beforeend', `<meta name="iuc-desktop" content="${DESKTOP}">`)

  await openLogin()

  const link = screen.getByRole('link', { name: 'Ouvrir le bureau distant' })
  expect(link).toHaveAttribute('href', DESKTOP)
  expect(link).toHaveAttribute('target', '_blank')
  expect(screen.getByText(/dans ton Codespace, que toi seul contrôles/)).toBeInTheDocument()
})
