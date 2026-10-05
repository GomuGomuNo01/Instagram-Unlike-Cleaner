import type { CSSProperties, ReactNode } from 'react'

import { AlertIcon, CheckCircleIcon, InfoIcon, XCircleIcon } from '../icons'
import { Spinner } from './Button'

// Retours d'état : messages, pastilles, chargements, progression et chiffres clés.
// Chaque état est porté par un texte (et une icône), jamais par la seule couleur.

export type Tone = 'info' | 'success' | 'warning' | 'danger'

const alertIcons = {
  info: InfoIcon,
  success: CheckCircleIcon,
  warning: AlertIcon,
  danger: XCircleIcon,
} as const

/** Message d'état. Les messages « danger » sont annoncés tout de suite aux lecteurs d'écran. */
export function Alert({
  tone = 'info',
  title,
  children,
  className = '',
}: {
  tone?: Tone
  title?: string
  children?: ReactNode
  className?: string
}) {
  const Icon = alertIcons[tone]
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      data-tone={tone}
      className={`alert animate-fade-up ${className}`}
    >
      <Icon data-icon="" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? 'mt-1' : ''}>{children}</div>}
      </div>
    </div>
  )
}

export function Badge({
  children,
  tone,
}: {
  children: ReactNode
  tone?: Tone | 'primary' | 'neutral'
}) {
  return (
    <span className="badge" data-tone={tone === 'neutral' ? undefined : tone}>
      {children}
    </span>
  )
}

/** Chargement d'un contenu court : indicateur et texte explicite. */
export function Loading({ label }: { label: string }) {
  return (
    <span role="status" className="inline-flex items-center gap-3 text-small text-fg-muted">
      <Spinner />
      {label}
    </span>
  )
}

/** Silhouette d'un contenu en cours de chargement. */
export function Skeleton({ className = '' }: { className?: string }) {
  return <span aria-hidden="true" className={`skeleton block ${className}`} />
}

/** Bloc de silhouettes, annoncé comme un chargement aux lecteurs d'écran. */
export function SkeletonBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="status" aria-busy="true" aria-label={label}>
      {children}
    </div>
  )
}

export function ProgressBar({
  value,
  label,
  indeterminate = false,
}: {
  value: number
  label: string
  indeterminate?: boolean
}) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : value}
      data-indeterminate={indeterminate || undefined}
      className="progress"
      style={{ '--progress': value / 100 } as CSSProperties}
    >
      <div className="progress-fill" />
    </div>
  )
}

/** Chiffre clé, à placer dans une liste de définitions (<dl>). La valeur réapparaît en
 * douceur quand elle change, pour signaler la mise à jour. */
export function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-surface-muted px-4 py-3">
      <dt className="text-caption font-medium text-fg-muted">{label}</dt>
      <dd className="mt-1 text-h3 tabular-nums">
        <span key={value} className="inline-block animate-value">
          {value}
        </span>
      </dd>
    </div>
  )
}

/** Point « en direct » : une activité est en cours. */
export function LiveDot({ tone = 'success' }: { tone?: 'success' | 'primary' }) {
  return (
    <span
      aria-hidden="true"
      className={`live-dot relative inline-flex h-2 w-2 shrink-0 rounded-full ${
        tone === 'success' ? 'bg-success-strong' : 'bg-primary'
      }`}
    />
  )
}
