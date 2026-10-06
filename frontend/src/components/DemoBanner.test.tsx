import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'

import { DemoBanner } from './DemoBanner'

it('« Installer la vraie version » télécharge directement l’installeur Windows', () => {
  render(<DemoBanner />)

  expect(screen.getByRole('link', { name: 'Installer la vraie version' })).toHaveAttribute(
    'href',
    'https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner/releases/latest/download/IUC-Setup.exe',
  )
})
