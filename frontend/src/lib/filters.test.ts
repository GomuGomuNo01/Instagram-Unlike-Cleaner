import { describe, expect, it } from 'vitest'

import {
  buildJobRequest,
  describeFilters,
  emptyFilters,
  localToday,
  validateFilters,
} from './filters'

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
      start_date: null,
      end_date: null,
      max_scanned: null,
    })
  })

  it('n’envoie que le filtre d’Instagram et la limite d’essai', () => {
    const request = buildJobRequest({
      sort: 'oldest_first',
      startDate: '2026-06-01',
      endDate: '2026-09-30',
      maxScanned: '25',
    })
    expect(request).toEqual({
      sort: 'oldest_first',
      start_date: '2026-06-01',
      end_date: '2026-09-30',
      max_scanned: 25,
    })
  })
})

describe('describeFilters', () => {
  it('résume le tri et la période', () => {
    expect(
      describeFilters({ sort: 'oldest_first', start_date: '2019-01-01', end_date: '2021-12-31' }),
    ).toBe('likes du 01/01/2019 au 31/12/2021, du plus ancien au plus récent')
  })

  it('complète une période ouverte', () => {
    expect(
      describeFilters({ sort: 'newest_first', start_date: null, end_date: '2021-12-31' }),
    ).toBe('likes du début au 31/12/2021, du plus récent au plus ancien')
    expect(describeFilters({ sort: 'newest_first' })).toBe(
      'tout l’historique, du plus récent au plus ancien',
    )
  })
})

it('localToday utilise la date locale', () => {
  expect(localToday(new Date(2026, 0, 9, 23, 30))).toBe('2026-01-09')
})
