import type { ComponentType, ReactNode, SVGProps } from 'react'

import {
  ActivityIcon,
  AlertIcon,
  ArrowRightIcon,
  BriefcaseIcon,
  ClockIcon,
  FileTextIcon,
  GaugeIcon,
  KeyboardIcon,
  ListCheckIcon,
  LockIcon,
  PauseIcon,
  RotateIcon,
  ShieldIcon,
  SlidersIcon,
} from '../../components/icons'
import { ButtonLink, Container, Disclosure, LiveDot, Section } from '../../components/ui'
import { reveal, spotlight } from '../../lib/motion'
import { MockFilterSummary, MockReport } from './mocks'

type Icon = ComponentType<SVGProps<SVGSVGElement>>

function IconTile({ icon: Icon }: { icon: Icon }) {
  return (
    <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-soft text-primary-strong transition-transform duration-component ease-emphasized motion-safe:group-hover:-rotate-3 motion-safe:group-hover:scale-105">
      <Icon className="h-6 w-6" />
    </span>
  )
}

// --- Engagements (preuves vérifiables, à la place de témoignages) -----------------------------

const commitments = [
  { value: '0', label: 'mot de passe lu ou stocké par IUC' },
  { value: '100 %', label: 'de tes données restent sur ton ordinateur' },
  { value: '150', label: 'likes par jour au maximum, par défaut' },
  { value: '250+', label: 'tests automatisés à chaque version' },
]

export function Commitments() {
  return (
    <section aria-label="Engagements" className="border-y border-border bg-canvas-subtle">
      <Container>
        <dl className="grid grid-cols-2 lg:grid-cols-4">
          {commitments.map((item, index) => (
            <div
              key={item.label}
              className="flex flex-col gap-1 px-2 py-8 text-center sm:px-6"
              {...reveal(index, 'fade')}
            >
              <dt className="text-small text-fg-muted">{item.label}</dt>
              <dd className="order-first text-h2 text-fg tabular-nums">{item.value}</dd>
            </div>
          ))}
        </dl>
      </Container>
    </section>
  )
}

// --- Avantages ----------------------------------------------------------------------------

const benefits = [
  {
    icon: ClockIcon,
    title: 'Des heures gagnées',
    text: 'Des centaines ou des milliers de likes retirés sans clic répétitif, même sur plusieurs jours.',
  },
  {
    icon: ListCheckIcon,
    title: 'Tu gardes la main',
    text: 'Tu choisis les critères et tu valides la liste. Rien n’est retiré sans ton accord.',
  },
  {
    icon: LockIcon,
    title: 'Confidentialité totale',
    text: 'Aucun mot de passe demandé, aucune donnée envoyée ailleurs que sur ton ordinateur.',
  },
  {
    icon: BriefcaseIcon,
    title: 'Un profil prêt pour la suite',
    text: 'Moins de traces gênantes avant une recherche de stage, d’alternance ou d’emploi.',
  },
]

export function Benefits() {
  return (
    <Section
      id="avantages"
      eyebrow="Pourquoi IUC"
      title="Le ménage que tu repousses, fait proprement"
      intro="Instagram permet de retirer ses likes, mais un par un ou par petits lots. IUC fait ce travail à ta place, avec les précautions nécessaires."
    >
      <ul ref={spotlight} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {benefits.map((benefit, index) => (
          <li key={benefit.title} {...reveal(index)}>
            <article className="card spotlight group h-full p-6">
              <IconTile icon={benefit.icon} />
              <h3 className="mt-6 text-h3 text-fg">{benefit.title}</h3>
              <p className="mt-2 text-small text-fg-muted">{benefit.text}</p>
            </article>
          </li>
        ))}
      </ul>
    </Section>
  )
}

// --- Fonctionnalités (grille modulaire) -------------------------------------------------------

