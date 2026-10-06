import type { CSSProperties, ReactNode } from 'react'

import { Avatar } from '../../components/Avatar'
import { CheckIcon, ChevronDownIcon, LockIcon } from '../../components/icons'
import { Badge, LiveDot } from '../../components/ui'

// Illustrations du produit : reproductions simplifiées des écrans d'IUC, avec des comptes
// fictifs. Purement visuelles (aria-hidden chez l'appelant) : le texte voisin porte le sens.

export function MockWindow({
  title,
  children,
  className = '',
}: {
  title: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`window ${className}`}>
      <div className="window-bar">
        <span className="window-dot" />
        <span className="window-dot" />
        <span className="window-dot" />
        <span className="ml-2 truncate text-caption font-medium text-fg-muted">{title}</span>
      </div>
      <div className="p-4 sm:p-6">{children}</div>
    </div>
  )
}

const previewRows = [
  { author: 'compte_humour', detail: 'Vidéo, partagée le 12/03/2021', keep: false },
  { author: 'page_memes', detail: 'Photo, partagée le 08/11/2020', keep: false },
  { author: 'ami_proche', detail: 'Carrousel, partagée le 24/06/2021', keep: true },
  { author: 'club_sport', detail: 'Vidéo, partagée le 02/01/2021', keep: false },
  { author: 'cuisine_facile', detail: 'Photo, partagée le 17/09/2019', keep: false },
]

/** Écran d'aperçu : likes ciblés, cases à cocher et action de lancement. */
export function MockPreview({ rows = previewRows.length }: { rows?: number }) {
  const shown = previewRows.slice(0, rows)
  const removed = shown.filter((row) => !row.keep).length
  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <p className="text-small font-semibold text-fg">Aperçu du nettoyage</p>
        <Badge tone="primary">prêt</Badge>
      </div>
      <p className="mt-1 text-caption text-fg-muted">
        {removed} likes seront retirés sur {shown.length}
      </p>
      <ul className="mt-4 divide-y divide-border">
        {shown.map((row) => (
          <li key={row.author} className="flex items-center gap-3 py-3">
            <span className="checkbox" data-checked={!row.keep} />
            <Avatar author={row.author} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-small font-medium text-fg">@{row.author}</span>
              <span className="block truncate text-caption text-fg-muted">{row.detail}</span>
            </span>
            {row.keep && <Badge>gardé</Badge>}
          </li>
        ))}
      </ul>
      <div className="mt-4 flex justify-end">
        <span className="btn btn-primary pointer-events-none">Lancer le nettoyage</span>
      </div>
    </div>
  )
}

/** Écran de connexion : la session est ouverte par l'utilisateur lui-même. */
export function MockLogin() {
  const rows = [
    { label: 'Fenêtre Chromium dédiée ouverte', done: true },
    { label: 'Connexion faite par toi, 2FA comprise', done: true },
    { label: 'Page de tes likes accessible', done: true },
  ]
  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <p className="text-small font-semibold text-fg">Session Instagram</p>
        <Badge tone="success">connecté</Badge>
      </div>
      <ul className="mt-4 space-y-3">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center gap-3 text-small text-fg">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-success-soft text-success-strong">
              <CheckIcon className="h-4 w-4" />
            </span>
            {row.label}
          </li>
        ))}
      </ul>
      <div className="mt-6 flex items-center gap-3 rounded-lg bg-surface-muted p-3 text-caption text-fg-muted">
        <LockIcon className="h-4 w-4 text-primary-strong" />
        Mot de passe lu ou stocké par IUC : jamais
      </div>
    </div>
  )
}

function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex min-h-8 items-center rounded-full border border-primary bg-primary-soft px-3 text-caption font-medium text-primary-strong">
      {children}
    </span>
  )
}

/** Résumé du filtre d'Instagram appliqué à un nettoyage. */
export function MockFilterSummary() {
  return (
    <div className="flex flex-wrap gap-2">
      <Chip>Du plus récent au plus ancien</Chip>
      <Chip>Début : 01/01/2019</Chip>
      <Chip>Fin : 31/12/2021</Chip>
    </div>
  )
}

