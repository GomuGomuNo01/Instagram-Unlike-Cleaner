import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'

// Le client d'API garde la fonction fetch du chargement : elle est remplacée avant tout import.
const sent = vi.hoisted(() => {
  const bodies: unknown[] = []
  globalThis.fetch = async (input: RequestInfo | URL) => {
    const request = input as Request
    if (request.method === 'POST') bodies.push(await request.json())
    const body = request.method === 'POST' ? { id: 1 } : []
    return new Response(JSON.stringify(body), {
      status: request.method === 'POST' ? 202 : 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }
  return bodies
})

import { giveConsent } from '../lib/preferences'
import { routes } from '../router'

beforeEach(() => {
  sent.length = 0
  giveConsent()
})

async function openCriteria() {
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/filtres'] })} />)
  return screen.findByRole('heading', { name: 'Trier et filtrer' })
}

it('reprend exactement le panneau d’Instagram : trier par, date de début, date de fin', async () => {
  await openCriteria()

  expect(screen.getByRole('group', { name: 'Trier par' })).toBeInTheDocument()
  expect(screen.getAllByRole('radio').map((radio) => radio.closest('label')?.textContent)).toEqual([
    'Du plus récent au plus ancien',
    'Du plus ancien au plus récent',
  ])
  expect(screen.getByLabelText('Date de début')).toBeInTheDocument()
  expect(screen.getByLabelText('Date de fin')).toBeInTheDocument()
  // Aucun autre critère : ni type de contenu, ni comptes.
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  expect(screen.queryByText(/Affiner/)).not.toBeInTheDocument()
})

it('n’envoie que le filtre d’Instagram', async () => {
  await openCriteria()
  await userEvent.click(screen.getByRole('radio', { name: 'Du plus ancien au plus récent' }))
  await userEvent.type(screen.getByLabelText('Date de fin'), '2021-12-31')

  await userEvent.click(screen.getByRole('button', { name: 'Préparer l’aperçu' }))

  await waitFor(() => expect(sent).toHaveLength(1))
  expect(sent[0]).toEqual({
    sort: 'oldest_first',
    start_date: null,
    end_date: '2021-12-31',
    max_scanned: null,
  })
})

it('n’envoie la limite d’essai que si l’essai est activé', async () => {
  await openCriteria()
  await userEvent.click(screen.getByRole('switch', { name: 'Faire d’abord un essai' }))
  await userEvent.type(screen.getByLabelText('Nombre maximal de likes à lire'), '25')

  await userEvent.click(screen.getByRole('button', { name: 'Préparer l’aperçu' }))

  await waitFor(() => expect(sent).toHaveLength(1))
  expect(sent[0]).toMatchObject({ max_scanned: 25 })
})
