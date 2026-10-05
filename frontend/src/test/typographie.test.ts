import { expect, it } from 'vitest'

// Règle éditoriale : aucun tiret cadratin dans l'interface. Le caractère est construit à
// partir de son code, pour que ce fichier respecte lui aussi la règle.
const EM_DASH = String.fromCharCode(0x2014)

const sources = import.meta.glob<string>('../**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
})

it('n’utilise aucun tiret cadratin', () => {
  const offenders = Object.entries(sources)
    .filter(([, text]) => text.includes(EM_DASH))
    .map(([path]) => path)

  expect(Object.keys(sources).length).toBeGreaterThan(30) // le contrôle porte bien sur le code
  expect(offenders).toEqual([])
})
