import { useId, useState, type KeyboardEvent, type ReactNode } from 'react'

import { ChevronDownIcon } from '../icons'

/** Bulle d'aide d'un bouton à icône, au survol (après un court délai) ou au focus clavier.
 * Le bouton garde son propre libellé accessible : la bulle n'en est qu'un écho visuel. */
export function Tooltip({
  label,
  align = 'center',
  children,
}: {
  label: string
  align?: 'center' | 'end'
  children: ReactNode
}) {
  return (
    <span className="tooltip-anchor">
      {children}
      <span className="tooltip" data-align={align === 'end' ? 'end' : undefined} aria-hidden="true">
        {label}
      </span>
    </span>
  )
}

/** Accordéon natif (details/summary) : clavier et lecteurs d'écran gérés par le navigateur,
 * ouverture animée là où c'est possible. */
export function Disclosure({
  summary,
  children,
  className = '',
}: {
  summary: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <details className={`disclosure ${className}`}>
      <summary className="flex min-h-14 items-center justify-between gap-4 py-4 text-body font-medium text-fg">
        {summary}
        <ChevronDownIcon data-icon="chevron" className="h-5 w-5 shrink-0 text-fg-subtle" />
      </summary>
      <div className="pb-6">{children}</div>
    </details>
  )
}

export interface TabItem {
  id: string
  label: string
  count?: number
  content: ReactNode
}

/** Onglets accessibles : flèches gauche et droite, Début et Fin pour passer de l'un à l'autre. */
export function Tabs({ label, items }: { label: string; items: TabItem[] }) {
  const baseId = useId()
  const [selected, setSelected] = useState(items[0]?.id)

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = items.length - 1
    const next =
      event.key === 'ArrowRight'
        ? (index + 1) % items.length
        : event.key === 'ArrowLeft'
          ? (index - 1 + items.length) % items.length
          : event.key === 'Home'
            ? 0
            : event.key === 'End'
              ? last
              : null
    if (next === null) return
    event.preventDefault()
    const item = items[next]
    if (!item) return
    setSelected(item.id)
    document.getElementById(`${baseId}-${item.id}-onglet`)?.focus()
  }

  return (
    <div>
      <div role="tablist" aria-label={label} className="tabs-list">
        {items.map((item, index) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`${baseId}-${item.id}-onglet`}
            aria-selected={item.id === selected}
            aria-controls={`${baseId}-${item.id}-panneau`}
            tabIndex={item.id === selected ? 0 : -1}
            onClick={() => setSelected(item.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className="tab"
          >
            {item.label}
            {item.count !== undefined && (
              <span className="rounded-full bg-fill px-2 text-caption tabular-nums">
                {item.count}
              </span>
            )}
          </button>
        ))}
      </div>
      {items.map((item) =>
        item.id === selected ? (
          <div
            key={item.id}
            role="tabpanel"
            id={`${baseId}-${item.id}-panneau`}
            aria-labelledby={`${baseId}-${item.id}-onglet`}
            tabIndex={0}
            className="animate-fade-in pt-6"
          >
            {item.content}
          </div>
        ) : null,
      )}
    </div>
  )
}
