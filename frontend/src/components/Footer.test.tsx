import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it } from 'vitest'

import { Footer } from './Footer'

it('le pied de page mène au profil GitHub de l’auteur pour le contact', () => {
  render(
    <MemoryRouter>
      <Footer />
    </MemoryRouter>,
  )

  expect(screen.getByRole('link', { name: 'Contact GitHub' })).toHaveAttribute(
    'href',
    'https://github.com/GomuGomuNo01',
  )
})
