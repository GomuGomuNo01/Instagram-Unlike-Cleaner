import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'

import { giveConsent, hasConsent } from '../lib/preferences'
import { routes } from '../router'

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(<RouterProvider router={router} />)
  return router
}

describe('page d’accueil', () => {
  it('présente la proposition de valeur et une action principale claire', () => {
    renderAt('/')

    // toHaveTextContent ramène les espaces insécables du titre à des espaces simples.
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Fais le ménage dans tes « J’aime » Instagram',
    )
    const start = screen.getAllByRole('link', { name: /Commencer le nettoyage/ })[0]
    expect(start).toHaveAttribute('href', '/commencer')
    expect(screen.getByRole('heading', { name: 'Questions fréquentes' })).toBeInTheDocument()
  })
})

describe('en-tête', () => {
  it('ouvre le menu mobile et le referme avec Échap', async () => {
    renderAt('/')
    const toggle = screen.getByRole('button', { name: 'Ouvrir le menu' })

    await userEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('navigation', { name: 'Menu' })).not.toHaveAttribute('inert')

    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('button', { name: 'Ouvrir le menu' })).toHaveFocus()
    expect(screen.getByRole('navigation', { name: 'Menu', hidden: true })).toHaveAttribute('inert')
  })
})

describe('avertissement et consentement', () => {
  it('bloque le parcours tant que les risques ne sont pas acceptés', async () => {
    const router = renderAt('/commencer')
    const accept = await screen.findByRole('button', { name: 'J’accepte et je me connecte' })
    expect(accept).toBeDisabled()

    await userEvent.click(screen.getByRole('checkbox'))
    await userEvent.click(accept)

    expect(hasConsent()).toBe(true)
    // L'écran suivant est chargé à la demande : la navigation aboutit une fois prêt.
    await waitFor(() => expect(router.state.location.pathname).toBe('/connexion'))
  })

  it('renvoie vers l’avertissement un écran ouvert sans consentement', async () => {
    const router = renderAt('/nettoyages/3/suivi')

    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
      'Quelques points importants',
    )
    expect(router.state.location.pathname).toBe('/commencer')
  })

  it('passe directement à la connexion une fois le consentement donné', async () => {
    giveConsent()
    const router = renderAt('/commencer')

    await screen.findByRole('heading', { name: 'Connecte-toi à Instagram' })
    expect(router.state.location.pathname).toBe('/connexion')
  })
})
