import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

import { usePresence, useScrollLock } from '../../lib/motion'
import { Button } from './Button'
import { Field } from './Form'

interface ConfirmDialogProps {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel: string
  danger?: boolean
  busy?: boolean
  /** Mot à recopier avant de pouvoir valider, pour les actions irréversibles. */
  requireText?: string
  onConfirm: () => void
  onCancel: () => void
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** Garde le focus clavier à l'intérieur de la fenêtre (Tab et Maj+Tab bouclent). */
function trapFocus(event: KeyboardEvent, container: HTMLElement | null) {
  const items = container ? [...container.querySelectorAll<HTMLElement>(FOCUSABLE)] : []
  const first = items[0]
  const last = items.at(-1)
  if (!first || !last) return
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

/** Fenêtre de confirmation modale. Clavier : Échap annule, Tab reste dans la fenêtre. Le
 * bouton « Annuler » reçoit le focus : une validation par erreur demande un geste volontaire.
 * À la fermeture, la fenêtre s'efface puis disparaît, ce qui remet la saisie à zéro et rend
 * le focus à l'élément qui l'avait ouverte. */
export function ConfirmDialog({ open, ...props }: ConfirmDialogProps) {
  const { mounted, state } = usePresence(open)
  return mounted ? <DialogContent state={state} {...props} /> : null
}

function DialogContent({
  state,
  title,
  children,
  confirmLabel,
  danger = false,
  busy = false,
  requireText,
  onConfirm,
  onCancel,
}: Omit<ConfirmDialogProps, 'open'> & { state: 'open' | 'closed' }) {
  const titleId = useId()
  const bodyId = useId()
  const inputId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const [typed, setTyped] = useState('')
  useScrollLock(true)

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    cancelRef.current?.focus()
    return () => opener?.focus()
  }, [])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onCancel()
      if (event.key === 'Tab') trapFocus(event, panelRef.current)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onCancel])

  const confirmed = !requireText || typed.trim().toUpperCase() === requireText
  return (
    <div
      className="dialog-overlay"
      data-state={state}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onCancel()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        className="dialog-panel"
      >
        <h2 id={titleId} className="text-h3">
          {title}
        </h2>
        <div id={bodyId} className="mt-3 text-body text-fg-muted">
          {children}
        </div>
        {requireText && (
          <Field
            id={inputId}
            label={`Pour confirmer, tape « ${requireText} »`}
            success={confirmed ? 'Confirmation saisie.' : undefined}
            className="mt-6"
          >
            {(aria) => (
              <input
                {...aria}
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                autoComplete="off"
                className="input"
              />
            )}
          </Field>
        )}
        <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button ref={cancelRef} variant="secondary" onClick={onCancel} disabled={busy}>
            Annuler
          </Button>
          <Button
            variant={danger ? 'danger' : 'primary'}
            onClick={onConfirm}
            disabled={!confirmed}
            loading={busy}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
