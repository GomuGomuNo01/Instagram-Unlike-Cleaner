import { createContext, useContext } from 'react'

export type ToastTone = 'success' | 'info' | 'warning' | 'danger'

export interface ToastMessage {
  tone?: ToastTone
  title: string
  description?: string
}

/** Affiche une notification brève (confirmation d'une action, par exemple). Sans
 * ToastProvider, l'appel est sans effet. */
export const ToastContext = createContext<(toast: ToastMessage) => void>(() => {})

export const useToast = () => useContext(ToastContext)
