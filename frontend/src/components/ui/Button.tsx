import type { ComponentProps, ReactNode } from 'react'
import type { Link } from 'react-router'

import { magnetic as attachMagnetic } from '../../lib/motion'
import { CheckIcon } from '../icons'
import { AppLink } from './Link'

// États : normal, survol, appui, focus (contour global), désactivé, chargement et succès.
// Les styles de chaque état sont dans styles/components.css (.btn).

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'inverse'
type Size = 'md' | 'lg' | 'icon'

interface Look {
  variant?: Variant
  size?: Size
  /** Icône avant le libellé. */
  icon?: ReactNode
  /** Icône après le libellé, qui glisse légèrement au survol (« aller vers »). */
  trailingIcon?: ReactNode
}

function buttonClass(variant: Variant, size: Size, extra: string): string {
  return ['btn', `btn-${variant}`, size === 'lg' && 'btn-lg', size === 'icon' && 'btn-icon', extra]
    .filter(Boolean)
    .join(' ')
}

function Trailing({ children }: { children: ReactNode }) {
  return (
    <span data-icon="trailing" className="inline-flex">
      {children}
    </span>
  )
}

export function Spinner({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      data-icon="status"
      className={`inline-block shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  )
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  trailingIcon,
  loading = false,
  success = false,
  className = '',
  type = 'button',
  disabled,
  children,
  ...props
}: ComponentProps<'button'> &
  Look & {
    /** Action en cours : bouton inactif, indicateur de chargement, libellé conservé. */
    loading?: boolean
    /** Action réussie : coche et fond de succès, le temps d'un message. */
    success?: boolean
  }) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      data-state={success ? 'success' : undefined}
      className={buttonClass(variant, size, className)}
      {...props}
    >
      {loading ? <Spinner /> : success ? <CheckIcon data-icon="status" /> : icon}
      {children}
      {trailingIcon && <Trailing>{trailingIcon}</Trailing>}
    </button>
  )
}

/** Lien présenté comme un bouton. `magnetic` : attraction légère vers le curseur, réservée
 * aux appels à l'action principaux de la page d'accueil. */
export function ButtonLink({
  variant = 'primary',
  size = 'md',
  icon,
  trailingIcon,
  magnetic = false,
  className = '',
  children,
  ...props
}: ComponentProps<typeof Link> & Look & { magnetic?: boolean; children: ReactNode }) {
  return (
    <AppLink
      ref={magnetic ? attachMagnetic : undefined}
      className={buttonClass(variant, size, `${magnetic ? 'magnetic' : ''} ${className}`)}
      {...props}
    >
      {icon}
      {children}
      {trailingIcon && <Trailing>{trailingIcon}</Trailing>}
    </AppLink>
  )
}
