import { expect, it } from 'vitest'

// Le système de design (styles/tokens.css) définit les seules valeurs autorisées. Ce test
// vérifie que les composants ne les contournent pas : pas de couleur de palette brute, pas
// de valeur arbitraire, pas de taille de texte ou d'ombre hors échelle, et des espacements
// pris dans l'échelle 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128 px.

const sources = Object.entries(
  import.meta.glob<string>(['../**/*.tsx', '!../**/*.test.tsx'], {
    query: '?raw',
    import: 'default',
    eager: true,
  }),
)

const PALETTE =
  'slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose'
const COLOR_UTILITIES =
  'bg|text|border|ring|outline|fill|stroke|from|via|to|divide|accent|decoration|placeholder|caret'

const rules: [string, RegExp][] = [
  [
    'couleur de palette brute',
    new RegExp(`\\b(?:${COLOR_UTILITIES})-(?:(?:${PALETTE})-\\d{2,3}|white|black)\\b`, 'g'),
  ],
  ['valeur arbitraire', /\b[a-z][\w-]*-\[[^\]]+\]/g],
  ['taille de texte hors échelle', /\btext-(?:xs|sm|base|lg|xl|[2-9]xl)\b/g],
  ['ombre hors échelle', /\bshadow(?:-(?:xs|sm|md|lg|xl|2xl))?\b(?!-)/g],
]

const SPACING = new Set(['0', '1', '2', '3', '4', '6', '8', '12', '16', '24', '32'])
const SPACING_UTILITY =
  /(?<![\w-])-?(?:p|px|py|pt|pb|pl|pr|ps|pe|m|mx|my|mt|mb|ml|mr|ms|me|gap|gap-x|gap-y|space-x|space-y)-(\d+(?:\.\d+)?)(?![\w./])/g

it('les composants n’utilisent que les tokens du système de design', () => {
  const offenders: string[] = []
  for (const [path, text] of sources) {
    for (const [label, pattern] of rules) {
      for (const match of text.matchAll(pattern))
        offenders.push(`${path} : ${label} « ${match[0]} »`)
    }
    for (const match of text.matchAll(SPACING_UTILITY)) {
      if (!SPACING.has(match[1] ?? '')) offenders.push(`${path} : espacement « ${match[0]} »`)
    }
  }

  expect(sources.length).toBeGreaterThan(30) // le contrôle porte bien sur les composants
  expect(offenders).toEqual([])
})
