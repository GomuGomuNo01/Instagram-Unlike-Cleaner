import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { expect, it } from 'vitest'

import { DemoSimulator } from './Demo'

function renderDemo() {
  render(
    <MemoryRouter>
      <DemoSimulator />
    </MemoryRouter>,
  )
}

function authors() {
  const list = screen.getByRole('list', { name: 'Likes ciblés par la simulation' })
  return within(list)
    .getAllByRole('checkbox')
    .map((box) => box.getAttribute('aria-label'))
}

it('applique le filtre d’Instagram, laisse décocher, puis simule le nettoyage', async () => {
  renderDemo()
  // Par défaut : likes jusqu'à 2021, du plus récent au plus ancien.
  expect(screen.getByText('6 likes seront retirés sur 10 likes.')).toBeInTheDocument()
  expect(authors()[0]).toBe('Retirer le like de @page_memes (Vidéo, 2021)')
  // Comme sur Instagram : aucun filtre par compte ni par type.
  expect(screen.queryByRole('radio', { name: 'Reels' })).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('radio', { name: 'Du plus ancien au plus récent' }))
  expect(authors()[0]).toBe('Retirer le like de @compte_humour (Vidéo, 2019)')

  await userEvent.selectOptions(screen.getByLabelText('Date de début'), '2020')
  expect(screen.getByText('4 likes seront retirés sur 10 likes.')).toBeInTheDocument()

  await userEvent.click(
    screen.getByRole('checkbox', { name: 'Retirer le like de @ami_proche (Carrousel, 2020)' }),
  )
  expect(screen.getByText('3 likes seront retirés sur 10 likes.')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Lancer la simulation' }))
  expect(
    await screen.findByText(
      'Simulation terminée : 3 likes retirés, 7 likes gardés.',
      {},
      { timeout: 3000 },
    ),
  ).toBeInTheDocument()

  const list = screen.getByRole('list', { name: 'Likes ciblés par la simulation' })
  expect(within(list).getAllByText('retiré')).toHaveLength(3)
  expect(within(list).getByText('gardé')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Nettoyer mes vrais likes' })).toHaveAttribute(
    'href',
    '/commencer',
  )

  await userEvent.click(screen.getByRole('button', { name: 'Recommencer' }))
  expect(screen.getByText('4 likes seront retirés sur 10 likes.')).toBeInTheDocument()
})
