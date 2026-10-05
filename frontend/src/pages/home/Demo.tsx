import { useEffect, useState } from 'react'

import { Avatar } from '../../components/Avatar'
import { ArrowRightIcon, CheckIcon, PlayIcon, RotateIcon } from '../../components/icons'
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  Checkbox,
  ChoiceGroup,
  ProgressBar,
  Section,
} from '../../components/ui'
import { plural } from '../../lib/format'
import { reveal } from '../../lib/motion'

// Démonstration interactive : une simulation du parcours (critères, aperçu, nettoyage) sur
// des likes fictifs. Aucune connexion à Instagram, aucune donnée enregistrée.

type Kind = 'photo' | 'video' | 'carousel'
type Period = 'all' | 'before' | 'since'
type ContentChoice = 'all' | 'posts' | 'reels'

interface DemoLike {
  id: number
  author: string
  kind: Kind
  year: number
}

const LIKES: DemoLike[] = [
  { id: 1, author: 'compte_humour', kind: 'video', year: 2019 },
  { id: 2, author: 'page_memes', kind: 'photo', year: 2019 },
  { id: 3, author: 'ami_proche', kind: 'carousel', year: 2020 },
  { id: 4, author: 'club_sport', kind: 'video', year: 2020 },
  { id: 5, author: 'cuisine_facile', kind: 'photo', year: 2021 },
  { id: 6, author: 'page_memes', kind: 'video', year: 2021 },
  { id: 7, author: 'voyage_photo', kind: 'carousel', year: 2022 },
  { id: 8, author: 'ami_proche', kind: 'photo', year: 2022 },
  { id: 9, author: 'compte_humour', kind: 'photo', year: 2023 },
  { id: 10, author: 'musique_live', kind: 'video', year: 2023 },
]

const PROTECTABLE = ['ami_proche', 'club_sport', 'voyage_photo']
const BATCH = 3 // likes retirés par lot dans la simulation
const TICK_MS = 700 // rythme de la simulation (le vrai nettoyage est bien plus lent)

const kindLabels: Record<Kind, string> = { photo: 'Photo', video: 'Vidéo', carousel: 'Carrousel' }

const periods = [
  { value: 'all', label: 'Tout l’historique' },
  { value: 'before', label: 'Avant 2021' },
  { value: 'since', label: 'Depuis 2021' },
] as const

const contents = [
  { value: 'all', label: 'Tous' },
  { value: 'posts', label: 'Publications' },
  { value: 'reels', label: 'Reels' },
] as const

function matches(like: DemoLike, period: Period, content: ContentChoice): boolean {
  if (period === 'before' && like.year >= 2021) return false
  if (period === 'since' && like.year < 2021) return false
  if (content === 'reels') return like.kind === 'video'
  if (content === 'posts') return like.kind !== 'video'
  return true
}

export function Demo() {
  return (
    <Section
      id="demo"
      band
      eyebrow="Démonstration interactive"
      title="Essaie avant de te lancer"
      intro="Une simulation avec des likes fictifs : règle les critères, décoche ce que tu veux garder, puis lance le nettoyage. Aucune connexion à Instagram."
    >
      <div {...reveal(0, 'scale')}>
        <DemoSimulator />
      </div>
    </Section>
  )
}

