import type { CSSProperties } from 'react'

import { ArrowRightIcon, CheckIcon, PlayIcon, ShieldIcon } from '../../components/icons'
import { ButtonLink, Container } from '../../components/ui'
import { pointerField, reveal } from '../../lib/motion'
import { MockPreview, MockWindow } from './mocks'

const depth = (value: number) => ({ '--depth': value }) as CSSProperties

const promises = [
  'Aperçu obligatoire avant tout retrait',
  'Rythme prudent, pause au moindre signal',
  'Rapport détaillé à la fin',
]

/** Héros : proposition de valeur, action principale, et le produit en profondeur. Le texte
 * apparaît en séquence (titre, description, actions, illustration) ; avec une souris, les
 * calques de l'illustration suivent légèrement le curseur. */
export function Hero() {
  return (
    <section
      ref={pointerField}
      aria-labelledby="hero-titre"
      className="relative isolate -mt-16 overflow-hidden pt-16"
    >
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
        <div className="dot-grid absolute inset-0" />
        {/* Halos d'arrière-plan : ils glissent moins vite que le contenu au défilement. */}
        <div className="absolute -top-48 left-1/2 -translate-x-1/2 lg:left-2/3">
          <div
            data-scroll-depth
            style={{ '--scroll-depth': 1.2 } as CSSProperties}
            className="glow h-160 w-160"
          />
        </div>
        <div className="absolute top-1/3 -left-32">
          <div
            data-scroll-depth
            style={{ '--scroll-depth': 0.6 } as CSSProperties}
            className="glow glow-alt h-128 w-128"
          />
        </div>
        <div className="cursor-glow" />
      </div>

      <Container className="grid items-center gap-16 pt-12 pb-24 sm:pt-24 lg:grid-cols-12 lg:gap-12 lg:pt-32 lg:pb-32">
        <div className="lg:col-span-7">
          <p {...reveal(0)}>
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1 text-small font-medium text-fg-muted elevation-xs backdrop-blur">
              <span aria-hidden="true" className="h-2 w-2 rounded-full bg-success-strong" />
              Open source, 100 % local, sans mot de passe
            </span>
          </p>
          <h1 id="hero-titre" className="mt-6 text-display text-fg" {...reveal(1)}>
            Fais le ménage dans tes <span className="text-primary-strong">« J’aime »</span>{' '}
            Instagram
          </h1>
          <p className="mt-6 max-w-text text-lead text-fg-muted" {...reveal(2)}>
            Des années de likes retirés en quelques clics. Tu choisis les critères, tu vérifies la
            liste, IUC s’occupe du reste, sans que rien ne quitte ton ordinateur.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row" {...reveal(3)}>
            <ButtonLink to="/commencer" size="lg" magnetic trailingIcon={<ArrowRightIcon />}>
              Commencer le nettoyage
            </ButtonLink>
            <ButtonLink
              to="/#demo"
              size="lg"
              variant="secondary"
              icon={<PlayIcon className="h-4 w-4" />}
            >
              Voir la démonstration
            </ButtonLink>
          </div>
          <ul className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-6" {...reveal(4)}>
            {promises.map((promise) => (
              <li key={promise} className="flex items-center gap-2 text-small text-fg-muted">
                <CheckIcon className="h-4 w-4 text-success-strong" />
                {promise}
              </li>
            ))}
          </ul>
        </div>

        <figure className="lg:col-span-5">
          <HeroVisual />
          <figcaption className="sr-only">
            Exemple d’aperçu : les likes ciblés sont listés, tu décoches ceux à garder, puis tu
            lances le nettoyage.
          </figcaption>
        </figure>
      </Container>
    </section>
  )
}

/** Illustration en trois calques : la fenêtre d'aperçu et deux cartes flottantes, plus
 * proches, qui bougent davantage avec le curseur. */
function HeroVisual() {
  return (
    <div aria-hidden="true" className="relative mx-auto w-full max-w-text lg:max-w-none">
      <div {...reveal(3, 'scale')}>
        <div data-depth style={depth(-8)}>
          <MockWindow title="IUC · Aperçu du nettoyage">
            <MockPreview />
          </MockWindow>
        </div>
      </div>

      <div className="absolute -top-6 right-2 sm:-right-6" {...reveal(5, 'scale')}>
        <div data-depth style={depth(18)}>
          <div className="glass flex items-center gap-3 rounded-lg p-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-success-soft text-success-strong">
              <CheckIcon className="h-4 w-4" />
            </span>
            <span>
              <span className="block text-small font-semibold text-fg">Lot retiré</span>
              <span className="block text-caption text-fg-muted">18 likes, pause de 2 min</span>
            </span>
          </div>
        </div>
      </div>

      <div className="absolute -bottom-8 left-2 sm:-left-8" {...reveal(6, 'scale')}>
        <div data-depth style={depth(12)}>
          <div className="glass flex items-center gap-3 rounded-lg p-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-soft text-primary-strong">
              <ShieldIcon className="h-4 w-4" />
            </span>
            <span>
              <span className="block text-small font-semibold text-fg">@ami_proche protégé</span>
              <span className="block text-caption text-fg-muted">
                ses likes sont toujours gardés
              </span>
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
