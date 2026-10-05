import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

import { motionDuration } from '../../lib/motion'
import { AlertIcon, CheckCircleIcon, CloseIcon, InfoIcon, XCircleIcon } from '../icons'
import { ToastContext, type ToastMessage, type ToastTone } from './toast-context'

const DISPLAY_MS = 5000 // durée d'affichage, suspendue au survol ou au focus
const MAX_VISIBLE = 3

interface ToastEntry extends ToastMessage {
  id: number
  open: boolean
}

const icons = {
  success: { Icon: CheckCircleIcon, color: 'text-success-strong' },
  info: { Icon: InfoIcon, color: 'text-info-strong' },
  warning: { Icon: AlertIcon, color: 'text-warning-strong' },
  danger: { Icon: XCircleIcon, color: 'text-danger-strong' },
} as const satisfies Record<ToastTone, unknown>

/** Notifications brèves en bas de l'écran, annoncées aux lecteurs d'écran. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([])
  const counter = useRef(0)

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.map((toast) => (toast.id === id ? { ...toast, open: false } : toast)))
    window.setTimeout(
      () => setToasts((list) => list.filter((toast) => toast.id !== id)),
      motionDuration('micro'),
    )
  }, [])

  const notify = useCallback((message: ToastMessage) => {
    counter.current += 1
    const entry = { ...message, id: counter.current, open: true }
    setToasts((list) => [...list.filter((toast) => toast.open).slice(1 - MAX_VISIBLE), entry])
  }, [])

  return (
    <ToastContext value={notify}>
      {children}
      <section aria-label="Notifications">
        <ol aria-live="polite" className="toast-region">
          {toasts.map((toast) => (
            <Toast key={toast.id} toast={toast} onDismiss={dismiss} />
          ))}
        </ol>
      </section>
    </ToastContext>
  )
}

function Toast({ toast, onDismiss }: { toast: ToastEntry; onDismiss: (id: number) => void }) {
  const [paused, setPaused] = useState(false)
  const { Icon, color } = icons[toast.tone ?? 'success']

  useEffect(() => {
    if (paused || !toast.open) return
    const timer = window.setTimeout(() => onDismiss(toast.id), DISPLAY_MS)
    return () => window.clearTimeout(timer)
  }, [paused, toast.open, toast.id, onDismiss])

  return (
    <li
      className="toast"
      data-state={toast.open ? 'open' : 'closed'}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <span className="flex h-5 items-center">
        <Icon className={`h-5 w-5 ${color}`} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-small font-semibold text-fg">{toast.title}</p>
        {toast.description && <p className="mt-1 text-small text-fg-muted">{toast.description}</p>}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Fermer la notification"
        className="btn btn-ghost btn-icon -my-3 -mr-3"
      >
        <CloseIcon className="h-4 w-4" />
      </button>
    </li>
  )
}
