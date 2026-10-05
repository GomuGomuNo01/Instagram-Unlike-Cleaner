import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

import { Button, inputClass } from './ui'

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

/** Fenêtre de confirmation modale, utilisable au clavier (Échap pour annuler). Le bouton
 * « Annuler » reçoit le focus : une validation par erreur demande un geste volontaire.
 * Le contenu disparaît à la fermeture, ce qui remet la saisie à zéro. */
export function ConfirmDialog({ open, ...props }: ConfirmDialogProps) {
  return open ? <DialogContent {...props} /> : null
}

function DialogContent({
  title,
  children,
  confirmLabel,
  danger = false,
  busy = false,
  requireText,
  onConfirm,
  onCancel,
}: Omit<ConfirmDialogProps, 'open'>) {
  const titleId = useId()
  const inputId = useId()
  const cancelRef = useRef<HTMLButtonElement>(null)
  const [typed, setTyped] = useState('')

  useEffect(() => {
    cancelRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  const confirmed = !requireText || typed.trim().toUpperCase() === requireText
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-zinc-950/60 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-zinc-900"
      >
        <h2 id={titleId} className="text-h3">
          {title}
        </h2>
        <div className="text-body mt-3">{children}</div>
        {requireText && (
          <div className="mt-6">
            <label htmlFor={inputId} className="block text-sm font-medium">
              Pour confirmer, tape « {requireText} »
            </label>
            <input
              id={inputId}
              value={typed}
              onChange={(event) => setTyped(event.target.value)}
              autoComplete="off"
              className={`${inputClass} mt-2`}
            />
          </div>
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