function Feature({
  icon,
  title,
  text,
  className = '',
  order,
  children,
}: {
  icon: Icon
  title: string
  text: string
  className?: string
  order: number
  children?: ReactNode
}) {
  return (
    <li className={className} {...reveal(order)}>
      <article className="card spotlight group flex h-full flex-col p-6 sm:p-8">
        <IconTile icon={icon} />
        <h3 className="mt-6 text-h3 text-fg">{title}</h3>
        <p className="mt-2 max-w-text text-small text-fg-muted">{text}</p>
        {children && (
          <div aria-hidden="true" className="mt-6 flex-1">
            {children}
          </div>
        )}
      </article>
    </li>
  )
}

export function Features() {
  return (
    <Section
      id="fonctionnalites"
      eyebrow="Fonctionnalités"
      title="Tout ce qu’il faut, rien de plus"
      intro="Une interface simple, pensée pour aller droit au but et rester claire à chaque étape."
    >
      <ul ref={spotlight} className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Feature
          icon={SlidersIcon}
          title="Le filtre d’Instagram, tel quel"
          text="Tri, date de début et date de fin du like : les réglages de son panneau « Trier et filtrer », appliqués pour toi sur ta page des likes."
          className="md:col-span-2"
          order={0}
        >
          <div className="rounded-lg border border-border bg-surface-muted p-4">
            <MockFilterSummary />
          </div>
        </Feature>
        <Feature
          icon={ActivityIcon}
          title="Suivi en direct"
          text="Progression, vitesse et temps restant, mis à jour à chaque lot."
          order={1}
        >
          <div className="flex items-center gap-3 rounded-lg border border-border bg-surface-muted p-4 text-small text-fg">
            <LiveDot />
            <span className="flex-1">Lot en cours</span>
            <span className="text-caption text-fg-muted tabular-nums">18 / min</span>
          </div>
        </Feature>
        <Feature
          icon={GaugeIcon}
          title="Un essai d’abord"
          text="Lis seulement les premiers likes de la liste, ou limite un lancement, pour tester sur un petit volume."
          order={0}
        />
        <Feature
          icon={PauseIcon}
          title="Pause et reprise"
          text="Mets en pause quand tu veux : le nettoyage repart exactement là où il s’était arrêté."
          order={1}
        />
        <Feature
          icon={KeyboardIcon}
          title="Accessible partout"
          text="Clavier, lecteur d’écran, thème clair ou sombre, mobile comme ordinateur."
          order={2}
        />
        <Feature
          icon={FileTextIcon}
          title="Un rapport complet"
          text="Bilan chiffré, échecs détaillés et export CSV pour garder une trace de chaque like retiré."
          className="md:col-span-2 lg:col-span-3"
          order={0}
        >
          <div className="rounded-lg border border-border bg-surface-muted p-4">
            <MockReport />
          </div>
        </Feature>
      </ul>
    </Section>
  )
}

// --- Sécurité -----------------------------------------------------------------------------

export function Security() {
  return (
    <Section
      id="securite"
      eyebrow="Sécurité et transparence"
      title="Ce qu’IUC s’interdit, et ce qu’il faut savoir"
      intro="Des engagements inscrits dans le code, et les risques présentés sans détour."
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <article className="card p-6 sm:p-8" {...reveal(0)}>
          <h3 className="flex items-center gap-3 text-h3 text-fg">
            <ShieldIcon className="h-6 w-6 text-success-strong" />
            Ce qu’IUC ne fait jamais
          </h3>
          <ul className="mt-6 space-y-3 text-body text-fg-muted">
            {[
              'Lire, demander ou stocker ton mot de passe.',
              'Envoyer tes données ailleurs que sur ton ordinateur.',
              'Retirer un like que tu n’as pas validé dans l’aperçu.',
              'Répondre à ta place aux fenêtres d’Instagram (sécurité, consentement).',
            ].map((line) => (
              <li key={line} className="flex gap-3">
                <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-success-strong" />
                {line}
              </li>
            ))}
          </ul>
        </article>
        <article className="card border-warning-border bg-warning-soft p-6 sm:p-8" {...reveal(1)}>
          <h3 className="flex items-center gap-3 text-h3 text-warning-fg">
            <AlertIcon className="h-6 w-6 text-warning-strong" />
            Les risques à connaître
          </h3>
          <ul className="mt-6 space-y-3 text-body text-warning-fg">
            {[
              'Les conditions d’utilisation d’Instagram n’autorisent pas l’automatisation : un blocage temporaire est possible, une suspension plus rare.',
              'Teste d’abord sur un compte secondaire, avec de petits volumes.',
              'Retirer un like efface la trace visible, pas ce que l’algorithme a déjà appris.',
            ].map((line) => (
              <li key={line} className="flex gap-3">
                <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-warning-strong" />
                {line}
              </li>
            ))}
          </ul>
        </article>
      </div>
    </Section>
  )
}

