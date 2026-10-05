import { describe, expect, it } from 'vitest'

import { formatDay, formatDuration, plural } from './format'
import { estimateRemainingSeconds, percent, removalRate } from './progress'

describe('removalRate', () => {
  it('est nulle tant qu’aucun lot n’est terminé', () => {
    expect(removalRate([], 0)).toBeNull()
  })

  it('donne des likes par minute depuis le début de l’exécution', () => {
    // 25 likes retirés en 1 min 15 s, comme le nettoyage n° 6 du 05/10/2026.
    const points = [
      { total: 20, at: 33_000 },
      { total: 25, at: 75_000 },
    ]
    expect(removalRate(points, 0)).toBeCloseTo(20)
  })
})

describe('estimateRemainingSeconds', () => {
  it('se base sur le rythme observé', () => {
    expect(estimateRemainingSeconds(40, 20)).toBe(120)
  })

  it('ne devine rien sans rythme', () => {
    expect(estimateRemainingSeconds(40, null)).toBeNull()
  })

  it('vaut zéro quand il ne reste rien', () => {
    expect(estimateRemainingSeconds(0, 20)).toBe(0)
  })
})

it('percent reste entre 0 et 100', () => {
  expect(percent(0, 0)).toBe(0)
  expect(percent(1, 3)).toBe(33)
  expect(percent(5, 4)).toBe(100)
})

it('formate durées, dates et pluriels', () => {
  expect(formatDuration(42)).toBe('42 s')
  expect(formatDuration(77)).toBe('1 min 17 s')
  expect(formatDuration(7380)).toBe('2 h 03 min')
  expect(formatDay('2026-10-03')).toBe('03/10/2026')
  expect(formatDay(null)).toBe('date inconnue')
  expect(plural(1, 'like')).toBe('1 like')
  expect(plural(3, 'like')).toBe('3 likes')
})
