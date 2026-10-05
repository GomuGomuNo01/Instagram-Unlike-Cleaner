import type { ComponentProps, ReactNode } from 'react'
import { Link } from 'react-router'

// --- Boutons -------------------------------------------------------------------------------
// États : normal, survol, appui, focus (contour global), désactivé et chargement.

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
type ButtonSize = 'md' | 'lg'

const base =
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium whitespace-nowrap transition-colors select-none disabled:cursor-not-allowed disabled:opacity-60'

const sizes: Record<ButtonSize, string> = {
  md: 'min-h-11 px-5 text-sm', // 44 px : confortable au doigt
  lg: 'min-h-12 px-6 text-base',
}

// « enabled: » évite l'effet de survol sur un bouton désactivé ; les liens n'ont pas cet état.
const variants: Record<ButtonVariant, { button: string; link: string }> = {
  primary: {
    button:
      'bg-indigo-600 text-white shadow-sm enabled:hover:bg-indigo-700 enabled:active:bg-indigo-800',
    link: 'bg-indigo-600 text-white shadow-sm hover:bg-indigo-700 active:bg-indigo-800',
  },
  secondary: {
    button:
      'border border-zinc-300 bg-white text-zinc-900 enabled:hover:bg-zinc-50 enabled:active:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:enabled:hover:bg-zinc-800 dark:enabled:active:bg-zinc-700',
    link: 'border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50 active:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800 dark:active:bg-zinc-700',
  },
  danger: {
    button: 'bg-red-600 text-white shadow-sm enabled:hover:bg-red-700 enabled:active:bg-red-800',
    link: 'bg-red-600 text-white shadow-sm hover:bg-red-700 active:bg-red-800',
  },
  ghost: {
    button:
      'text-zinc-700 enabled:hover:bg-zinc-100 enabled:active:bg-zinc-200 dark:text-zinc-300 dark:enabled:hover:bg-zinc-800',
    link: 'text-zinc-700 hover:bg-zinc-100 active:bg-zinc-200 dark:text-zinc-300 dark:hover:bg-zinc-800',
  },
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className = '',
  type = 'button',
  disabled,
  children,
  ...props
}: ComponentProps<'button'> & { variant?: ButtonVariant; size?: ButtonSize; loading?: boolean }) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`${base} ${sizes[size]} ${variants[variant].button} ${className}`}
      {...props}
    >
      {loading && <SpinnerIcon />}
      {children}
    </button>
  )
}

export function ButtonLink({
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: ComponentProps<typeof Link> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return (
    <Link className={`${base} ${sizes[size]} ${variants[variant].link} ${className}`} {...props} />
  )
}

function SpinnerIcon() {
  return (
    <span
      aria-hidden="true"
      className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  )
}

// --- Mise en page --------------------------------------------------------------------------

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 ${className}`}
    >
      {children}
    </section>
  )
}

/** En-tête de page : repère (étape), titre, description, puis l'action principale. */
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
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="text-h1 mt-2">{title}</h1>
        {description && <p className="text-lead mt-3">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </header>
  )
}

// --- Messages et indicateurs ---------------------------------------------------------------

type Tone = 'info' | 'success' | 'warning' | 'danger'

const toneStyles: Record<Tone, string> = {
  info: 'border-sky-200 bg-sky-50 text-sky-950 dark:border-sky-900 dark:bg-sky-950/60 dark:text-sky-100',
  success:
    'border-emerald-200 bg-emerald-50 text-emerald-950 dark:border-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-100',
  warning:
    'border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-900 dark:bg-amber-950/60 dark:text-amber-100',
  danger:
    'border-red-200 bg-red-50 text-red-950 dark:border-red-900 dark:bg-red-950/60 dark:text-red-100',
}

/** Message d'état. Les messages « danger » sont annoncés tout de suite aux lecteurs d'écran. */
export function Alert({
  tone = 'info',
  title,
  children,
}: {
  tone?: Tone
  title?: string
  children?: ReactNode
}) {
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={`rounded-xl border px-4 py-3 text-sm leading-relaxed ${toneStyles[tone]}`}
    >
      {title && <p className="font-semibold">{title}</p>}
      {children && <div className={title ? 'mt-1' : ''}>{children}</div>}
    </div>
  )
}

const badgeTones: Record<Tone | 'neutral', string> = {
  neutral: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
  info: 'bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-100',
  success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-100',
  warning: 'bg-amber-100 text-amber-900 dark:bg-amber-900/60 dark:text-amber-100',
  danger: 'bg-red-100 text-red-800 dark:bg-red-900/60 dark:text-red-100',
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: Tone | 'neutral'
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap ${badgeTones[tone]}`}
    >
      {children}
    </span>
  )
}

export function ProgressBar({ value, label }: { value: number; label: string }) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      className="h-3 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
    >
      <div
        className="h-full rounded-full bg-indigo-600 transition-[width] duration-500"
        style={{ width: `${value}%` }}
      />
    </div>
  )
}

export function Spinner({ label }: { label: string }) {
  return (
    <span className="text-small inline-flex items-center gap-3">
      <SpinnerIcon />
      {label}
    </span>
  )
}

/** Chiffre clé, à placer dans une liste de définitions (<dl>). */
export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-xl bg-zinc-50 px-4 py-3 dark:bg-zinc-950">
      <dt className="text-xs font-medium text-zinc-600 dark:text-zinc-400">{label}</dt>
      <dd className="mt-1 text-xl font-semibold tabular-nums">{value}</dd>
    </div>
  )
}

// --- Formulaires ---------------------------------------------------------------------------

export const inputClass =
  'block min-h-11 w-full rounded-lg border border-zinc-300 bg-white px-3 text-base text-zinc-900 placeholder:text-zinc-500 sm:text-sm dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 aria-[invalid=true]:border-red-600 dark:aria-[invalid=true]:border-red-400'

export interface FieldAria {
  id: string
  'aria-describedby'?: string
  'aria-invalid'?: true
}

/** Champ de formulaire : libellé, aide et erreur affichée juste sous le champ concerné. */
export function Field({
  id,
  label,
  help,
  error,
  children,
}: {
  id: string
  label: string
  help?: string
  error?: string
  children: (aria: FieldAria) => ReactNode
}) {
  const describedBy = [help && `${id}-aide`, error && `${id}-erreur`].filter(Boolean).join(' ')
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      {help && (
        <p id={`${id}-aide`} className="text-small mt-1">
          {help}
        </p>
      )}
      <div className="mt-2">
        {children({
          id,
          'aria-describedby': describedBy || undefined,
          'aria-invalid': error ? true : undefined,
        })}
      </div>
      {error && (
        <p id={`${id}-erreur`} className="mt-2 text-sm font-medium text-red-700 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  )
}