const sortRows = ['Du plus récent au plus ancien', 'Du plus ancien au plus récent']
const dateRows = [
  { label: 'Date de début', parts: ['janv.', '1', '2019'] },
  { label: 'Date de fin', parts: ['déc.', '31', '2021'] },
]

/** Écran des critères : le panneau « Trier et filtrer » d'Instagram, rempli par IUC. */
export function MockCriteria() {
  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <p className="text-small font-semibold text-fg">Trier et filtrer</p>
        <Badge tone="info">Filtre d’Instagram</Badge>
      </div>
      <p className="mt-4 text-caption font-semibold text-fg">Trier par</p>
      <ul className="mt-2 space-y-2">
        {sortRows.map((label, index) => (
          <li key={label} className="flex items-center justify-between gap-3 text-small text-fg">
            {label}
            <span
              className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border ${
                index === 0 ? 'border-primary' : 'border-border-strong'
              }`}
            >
              {index === 0 && <span className="h-2 w-2 rounded-full bg-primary" />}
            </span>
          </li>
        ))}
      </ul>
      {dateRows.map((row) => (
        <div key={row.label} className="mt-3">
          <p className="text-caption font-semibold text-fg">{row.label}</p>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {row.parts.map((part) => (
              <span
                key={part}
                className="flex items-center justify-between gap-1 rounded-sm border border-border-strong px-3 py-2 text-caption text-fg"
              >
                {part}
                <ChevronDownIcon className="h-3 w-3 text-fg-muted" />
              </span>
            ))}
          </div>
        </div>
      ))}
      <span className="btn btn-primary pointer-events-none mt-4 w-full">Appliquer</span>
    </div>
  )
}

/** Écran de suivi : progression, vitesse et journal. */
export function MockProgress() {
  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <p className="flex items-center gap-2 text-small font-semibold text-fg">
          <LiveDot />
          Nettoyage en cours
        </p>
        <span className="text-caption text-fg-muted tabular-nums">64 %</span>
      </div>
      <div className="progress mt-4" style={{ '--progress': 0.64 } as CSSProperties}>
        <div className="progress-fill" />
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-2">
        {[
          ['Retirés', '100'],
          ['Vitesse', '18 / min'],
          ['Restant', '≈ 3 min'],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg bg-surface-muted px-3 py-2">
            <dt className="text-caption text-fg-muted">{label}</dt>
            <dd className="text-small font-semibold text-fg tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <ol className="mt-4 space-y-2 text-caption text-fg-muted">
        <li className="flex gap-3">
          <span className="tabular-nums">14:02:31</span>Lot retiré : 20 likes (total 100).
        </li>
        <li className="flex gap-3">
          <span className="tabular-nums">14:01:12</span>Lot retiré : 20 likes (total 80).
        </li>
        <li className="flex gap-3">
          <span className="tabular-nums">14:00:05</span>Pause entre deux lots, comme prévu.
        </li>
      </ol>
    </div>
  )
}

/** Extrait du rapport final (export CSV). */
export function MockReport() {
  const lines = [
    ['@compte_humour', 'Vidéo', 'retiré'],
    ['@page_memes', 'Photo', 'retiré'],
    ['@ami_proche', 'Carrousel', 'gardé'],
    ['@club_sport', 'Vidéo', 'retiré'],
  ]
  return (
    <table className="w-full text-left text-caption">
      <thead className="text-fg-muted">
        <tr>
          <th className="pb-2 font-medium">Compte</th>
          <th className="pb-2 font-medium">Type</th>
          <th className="pb-2 font-medium">Statut</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border text-fg">
        {lines.map(([author, kind, status]) => (
          <tr key={author}>
            <td className="py-2 font-medium">{author}</td>
            <td className="py-2 text-fg-muted">{kind}</td>
            <td className="py-2">
              <Badge tone={status === 'retiré' ? 'success' : undefined}>{status}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
