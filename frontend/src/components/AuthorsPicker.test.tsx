import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { expect, it } from 'vitest'

import { AuthorsPicker } from './AuthorsPicker'

const suggestions = [
  { author: 'club_basket', likes: 46 },
  { author: 'compte.fictif', likes: 20 },
  { author: 'club_sport', likes: 3 },
]

function Harness({ unavailable = [] as string[] }) {
  const [authors, setAuthors] = useState<string[]>([])
  return (
    <AuthorsPicker
      label="Comptes protégés"
      help="aide"
      value={authors}
      onChange={setAuthors}
      suggestions={suggestions}
      unavailable={unavailable}
      unavailableLabel="déjà ciblé"
    />
  )
}

it('affiche la liste des comptes connus avec leur nombre de likes', async () => {
  render(<Harness />)

  await userEvent.click(screen.getByRole('combobox', { name: 'Comptes protégés' }))

  const options = within(screen.getByRole('listbox')).getAllByRole('option')
  expect(options.map((option) => option.textContent)).toEqual([
    '@club_basket46 likes',
    '@compte.fictif20 likes',
    '@club_sport3 likes',
  ])
})

it('filtre par recherche et ajoute un compte au clic', async () => {
  render(<Harness />)

  await userEvent.type(screen.getByRole('combobox'), 'fic')
  await userEvent.click(screen.getByRole('option', { name: /compte\.fictif/ }))

  expect(screen.getByRole('button', { name: 'Retirer @compte.fictif' })).toBeInTheDocument()
})

it('se pilote au clavier et accepte un compte absent de la liste', async () => {
  render(<Harness />)
  const input = screen.getByRole('combobox')

  await userEvent.type(input, '@Autre_Compte{Enter}')
  expect(screen.getByRole('button', { name: 'Retirer @autre_compte' })).toBeInTheDocument()

  await userEvent.type(input, '{ArrowDown}{Enter}')
  expect(screen.getByRole('button', { name: 'Retirer @compte.fictif' })).toBeInTheDocument()

  await userEvent.type(input, 'deux mots{Enter}')
  expect(screen.getByText(/n’est pas un nom de compte valide/)).toBeInTheDocument()
})

it('empêche de choisir un compte déjà présent dans l’autre liste', async () => {
  render(<Harness unavailable={['club_basket']} />)

  await userEvent.click(screen.getByRole('combobox'))
  await userEvent.click(screen.getByRole('option', { name: /@club_basket/ }))

  expect(screen.getByRole('option', { name: /@club_basket/ })).toHaveAttribute(
    'aria-disabled',
    'true',
  )
  expect(screen.queryByRole('button', { name: 'Retirer @club_basket' })).not.toBeInTheDocument()
})
