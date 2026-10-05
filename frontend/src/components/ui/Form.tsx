import { useId, type ComponentProps, type ReactNode } from 'react'

import { CheckCircleIcon, XCircleIcon } from '../icons'

// Formulaires : libellé explicite, aide, erreur et succès affichés juste sous le champ.
// Les styles des états (focus, erreur, succès, désactivé) sont dans components.css.

export const inputClass = 'input'

export interface FieldAria {
  id: string
  'aria-describedby'?: string
  'aria-invalid'?: true
  'data-state'?: 'success'
}

export function FieldMessage({
  id,
  tone,
  children,
}: {
  id: string
  tone: 'error' | 'success'
  children: ReactNode
}) {
  const Icon = tone === 'error' ? XCircleIcon : CheckCircleIcon
  return (
    <p
      id={id}
      className={`mt-2 flex animate-fade-up items-start gap-2 text-small font-medium ${
        tone === 'error' ? 'text-danger-strong' : 'text-success-strong'
      }`}
    >
      <span className="flex h-5 shrink-0 items-center">
        <Icon className="h-4 w-4" />
      </span>
      {children}
    </p>
  )
}

/** Champ de formulaire : `children` reçoit les attributs d'accessibilité à poser sur le
 * contrôle (identifiant, description, état invalide). */
export function Field({
  id,
  label,
  help,
  error,
  success,
  className = '',
  children,
}: {
  id: string
  label: string
  help?: string
  error?: string
  success?: string
  className?: string
  children: (aria: FieldAria) => ReactNode
}) {
  const showSuccess = Boolean(success && !error)
  const describedBy = [help && `${id}-aide`, error && `${id}-erreur`, showSuccess && `${id}-succes`]
    .filter(Boolean)
    .join(' ')
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-small font-medium text-fg">
        {label}
      </label>
      {help && (
        <p id={`${id}-aide`} className="mt-1 text-small text-fg-muted">
          {help}
        </p>
      )}
      <div className="mt-2">
        {children({
          id,
          'aria-describedby': describedBy || undefined,
          'aria-invalid': error ? true : undefined,
          'data-state': showSuccess ? 'success' : undefined,
        })}
      </div>
      {error && (
        <FieldMessage id={`${id}-erreur`} tone="error">
          {error}
        </FieldMessage>
      )}
      {showSuccess && (
        <FieldMessage id={`${id}-succes`} tone="success">
          {success}
        </FieldMessage>
      )}
    </div>
  )
}

/** Case à cocher native, redessinée et animée. */
export function Checkbox({ className = '', ...props }: Omit<ComponentProps<'input'>, 'type'>) {
  return <input type="checkbox" className={`checkbox ${className}`} {...props} />
}

/** Interrupteur : toute la ligne est cliquable (cible tactile confortable). */
export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
  description?: string
  disabled?: boolean
}) {
  const id = useId()
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-labelledby={`${id}-libelle`}
      aria-describedby={description ? `${id}-description` : undefined}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="flex min-h-11 w-full items-center justify-between gap-4 rounded-lg text-left disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span>
        <span id={`${id}-libelle`} className="block text-small font-medium text-fg">
          {label}
        </span>
        {description && (
          <span id={`${id}-description`} className="mt-1 block text-small text-fg-muted">
            {description}
          </span>
        )}
      </span>
      <span className="switch-track" aria-hidden="true" />
    </button>
  )
}

export interface Choice<T extends string> {
  value: T
  label: string
}

/** Choix exclusif parmi quelques options, toutes visibles (boutons radio). */
export function ChoiceGroup<T extends string>({
  legend,
  name,
  options,
  value,
  onChange,
}: {
  legend: string
  name: string
  options: readonly Choice<T>[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <fieldset>
      <legend className="text-small font-medium text-fg">{legend}</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((option) => (
          <label key={option.value} className="choice">
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
