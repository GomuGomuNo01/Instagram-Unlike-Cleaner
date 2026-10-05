import { act, render, renderHook, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { initMotion, reveal, usePresence } from './motion'

afterEach(() => {
  vi.useRealTimers()
  document.documentElement.classList.remove('motion-ready')
})

it('affiche directement le contenu sans IntersectionObserver', () => {
  initMotion()
  render(<h2 {...reveal(1)}>Titre</h2>)

  const title = screen.getByRole('heading', { name: 'Titre' })
  // Rien n'est masqué : pas de classe d'activation, élément marqué comme apparu.
  expect(document.documentElement).not.toHaveClass('motion-ready')
  expect(title).toHaveAttribute('data-revealed')
  expect(title).toHaveStyle({ '--reveal-order': '1' })
})

it('garde un élément le temps de son animation de sortie', () => {
  vi.useFakeTimers()
  const { result, rerender } = renderHook(({ open }) => usePresence(open), {
    initialProps: { open: false },
  })
  expect(result.current.mounted).toBe(false)

  rerender({ open: true })
  expect(result.current).toEqual({ mounted: true, state: 'open' })

  rerender({ open: false })
  expect(result.current).toEqual({ mounted: true, state: 'closed' })

  act(() => vi.runAllTimers())
  expect(result.current.mounted).toBe(false)
})
