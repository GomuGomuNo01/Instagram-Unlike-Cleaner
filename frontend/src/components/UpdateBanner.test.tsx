import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import type { UpdateInfo } from '../api/types'
import { UpdateBanner } from './UpdateBanner'

const RELEASE = 'https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner/releases/latest'

function update(overrides: Partial<UpdateInfo> = {}): UpdateInfo {
  return {
    enabled: true,
    mode: 'installer',
    current: '1.4.0',
    latest: '1.5.0',
    available: true,
    release_url: RELEASE,
    download_url: null,
    error: null,
    ...overrides,
  }
}

/** Fausse API : GET /api/update renvoie `info`, POST /api/update/install renvoie `install`. */
function serve(info: UpdateInfo, install: Response = Response.json({ version: '1.5.0' })) {
  const requests: string[] = []
  vi.stubGlobal('fetch', async (request: Request) => {
    const { pathname } = new URL(request.url)
    requests.push(`${request.method} ${pathname}`)
    return pathname === '/api/update' ? Response.json(info) : install.clone()
  })
  return requests
}

afterEach(() => vi.unstubAllGlobals())

it('ne montre rien quand IUC est à jour', async () => {
  const requests = serve(update({ latest: '1.4.0', available: false }))

  const { container } = render(<UpdateBanner />)

  await vi.waitFor(() => expect(requests).toEqual(['GET /api/update']))
  expect(container).toBeEmptyDOMElement()
})

it('installe la nouvelle version en un clic, puis annonce la relance', async () => {
  const requests = serve(update())
  render(<UpdateBanner />)

  expect(await screen.findByText('IUC 1.5.0 est disponible')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Voir les nouveautés' })).toHaveAttribute('href', RELEASE)
  await userEvent.click(screen.getByRole('button', { name: 'Mettre à jour' }))

  expect(await screen.findByRole('status')).toHaveTextContent(/se rouvre tout seul/)
  expect(requests).toEqual(['GET /api/update', 'POST /api/update/install'])
})

it('affiche la raison d’un échec et permet de réessayer', async () => {
  serve(update(), Response.json({ detail: 'GitHub ne répond pas.' }, { status: 502 }))
  render(<UpdateBanner />)

  await userEvent.click(await screen.findByRole('button', { name: 'Mettre à jour' }))

  expect(await screen.findByRole('alert')).toHaveTextContent('GitHub ne répond pas.')
  expect(screen.getByRole('button', { name: 'Mettre à jour' })).toBeEnabled()
})

it('version portable : propose la nouvelle archive au lieu d’installer', async () => {
  const zip = `${RELEASE}/download/IUC-portable.zip`
  serve(update({ mode: 'portable', download_url: zip }))
  render(<UpdateBanner />)

  expect(
    await screen.findByRole('link', { name: 'Télécharger la version portable' }),
  ).toHaveAttribute('href', zip)
  expect(screen.queryByRole('button', { name: 'Mettre à jour' })).not.toBeInTheDocument()
})
