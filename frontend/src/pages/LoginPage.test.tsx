import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'

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

beforeEach(() => giveConsent())

function openLogin() {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/connexion'] })} />)
  return screen.findByRole('heading', { name: 'Connecte-toi à Instagram' })
}

it('rappelle que le mot de passe ne passe jamais par IUC', async () => {
  await openLogin()

  expect(
    screen.getByText(/La session reste dans le dossier d’IUC, sur ton ordinateur/),
  ).toBeInTheDocument()
})
