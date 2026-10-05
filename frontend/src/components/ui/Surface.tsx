import type { ReactNode } from 'react'

import { reveal } from '../../lib/motion'

// Mise en page : conteneurs, cartes, en-têtes de page et sections de la page d'accueil.

export function Container({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`mx-auto w-full max-w-page px-4 sm:px-6 lg:px-8 ${className}`}>{children}</div>
  )
}

const paddings = { none: '', md: 'p-6', lg: 'p-6 sm:p-8' } as const

export function Card({
  children,
  className = '',
  padding = 'md',
  interactive = false,
  as: Tag = 'section',
}: {
  children: ReactNode
  className?: string
  padding?: keyof typeof paddings
  /** Carte cliquable : légère élévation au survol. */
  interactive?: boolean
  as?: 'section' | 'div' | 'article' | 'li'
}) {
  return (
    <Tag
      className={`card ${interactive ? 'card-interactive' : ''} ${paddings[padding]} ${className}`}
    >
      {children}
    </Tag>
  )
}

/** En-tête d'un écran : repère, titre, description, puis l'action principale. */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="mb-8 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-text">
        {eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}
        <h1 className="text-h1">{title}</h1>
        {description && <p className="mt-3 text-lead text-fg-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </header>
  )
}

/** Section de la page d'accueil : repère, titre, introduction, puis son contenu. Les textes
 * apparaissent en séquence à l'entrée de la section dans l'écran. */
export function Section({
  id,
  eyebrow,
  title,
  intro,
  band = false,
  centered = false,
  children,
}: {
  id: string
  eyebrow?: string
  title: string
  intro?: string
  /** Fond légèrement teinté, fondu vers les sections voisines. */
  band?: boolean
  centered?: boolean
  children: ReactNode
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-titre`}
      className={`py-16 sm:py-24 lg:py-32 ${band ? 'surface-band' : ''}`}
    >
      <Container>
        <div className={centered ? 'mx-auto max-w-prose text-center' : 'max-w-prose'}>
          {eyebrow && (
            <p className="eyebrow" {...reveal(0)}>
              {eyebrow}
            </p>
          )}
          <h2 id={`${id}-titre`} className="mt-3 text-h2" {...reveal(1)}>
            {title}
          </h2>
          {intro && (
            <p className="mt-4 text-lead text-fg-muted" {...reveal(2)}>
              {intro}
            </p>
          )}
        </div>
        <div className="mt-12 sm:mt-16">{children}</div>
      </Container>
    </section>
  )
}
