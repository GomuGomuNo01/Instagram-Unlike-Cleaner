import type { CSSProperties, ReactNode } from 'react'

import { Avatar } from '../../components/Avatar'
import { CheckIcon, LockIcon, ShieldIcon } from '../../components/icons'
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
  { author: 'compte_humour', detail: 'Vidéo, aimée le 12/03/2021', keep: false },
  { author: 'page_memes', detail: 'Photo, aimée le 08/11/2020', keep: false },
  { author: 'ami_proche', detail: 'Carrousel, aimée le 24/06/2022', keep: true },
  { author: 'club_sport', detail: 'Vidéo, aimée le 02/01/2021', keep: false },
  { author: 'cuisine_facile', detail: 'Photo, aimée le 17/09/2019', keep: false },
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

function Chip({ children, selected = false }: { children: ReactNode; selected?: boolean }) {
  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-full border px-3 text-caption font-medium ${
        selected
          ? 'border-primary bg-primary-soft text-primary-strong'
          : 'border-border-strong text-fg-muted'
      }`}
    >
      {children}
    </span>
  )
}

const accounts = [
  { author: 'compte_humour', likes: 46 },
  { author: 'page_memes', likes: 31 },
  { author: 'club_sport', likes: 18 },
  { author: 'ami_proche', likes: 12 },
]

/** Liste des comptes trouvés dans les likes, avec leur poids relatif. */
export function MockAccounts({ count = accounts.length }: { count?: number }) {
  const max = accounts[0]?.likes ?? 1
  return (
    <ul className="space-y-3">
      {accounts.slice(0, count).map((account) => (
        <li key={account.author} className="flex items-center gap-3">
          <Avatar author={account.author} />
          <span className="min-w-0 flex-1">
            <span className="flex items-center justify-between gap-2 text-small">
              <span className="truncate font-medium text-fg">@{account.author}</span>
              <span className="text-caption text-fg-muted tabular-nums">{account.likes} likes</span>
            </span>
            <span className="mt-1 block h-1 overflow-hidden rounded-full bg-fill">
              <span
                className="block h-full origin-left rounded-full bg-primary"
                style={{ scale: `${account.likes / max} 1` } as CSSProperties}
              />
            </span>
          </span>
        </li>
      ))}
    </ul>
  )
}

/** Écran des critères : période, type de contenu et comptes. */
export function MockCriteria() {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-caption font-semibold text-fg">Période</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Chip selected>Du 01/01/2019</Chip>
          <Chip selected>Au 31/12/2021</Chip>
        </div>
      </div>
      <div>
        <p className="text-caption font-semibold text-fg">Type de contenu</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Chip>Tous</Chip>
          <Chip selected>Reels</Chip>
          <Chip>Publications</Chip>
        </div>
      </div>
      <div>
        <p className="flex items-center gap-2 text-caption font-semibold text-fg">
          <ShieldIcon className="h-4 w-4 text-success-strong" />
          Ne jamais toucher à ces comptes
        </p>
        <div className="mt-2">
          <MockAccounts count={3} />
        </div>
      </div>
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
          ['Retirés', '96'],
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
          <span className="tabular-nums">14:02:31</span>Lot retiré : 18 likes (total 96).
        </li>
        <li className="flex gap-3">
          <span className="tabular-nums">14:01:12</span>Lot retiré : 18 likes (total 78).
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
