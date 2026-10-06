import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { expect, it, vi } from 'vitest'

import { routes } from '../router'

async function openPresentation() {
  render(
    <RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/presentation'] })} />,
  )
  await screen.findByRole('heading', { name: 'IUC en 20 secondes' })
}

it('présente IUC en vidéo, avec un équivalent textuel de chaque scène', async () => {
  await openPresentation()

  const video = document.querySelector('video')
  expect(video).toHaveAttribute('src', '/presentation.mp4')
  expect(video).toHaveAttribute('poster', '/presentation-poster.jpg')
  expect(video).toHaveAttribute('controls')
  const chapters = within(
    screen.getByRole('list', { name: 'Ce que montre la vidéo' }),
  ).getAllByRole('button')
  expect(chapters.map((chapter) => chapter.querySelector('.tabular-nums')?.textContent)).toEqual([
    '0:00',
    '0:03',
    '0:06',
    '0:09',
    '0:12',
    '0:15',
    '0:18',
  ])
})

it('un chapitre place la vidéo sur sa scène et la lance', async () => {
  const play = vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  await openPresentation()

  await userEvent.click(screen.getByRole('button', { name: /3\. Aperçu/ }))

  expect(document.querySelector('video')?.currentTime).toBe(12.6)
  expect(play).toHaveBeenCalled()
})

it('l’onglet « Présentation » figure en tête de la navigation', async () => {
  await openPresentation()

  const nav = screen.getByRole('navigation', { name: 'Navigation principale' })
  const first = within(nav).getAllByRole('link')[0]
  expect(first).toHaveTextContent('Présentation')
  expect(first).toHaveAttribute('aria-current', 'page')
})
