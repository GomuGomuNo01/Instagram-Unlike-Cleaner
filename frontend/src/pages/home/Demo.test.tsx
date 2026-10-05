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

it('applique les critères, laisse décocher, puis simule le nettoyage', async () => {
  renderDemo()
  // Par défaut, @ami_proche est protégé : ses deux likes ne sont pas ciblés.
  expect(screen.getByText('8 likes seront retirés sur 10 likes.')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('radio', { name: 'Reels' }))
  expect(screen.getByText('4 likes seront retirés sur 10 likes.')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: '@club_sport' }))
  expect(screen.getByRole('button', { name: /@club_sport/ })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  expect(screen.getByText('3 likes seront retirés sur 10 likes.')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('checkbox', { name: /@compte_humour \(Vidéo, 2019\)/ }))
  expect(screen.getByText('2 likes seront retirés sur 10 likes.')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Lancer la simulation' }))
  expect(
    await screen.findByText(
      'Simulation terminée : 2 likes retirés, 8 likes gardés.',
      {},
      { timeout: 3000 },
    ),
  ).toBeInTheDocument()

  const list = screen.getByRole('list', { name: 'Likes ciblés par la simulation' })
  expect(within(list).getAllByText('retiré')).toHaveLength(2)
  expect(within(list).getByText('gardé')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Nettoyer mes vrais likes' })).toHaveAttribute(
    'href',
    '/commencer',
  )

  await userEvent.click(screen.getByRole('button', { name: 'Recommencer' }))
  expect(screen.getByText('3 likes seront retirés sur 10 likes.')).toBeInTheDocument()
})
