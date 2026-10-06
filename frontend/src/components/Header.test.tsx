import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'

const DOWNLOAD =
  'https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner/releases/latest/download/IUC-Setup.exe'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

async function renderHeader() {
  const { Header } = await import('./Header')
  render(
    <MemoryRouter>
      <Header />
    </MemoryRouter>,
  )
}

it('dans la démo en ligne, la navigation propose de télécharger la vraie version', async () => {
  vi.stubEnv('VITE_DEMO', 'true')
  await renderHeader()

  const links = screen.getAllByRole('link', { name: 'Télécharger pour Windows', hidden: true })
  expect(links).toHaveLength(2) // barre de navigation et menu mobile
  for (const link of links) expect(link).toHaveAttribute('href', DOWNLOAD)
})

it('dans IUC installé, pas de lien de téléchargement', async () => {
  await renderHeader()

  expect(
    screen.queryByRole('link', { name: 'Télécharger pour Windows', hidden: true }),
  ).not.toBeInTheDocument()
})
