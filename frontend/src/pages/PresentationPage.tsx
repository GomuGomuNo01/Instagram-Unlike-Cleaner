import { useRef } from 'react'

import { AppPage } from '../components/Layout'
import { ArrowRightIcon, DownloadIcon, PlayIcon } from '../components/icons'
import { WINDOWS_DOWNLOAD } from '../components/navigation'
import { ButtonLink, Card, PageHeader } from '../components/ui'
import { prefersReducedMotion } from '../lib/motion'

const VIDEO = `${import.meta.env.BASE_URL}presentation.mp4`
const POSTER = `${import.meta.env.BASE_URL}presentation-poster.jpg`
const DEMO = import.meta.env.VITE_DEMO === 'true'

/** Chapitres de la vidéo (muette) : repères cliquables et équivalent textuel de chaque scène.
 * Les instants suivent l'animation source, docs/video/presentation.html. */
const chapters = [
  {
    at: 0,
    title: 'IUC',
    text: 'Des années de « J’aime » effacés, sans confier ton mot de passe.',
  },
  {
    at: 3.2,
    title: 'Le problème',
    text: '1 493 likes accumulés : à la main, des heures de clics ; avec un outil en ligne, ton mot de passe en jeu.',
  },
  {
    at: 6.2,
    title: '1. Connexion',
    text: 'Tu te connectes toi-même dans une fenêtre dédiée, double authentification comprise. IUC ne lit jamais ton mot de passe.',
  },
  {
    at: 9.4,
    title: '2. Filtre d’Instagram',
    text: 'Tri, date de début et date de fin du like : IUC remplit pour toi le panneau « Trier et filtrer ».',
  },
  {
    at: 12.6,
    title: '3. Aperçu',
    text: 'Chaque like ciblé est listé avec son compte. Tu décoches ceux que tu veux garder.',
  },
  {
    at: 15.8,
    title: '4. Nettoyage',
    text: 'Retrait par lots avec pauses, limite par jour et arrêt au moindre signal, puis un rapport complet.',
  },
  {
    at: 18.8,
    title: 'À toi de jouer',
    text: 'Essaie la démo, ou télécharge IUC pour Windows.',
  },
] as const

function clock(seconds: number): string {
  const whole = Math.floor(seconds)
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}

/** Présentation : IUC et son fonctionnement en une vidéo de 20 secondes. */
export function PresentationPage() {
  const video = useRef<HTMLVideoElement>(null)

  const jumpTo = (seconds: number) => {
    const player = video.current
    if (!player) return
    player.currentTime = seconds
    void player.play().catch(() => {
      // Lecture refusée par le navigateur : la vidéo reste positionnée sur le chapitre.
    })
  }

  return (
    <AppPage>
      <PageHeader
        eyebrow="Présentation"
        title="IUC en 20 secondes"
        description="L’application et son fonctionnement, de la connexion au rapport : une présentation animée, sans son."
      />
      <Card padding="none" className="overflow-hidden">
        <video
          ref={video}
          src={VIDEO}
          poster={POSTER}
          controls
          muted
          playsInline
          preload="metadata"
          // Lecture automatique, sauf si le système demande de limiter les animations.
          autoPlay={!prefersReducedMotion()}
          aria-describedby="chapitres"
          className="block aspect-video w-full bg-surface-sunken"
        >
          <a href={VIDEO}>Télécharger la vidéo de présentation (MP4)</a>
        </video>
      </Card>

      <section aria-labelledby="chapitres-titre" className="mt-12">
        <h2 id="chapitres-titre" className="text-h3 text-fg">
          Ce que montre la vidéo
        </h2>
        <ol
          id="chapitres"
          aria-labelledby="chapitres-titre"
          className="mt-4 grid gap-3 sm:grid-cols-2"
        >
          {chapters.map((chapter) => (
            <li key={chapter.at}>
              <button
                type="button"
                onClick={() => jumpTo(chapter.at)}
                className="card card-interactive flex h-full w-full items-start gap-4 p-4 text-left"
              >
                <span className="inline-flex min-h-8 shrink-0 items-center gap-2 rounded-full bg-primary-soft px-3 text-caption font-semibold text-primary-strong tabular-nums">
                  <PlayIcon className="h-3 w-3" />
                  {clock(chapter.at)}
                </span>
                <span>
                  <span className="block text-small font-semibold text-fg">{chapter.title}</span>
                  <span className="mt-1 block text-small text-fg-muted">{chapter.text}</span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      </section>

      <div className="mt-12 flex flex-col gap-3 sm:flex-row sm:items-center">
        <ButtonLink to="/#demo" size="lg" trailingIcon={<ArrowRightIcon />}>
          Essayer la démo interactive
        </ButtonLink>
        {DEMO ? (
          <a href={WINDOWS_DOWNLOAD} download className="btn btn-secondary btn-lg">
            <DownloadIcon className="h-5 w-5" />
            Télécharger pour Windows
          </a>
        ) : (
          <ButtonLink to="/commencer" variant="secondary" size="lg">
            Commencer un nettoyage
          </ButtonLink>
        )}
        <a href={VIDEO} download className="link text-small sm:ml-auto">
          Télécharger la vidéo (MP4, 3,4 Mo)
        </a>
      </div>
    </AppPage>
  )
}