// --- Questions fréquentes -------------------------------------------------------------------

const questions = [
  [
    'Dois-je donner mon mot de passe ?',
    'Non. Tu te connectes toi-même dans une fenêtre dédiée. IUC ne lit aucun champ du formulaire : il vérifie seulement que ta session est ouverte.',
  ],
  [
    'Mon compte risque-t-il quelque chose ?',
    'Instagram n’autorise pas l’automatisation. IUC limite la cadence (lots, pauses, plafond par jour) et s’arrête au moindre signal, mais le risque zéro n’existe pas. Commence par un compte secondaire.',
  ],
  [
    'Puis-je choisir précisément quels likes retirer ?',
    'Oui, en deux temps. Le filtre d’Instagram cible une période (date de début, date de fin du like) dans l’ordre de ton choix. Puis l’aperçu liste chaque like ciblé : tu décoches ceux que tu veux garder.',
  ],
  [
    'Pourquoi pas de filtre par compte ou par type de contenu ?',
    'Instagram web ne le propose pas : son panneau « Trier et filtrer » se limite au tri et aux dates. IUC s’en tient à ce filtre. L’aperçu affiche le compte et le type de chaque like, pour décocher ceux à garder.',
  ],
  [
    'Combien de temps faut-il ?',
    'Environ une minute pour vingt-cinq likes. Au-delà de la limite quotidienne (150 par défaut), le nettoyage se poursuit le lendemain là où il s’était arrêté.',
  ],
  [
    'Que deviennent mes données ?',
    'Elles restent dans le dossier d’IUC sur ton ordinateur. Tu peux tout supprimer depuis le rapport d’un nettoyage.',
  ],
  [
    'IUC est-il lié à Instagram ?',
    'Non. IUC est un projet indépendant, sans lien avec Instagram ni Meta.',
  ],
] as const

export function Faq() {
  return (
    <Section
      id="faq"
      band
      eyebrow="FAQ"
      title="Questions fréquentes"
      intro="Les réponses aux questions qu’on se pose avant de commencer."
    >
      <div className="card max-w-prose divide-y divide-border px-6" {...reveal(0)}>
        {questions.map(([question, answer]) => (
          <Disclosure key={question} summary={question}>
            <p className="text-body text-fg-muted">{answer}</p>
          </Disclosure>
        ))}
      </div>
    </Section>
  )
}

// --- Appel final ----------------------------------------------------------------------------

export function FinalCallToAction() {
  return (
    <section aria-labelledby="cta-titre" className="pb-16 sm:pb-24 lg:pb-32">
      <Container>
        <div className="cta-panel px-6 py-16 text-center sm:px-12 sm:py-24" {...reveal(0, 'scale')}>
          <h2 id="cta-titre" className="mx-auto max-w-text text-h2">
            Prêt à faire le ménage ?
          </h2>
          <p className="cta-muted mx-auto mt-4 max-w-text text-lead">
            Quelques minutes suffisent pour préparer ton premier nettoyage. Tu vérifies tout avant
            que le moindre like ne soit retiré.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <ButtonLink
              to="/commencer"
              size="lg"
              variant="inverse"
              magnetic
              trailingIcon={<ArrowRightIcon />}
            >
              Commencer le nettoyage
            </ButtonLink>
          </div>
          <p className="cta-muted mt-6 flex items-center justify-center gap-2 text-small">
            <RotateIcon className="h-4 w-4" />
            Gratuit, open source, et tu peux tout arrêter à tout moment.
          </p>
        </div>
      </Container>
    </section>
  )
}
