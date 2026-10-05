import type { ComponentType } from 'react'

import { CheckIcon } from '../../components/icons'
import { Section } from '../../components/ui'
import { reveal, useActiveStep } from '../../lib/motion'
import { MockCriteria, MockLogin, MockPreview, MockProgress, MockWindow } from './mocks'

interface Chapter {
  title: string
  text: string
  points: string[]
  screen: { title: string; Mock: ComponentType }
}

const chapters: Chapter[] = [
  {
    title: 'Connecte-toi, simplement',
    text: 'IUC ouvre une fenêtre Chromium dédiée. Tu t’y connectes toi-même, double authentification comprise.',
    points: ['Aucun mot de passe lu ni stocké', 'Session reprise automatiquement ensuite'],
    screen: { title: 'IUC · Connexion', Mock: MockLogin },
  },
  {
    title: 'Choisis tes critères',
    text: 'Période du like, type de contenu, comptes à cibler ou à protéger : la liste de tes comptes est à portée de clic.',
    points: ['Filtres combinables', 'Comptes classés par nombre de likes'],
    screen: { title: 'IUC · Critères', Mock: MockCriteria },
  },
  {
    title: 'Vérifie l’aperçu',
    text: 'Chaque like ciblé est listé. Tu décoches ceux que tu veux garder : rien n’est retiré sans ton accord.',
    points: ['Tout cocher ou tout décocher', 'Premier essai sur quelques likes possible'],
    screen: { title: 'IUC · Aperçu', Mock: () => <MockPreview rows={4} /> },
  },
  {
    title: 'Laisse IUC nettoyer',
    text: 'Les likes sont retirés par lots, avec des pauses et une limite par jour. Tu suis tout en direct, puis un rapport conclut.',
    points: ['Pause et reprise à tout moment', 'Arrêt automatique au moindre signal'],
    screen: { title: 'IUC · Suivi', Mock: MockProgress },
  },
]

/** « Comment ça marche » raconté au défilement : sur grand écran, l'écran du produit reste
 * visible et change avec l'étape lue ; sur mobile, chaque étape montre son propre écran.
 * Le défilement reste entièrement naturel. */
export function HowItWorks() {
  const { active, register } = useActiveStep()
  return (
    <Section
      id="fonctionnement"
      band
      eyebrow="Comment ça marche"
      title="Quatre étapes, et tu gardes la main sur chacune"
      intro="De la connexion au rapport final, IUC t’accompagne sans jamais décider à ta place."
    >
      <div className="grid gap-16 lg:grid-cols-2">
        <ol className="space-y-16 lg:space-y-0">
          {chapters.map((chapter, index) => {
            const current = index === active
            return (
              <li key={chapter.title} ref={register(index)} className="story-step">
                <div {...reveal(0)}>
                  <div className="flex items-center gap-4">
                    <span
                      aria-hidden="true"
                      className={`story-step-marker flex h-10 w-10 shrink-0 items-center justify-center rounded-full border text-small font-semibold ${
                        current
                          ? 'border-primary bg-primary text-on-primary'
                          : 'border-border-strong text-fg-muted'
                      }`}
                    >
                      {index + 1}
                    </span>
                    <h3 className="text-h3 text-fg">
                      <span className="sr-only">Étape {index + 1} : </span>
                      {chapter.title}
                    </h3>
                  </div>
                  <p className="mt-4 max-w-text text-body text-fg-muted">{chapter.text}</p>
                  <ul className="mt-4 space-y-2">
                    {chapter.points.map((point) => (
                      <li key={point} className="flex items-center gap-2 text-small text-fg">
                        <CheckIcon className="h-4 w-4 text-success-strong" />
                        {point}
                      </li>
                    ))}
                  </ul>
                  <div aria-hidden="true" className="mt-8 lg:hidden">
                    <MockWindow title={chapter.screen.title}>
                      <chapter.screen.Mock />
                    </MockWindow>
                  </div>
                </div>
              </li>
            )
          })}
        </ol>

        <div aria-hidden="true" className="hidden lg:block">
          <div className="sticky top-32">
            <div className="relative aspect-4/3">
              {chapters.map((chapter, index) => (
                <div
                  key={chapter.title}
                  className="story-screen"
                  data-active={index === active || undefined}
                >
                  <MockWindow title={chapter.screen.title} className="h-full">
                    <chapter.screen.Mock />
                  </MockWindow>
                </div>
              ))}
            </div>
            <div className="mt-6 flex justify-center gap-2">
              {chapters.map((chapter, index) => (
                <span
                  key={chapter.title}
                  className={`h-1 w-6 rounded-full transition-colors duration-page ${
                    index === active ? 'bg-primary' : 'bg-fill-strong'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </Section>
  )
}
