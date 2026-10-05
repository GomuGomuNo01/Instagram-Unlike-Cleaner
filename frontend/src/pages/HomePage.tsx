import type { ReactNode } from 'react'
import { Link } from 'react-router'

import {
  AlertIcon,
  ArrowRightIcon,
  BriefcaseIcon,
  CheckIcon,
  ChevronDownIcon,
  ClockIcon,
  ListCheckIcon,
  LockIcon,
  ShieldIcon,
} from '../components/icons'
import { Badge, ButtonLink } from '../components/ui'

/** Page d'accueil : proposition de valeur, fonctionnement, confiance, FAQ et appel à l'action. */
export function HomePage() {
  return (
    <>
      <Hero />
      <Benefits />
      <HowItWorks />
      <KeyFigures />
      <Features />
      <Security />
      <Faq />
      <FinalCallToAction />
    </>
  )
}

function Section({
  id,
  title,
  intro,
  muted = false,
  children,
}: {
  id: string
  title: string
  intro?: string
  muted?: boolean
  children: ReactNode
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-titre`}
      className={`py-16 sm:py-24 ${muted ? 'bg-zinc-50 dark:bg-zinc-900/40' : ''}`}
    >
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="max-w-2xl">
          <h2 id={`${id}-titre`} className="text-h2">
            {title}
          </h2>
          {intro && <p className="text-lead mt-4">{intro}</p>}
        </div>
        <div className="mt-12">{children}</div>
      </div>
    </section>
  )
}

function Hero() {
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-12 pb-16 sm:px-6 sm:pt-16 sm:pb-24 lg:grid-cols-2">
      <div>
        <p className="eyebrow">100 % local, sans mot de passe demandé</p>
        <h1 className="text-display mt-4">Fais le ménage dans tes « J’aime » Instagram</h1>
        <p className="text-lead mt-6 max-w-xl">
          Des années de likes, retirés en quelques clics. Tu choisis les critères, tu vérifies la
          liste, IUC s’occupe du reste. Rien ne quitte ton ordinateur.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/commencer" size="lg">
            Commencer le nettoyage
            <ArrowRightIcon />
          </ButtonLink>
          <ButtonLink to="/#fonctionnement" variant="secondary" size="lg">
            Voir comment ça marche
          </ButtonLink>
        </div>
        <ul className="mt-8 space-y-2">
          {[
            'Aperçu obligatoire avant tout retrait',
            'Rythme prudent, pause automatique au moindre signal',
            'Rapport détaillé à la fin de chaque nettoyage',
          ].map((point) => (
            <li key={point} className="text-small flex items-center gap-2">
              <CheckIcon className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              {point}
            </li>
          ))}
        </ul>
      </div>
      <ProductPreview />
    </section>
  )
}

const previewRows = [
  { author: 'compte_humour', detail: 'Vidéo, partagée le 12/03/2021', keep: false },
  { author: 'page_memes', detail: 'Photo, partagée le 08/11/2020', keep: false },
  { author: 'ami_proche', detail: 'Carrousel, partagée le 24/06/2022', keep: true },
  { author: 'club_sport', detail: 'Vidéo, partagée le 02/01/2021', keep: false },
]

/** Illustration du produit : reproduction simplifiée de l'écran d'aperçu. */
function ProductPreview() {
  return (
    <figure>
      <div
        aria-hidden="true"
        className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex items-center justify-between gap-4">
          <p className="font-semibold">Aperçu du nettoyage</p>
          <Badge tone="info">prêt</Badge>
        </div>
        <p className="text-small mt-1">3 likes seront retirés sur 4</p>
        <ul className="mt-6 divide-y divide-zinc-200 dark:divide-zinc-800">
          {previewRows.map((row) => (
            <li key={row.author} className="flex items-center gap-4 py-3">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded border ${
                  row.keep
                    ? 'border-zinc-400 dark:border-zinc-600'
                    : 'border-indigo-600 bg-indigo-600 text-white'
                }`}
              >
                {!row.keep && <CheckIcon className="h-4 w-4" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">@{row.author}</span>
                <span className="block truncate text-xs text-zinc-600 dark:text-zinc-400">
                  {row.detail}
                </span>
              </span>
              {row.keep && <Badge>gardé</Badge>}
            </li>
          ))}
        </ul>
        <div className="mt-6 flex justify-end">
          <span className="inline-flex min-h-11 items-center rounded-lg bg-indigo-600 px-5 text-sm font-medium text-white">
            Lancer le nettoyage
          </span>
        </div>
      </div>
      <figcaption className="sr-only">
        Exemple d’aperçu : tu décoches les likes à garder, puis tu lances le nettoyage.
      </figcaption>
    </figure>
  )
}

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

function Benefits() {
  return (
    <Section
      id="avantages"
      title="Pourquoi utiliser IUC ?"
      intro="Instagram permet de retirer ses likes, mais un par un ou par petits lots. IUC fait ce travail à ta place, avec les précautions nécessaires."
      muted
    >
      <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {benefits.map(({ icon: Icon, title, text }) => (
          <li
            key={title}
            className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
              <Icon className="h-6 w-6" />
            </span>
            <h3 className="text-h3 mt-6">{title}</h3>
            <p className="text-small mt-2">{text}</p>
          </li>
        ))}
      </ul>
    </Section>
  )
}

const steps = [
  {
    title: 'Connecte-toi',
    text: 'IUC ouvre une fenêtre dédiée. Tu t’y connectes toi-même à Instagram, double authentification comprise.',
  },
  {
    title: 'Choisis et vérifie',
    text: 'Période, type de contenu, comptes à cibler ou à protéger. Puis tu décoches ce que tu veux garder.',
  },
  {
    title: 'Nettoie en sécurité',
    text: 'Les likes sont retirés par lots, avec des pauses et une limite par jour. Un rapport conclut le tout.',
  },
]