export function DemoSimulator() {
  const [period, setPeriod] = useState<Period>('all')
  const [content, setContent] = useState<ContentChoice>('all')
  const [protectedAuthors, setProtectedAuthors] = useState<string[]>(['ami_proche'])
  const [kept, setKept] = useState<number[]>([])
  const [queue, setQueue] = useState<number[] | null>(null) // null : réglages en cours
  const [removedCount, setRemovedCount] = useState(0)

  const targeted = LIKES.filter(
    (like) => matches(like, period, content) && !protectedAuthors.includes(like.author),
  )
  const toRemove = targeted.filter((like) => !kept.includes(like.id))
  const running = queue !== null && removedCount < queue.length
  const finished = queue !== null && !running
  const removed = new Set(queue?.slice(0, removedCount))
  const locked = queue !== null

  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => setRemovedCount((count) => count + BATCH), TICK_MS)
    return () => window.clearInterval(timer)
  }, [running])

  const start = () => {
    setQueue(toRemove.map((like) => like.id))
    setRemovedCount(0)
  }
  const reset = () => {
    setQueue(null)
    setRemovedCount(0)
    setKept([])
  }
  const toggleProtected = (author: string) =>
    setProtectedAuthors((list) =>
      list.includes(author) ? list.filter((item) => item !== author) : [...list, author],
    )

  const total = queue?.length ?? 0
  const done = Math.min(removedCount, total)
  const status = finished
    ? `Simulation terminée : ${plural(done, 'like retiré', 'likes retirés')}, ${plural(
        LIKES.length - done,
        'like gardé',
        'likes gardés',
      )}.`
    : running
      ? `Retrait en cours : ${done} sur ${total}.`
      : `${plural(toRemove.length, 'like sera retiré', 'likes seront retirés')} sur ${plural(
          LIKES.length,
          'like',
        )}.`

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      <Card padding="lg" className="lg:col-span-5">
        <h3 className="text-h3 text-fg">1. Tes critères</h3>
        <div className="mt-6 space-y-6">
          <fieldset disabled={locked} className="space-y-6 disabled:opacity-60">
            <ChoiceGroup
              legend="Période du like"
              name="demo-periode"
              options={periods}
              value={period}
              onChange={setPeriod}
            />
            <ChoiceGroup
              legend="Type de contenu"
              name="demo-contenu"
              options={contents}
              value={content}
              onChange={setContent}
            />
            <div>
              <p className="text-small font-medium text-fg">Ne jamais toucher à ces comptes</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {PROTECTABLE.map((author) => {
                  const pressed = protectedAuthors.includes(author)
                  return (
                    <button
                      key={author}
                      type="button"
                      aria-pressed={pressed}
                      onClick={() => toggleProtected(author)}
                      className={`inline-flex min-h-11 items-center gap-2 rounded-full border px-4 text-small font-medium transition-colors ${
                        pressed
                          ? 'border-primary bg-primary-soft text-primary-strong'
                          : 'border-border-strong bg-surface text-fg hover:border-fg-subtle'
                      }`}
                    >
                      {pressed && <CheckIcon className="h-4 w-4 animate-pop" />}@{author}
                    </button>
                  )
                })}
              </div>
            </div>
          </fieldset>
        </div>
      </Card>

      <Card padding="none" className="overflow-hidden lg:col-span-7">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-4">
          <h3 className="text-h3 text-fg">2. Aperçu et nettoyage</h3>
          <Badge tone={finished ? 'success' : running ? 'info' : 'primary'}>
            {finished ? 'terminé' : running ? 'en cours' : 'prêt'}
          </Badge>
        </div>

        <div className="px-6 pt-4">
          <p aria-live="polite" className="text-small font-medium text-fg">
            {status}
          </p>
          {queue !== null && (
            <div className="mt-3">
              <ProgressBar
                value={total ? Math.round((done / total) * 100) : 100}
                label="Progression de la simulation"
              />
            </div>
          )}
        </div>

        <ul aria-label="Likes ciblés par la simulation" className="mt-2 divide-y divide-border">
          {targeted.length === 0 && (
            <li className="px-6 py-8 text-center text-small text-fg-muted">
              Aucun like ne correspond à ces critères.
            </li>
          )}
          {targeted.map((like) => {
            const isKept = kept.includes(like.id)
            const isRemoved = removed.has(like.id)
            return (
              <li key={like.id} className="demo-row" data-removed={isRemoved || undefined}>
                <label className="flex min-h-14 cursor-pointer items-center gap-3 px-6 py-2 hover:bg-fill has-disabled:cursor-default has-disabled:hover:bg-transparent">
                  <Checkbox
                    checked={!isKept}
                    disabled={locked}
                    onChange={(event) =>
                      setKept((list) =>
                        event.target.checked
                          ? list.filter((id) => id !== like.id)
                          : [...list, like.id],
                      )
                    }
                    aria-label={`Retirer le like de @${like.author} (${kindLabels[like.kind]}, ${like.year})`}
                  />
                  <Avatar author={like.author} />
                  <span className="min-w-0 flex-1">
                    <span data-author className="block truncate text-small font-medium text-fg">
                      @{like.author}
                    </span>
                    <span className="block text-caption text-fg-muted">
                      {kindLabels[like.kind]}, aimée en {like.year}
                    </span>
                  </span>
                  {isRemoved ? (
                    <Badge tone="success">retiré</Badge>
                  ) : isKept ? (
                    <Badge>gardé</Badge>
                  ) : null}
                </label>
              </li>
            )
          })}
        </ul>

        <div className="flex flex-col gap-3 border-t border-border px-6 py-4 sm:flex-row sm:items-center sm:justify-end">
          {finished ? (
            <>
              <Button variant="secondary" onClick={reset} icon={<RotateIcon className="h-4 w-4" />}>
                Recommencer
              </Button>
              <ButtonLink to="/commencer" trailingIcon={<ArrowRightIcon />}>
                Nettoyer mes vrais likes
              </ButtonLink>
            </>
          ) : (
            <Button
              onClick={start}
              loading={running}
              disabled={toRemove.length === 0}
              icon={<PlayIcon className="h-4 w-4" />}
            >
              {running ? 'Simulation en cours…' : 'Lancer la simulation'}
            </Button>
          )}
        </div>
        {finished && (
          <div className="px-6 pb-6">
            <Alert tone="success" title="C’est exactement ce que fait IUC">
              En vrai, les likes sont retirés par lots de 18 avec des pauses, et un rapport détaillé
              t’attend à la fin.
            </Alert>
          </div>
        )}
      </Card>
    </div>
  )
}
