import { describe, expect, it } from 'vitest'

import {
  buildJobRequest,
  emptyFilters,
  localToday,
  normalizeAuthor,
  validateFilters,
} from './filters'

describe('normalizeAuthor', () => {
  it.each([
    ['@Compte_A', 'compte_a'],
    ['  auteur.b ', 'auteur.b'],
    ['deux mots', null],
    ['accent_é', null],
    ['@', null],
    ['a'.repeat(31), null],
  ])('%s → %s', (raw, expected) => {
    expect(normalizeAuthor(raw)).toBe(expected)
  })
})

describe('validateFilters', () => {
  const today = '2026-10-05'

  it('accepte des critères vides', () => {
    expect(validateFilters(emptyFilters, today)).toEqual({})
  })

  it('rattache chaque erreur de date à son champ', () => {
    const future = validateFilters(
      { ...emptyFilters, startDate: '2026-10-07', endDate: '2026-10-08' },
      today,
    )
    expect(future).toEqual({
      startDate: 'Cette date est dans le futur.',
      endDate: 'Cette date est dans le futur.',
    })
    const inverted = validateFilters(
      { ...emptyFilters, startDate: '2026-06-01', endDate: '2026-01-01' },
      today,
    )
    expect(inverted).toEqual({ endDate: 'La date de fin doit suivre la date de début.' })
  })

  it('signale un compte à la fois ciblé et protégé sous la liste des comptes protégés', () => {
    const errors = validateFilters(
      { ...emptyFilters, includeAuthors: ['a', 'b'], excludeAuthors: ['b'] },
      today,
    )
    expect(errors).toEqual({ excludeAuthors: 'Déjà dans les comptes ciblés : @b.' })
  })

  it.each(['0', '-3', '2.5', 'abc'])('refuse un nombre maximal invalide (%s)', (value) => {
    expect(validateFilters({ ...emptyFilters, maxScanned: value }, today)).toHaveProperty(
      'maxScanned',
    )
  })
})

describe('buildJobRequest', () => {
  it('transforme les champs vides en null', () => {
    expect(buildJobRequest(emptyFilters)).toEqual({
      sort: 'newest_first',
      content: 'all',
      start_date: null,
      end_date: null,
      include_authors: [],
      exclude_authors: [],
      max_scanned: null,
    })
  })

  it('reprend les critères saisis', () => {
    const request = buildJobRequest({
      ...emptyFilters,
      startDate: '2026-06-01',
      sort: 'oldest_first',
      content: 'reels',
      excludeAuthors: ['compte_a'],
      maxScanned: '25',
    })
    expect(request).toMatchObject({
      start_date: '2026-06-01',
      sort: 'oldest_first',
      content: 'reels',
      exclude_authors: ['compte_a'],
      max_scanned: 25,
    })
  })
})

it('localToday utilise la date locale', () => {
  expect(localToday(new Date(2026, 0, 9, 23, 30))).toBe('2026-01-09')
})