function HowItWorks() {
  return (
    <Section
      id="fonctionnement"
      title="Comment ça marche"
      intro="Trois étapes, et tu restes maître de chacune d’elles."
    >
      <ol className="grid gap-8 md:grid-cols-3">
        {steps.map((step, index) => (
          <li key={step.title}>
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-600 text-lg font-semibold text-white">
              {index + 1}
            </span>
            <h3 className="text-h3 mt-6">{step.title}</h3>
            <p className="text-body mt-2">{step.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  )
}

const figures = [
  { value: '0', label: 'mot de passe lu ou stocké par IUC' },
  { value: '100 %', label: 'de tes données restent sur ton ordinateur' },
  { value: '150', label: 'likes par jour au maximum, par défaut, pour rester prudent' },
  { value: '240+', label: 'tests automatisés vérifient chaque version' },
]

function KeyFigures() {
  return (
    <Section
      id="confiance"
      title="Conçu pour inspirer confiance"
      intro="Des engagements vérifiables, inscrits dans le code."
      muted
    >
      <dl className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {figures.map((figure) => (
          <div
            key={figure.label}
            className="flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <dt className="text-small">{figure.label}</dt>
            <dd className="order-first text-4xl font-semibold tracking-tight text-indigo-700 dark:text-indigo-300">
              {figure.value}
            </dd>
          </div>
        ))}
      </dl>
    </Section>
  )
}

const features = [
  ['Filtres précis', 'Période du like, ordre, type de contenu, comptes ciblés ou protégés.'],
  ['Liste de tes comptes', 'Retrouve en un clic les comptes que tu as le plus aimés.'],
  ['Aperçu à cocher', 'Chaque like ciblé est listé ; tu décoches ce que tu veux garder.'],
  ['Suivi en direct', 'Progression, vitesse, temps restant, pause et reprise à tout moment.'],
  ['Reprise automatique', 'Un nettoyage interrompu repart exactement là où il s’était arrêté.'],
  ['Rapport complet', 'Bilan chiffré, échecs détaillés et export CSV pour garder une trace.'],
] as const

function Features() {
  return (
    <Section
      id="fonctionnalites"
      title="Tout ce qu’il faut, rien de plus"
      intro="Une interface simple, pensée pour aller droit au but."
    >
      <ul className="grid gap-x-12 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(([title, text]) => (
          <li key={title} className="flex gap-4">
            <CheckIcon className="mt-1 h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            <div>
              <h3 className="text-h3">{title}</h3>
              <p className="text-small mt-1">{text}</p>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  )
}

function Security() {
  return (
    <Section
      id="securite"
      title="Sécurité et transparence"
      intro="Ce qu’IUC s’interdit, et ce qu’il vaut mieux savoir avant de commencer."
      muted
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <h3 className="text-h3 flex items-center gap-3">
            <ShieldIcon className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            Ce qu’IUC ne fait jamais
          </h3>
          <ul className="text-body mt-4 list-disc space-y-2 pl-6">
            <li>Lire, demander ou stocker ton mot de passe.</li>
            <li>Envoyer tes données ailleurs que sur ton ordinateur.</li>
            <li>Retirer un like que tu n’as pas validé dans l’aperçu.</li>
            <li>Répondre à ta place aux fenêtres d’Instagram (sécurité, consentement).</li>
          </ul>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 dark:border-amber-900 dark:bg-amber-950/40">
          <h3 className="text-h3 flex items-center gap-3">
            <AlertIcon className="h-6 w-6 text-amber-700 dark:text-amber-300" />
            Les risques à connaître
          </h3>
          <ul className="text-body mt-4 list-disc space-y-2 pl-6">
            <li>
              Les conditions d’utilisation d’Instagram n’autorisent pas l’automatisation : un
              blocage temporaire est possible, une suspension plus rare.
            </li>
            <li>Teste d’abord sur un compte secondaire, avec de petits volumes.</li>
            <li>Retirer un like efface la trace visible, pas ce que l’algorithme a déjà appris.</li>
          </ul>
        </div>
      </div>
    </Section>
  )
}

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
    'Oui : période, type de contenu, comptes à cibler ou à protéger, puis un aperçu où tu décoches chaque like à garder.',
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

function Faq() {
  return (
    <Section id="faq" title="Questions fréquentes">
      <div className="max-w-3xl divide-y divide-zinc-200 border-y border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
        {questions.map(([question, answer]) => (
          <details key={question} className="group">
            <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-4 text-base font-medium">
              {question}
              <ChevronDownIcon className="h-5 w-5 text-zinc-500 transition-transform group-open:rotate-180" />
            </summary>
            <p className="text-body pb-6">{answer}</p>
          </details>
        ))}
      </div>
    </Section>
  )
}

function FinalCallToAction() {
  return (
    <section aria-labelledby="cta-titre" className="px-4 pb-16 sm:px-6 sm:pb-24">
      <div className="mx-auto max-w-6xl rounded-3xl bg-indigo-600 px-6 py-12 text-center text-white sm:px-12 sm:py-16">
        <h2 id="cta-titre" className="text-h2">
          Prêt à faire le ménage ?
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-lg leading-relaxed text-indigo-100">
          Quelques minutes suffisent pour préparer ton premier nettoyage. Tu vérifies tout avant que
          le moindre like ne soit retiré.
        </p>
        <Link
          to="/commencer"
          className="mt-8 inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-white px-6 text-base font-medium text-indigo-700 shadow-sm transition-colors hover:bg-indigo-50 active:bg-indigo-100"
        >
          Commencer le nettoyage
          <ArrowRightIcon />
        </Link>
      </div>
    </section>
  )
}
