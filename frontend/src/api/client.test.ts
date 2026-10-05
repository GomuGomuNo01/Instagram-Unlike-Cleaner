import { afterEach, describe, expect, it } from 'vitest'

import { describeError } from './client'
import { getToken, saveToken } from './token'

describe('jeton de l’API', () => {
  afterEach(() => {
    document.head.querySelectorAll('meta[name="iuc-token"]').forEach((meta) => meta.remove())
  })

  it('vient de la balise injectée par `iuc serve`', () => {
    document.head.insertAdjacentHTML('beforeend', '<meta name="iuc-token" content="jeton-serveur">')
    saveToken('jeton-saisi')

    expect(getToken()).toBe('jeton-serveur')
  })

  it('vient sinon de la saisie (mode développement)', () => {
    expect(getToken()).toBeNull()
    saveToken('  jeton-saisi ')

    expect(getToken()).toBe('jeton-saisi')
  })
})

describe('describeError', () => {
  it('explique un jeton refusé', () => {
    expect(describeError(401, { detail: 'x' })).toMatch(/recharge la page/)
  })

  it('reprend le message de l’API', () => {
    expect(describeError(409, { detail: 'Une tâche est déjà en cours.' })).toBe(
      'Une tâche est déjà en cours.',
    )
  })

  it('assemble les erreurs de validation', () => {
    const detail = [{ msg: 'Value error, la date 06/10/2026 est dans le futur' }, { msg: 'autre' }]
    expect(describeError(422, { detail })).toBe('la date 06/10/2026 est dans le futur ; autre')
  })
})
