import { useCallback, useEffect, useState } from 'react'

import { getToken } from './token'
import type { Job } from './types'

export type JobEventType = 'snapshot' | 'status' | 'progress' | 'batch' | 'end'

export interface EndData {
  ok: boolean
  message: string
  result: {
    reason?: string
    done?: number
    failed?: number
    skipped?: number
    remaining?: number
    detail?: string | null
    targeted?: number
  } | null
  job: Job
}

export type JobEvent =
  | { type: 'snapshot' | 'status'; id: number | null; at: number; data: { job: Job } }
  | { type: 'progress'; id: number | null; at: number; data: { scanned: number } }
  | { type: 'batch'; id: number | null; at: number; data: { removed: number; total: number } }
  | { type: 'end'; id: number | null; at: number; data: EndData }

const EVENT_TYPES: JobEventType[] = ['snapshot', 'status', 'progress', 'batch', 'end']

/** Suit la progression d'un nettoyage (Server-Sent Events). Le flux s'arrête à l'événement
 * « end » ; `restart` le rouvre, par exemple après une reprise. */
export function useJobEvents(jobId: number, enabled = true) {
  const [events, setEvents] = useState<JobEvent[]>([])
  const [ended, setEnded] = useState(false)
  const [round, setRound] = useState(0)

  useEffect(() => {
    if (!enabled) return
    const token = encodeURIComponent(getToken() ?? '')
    const source = new EventSource(`/api/jobs/${jobId}/events?token=${token}`)
    const seen = new Set<string>()
    for (const type of EVENT_TYPES) {
      source.addEventListener(type, (message: MessageEvent<string>) => {
        // Après une reconnexion automatique, le serveur rejoue la tâche en cours.
        if (message.lastEventId) {
          if (seen.has(message.lastEventId)) return
          seen.add(message.lastEventId)
        }
        const event = {
          type,
          id: message.lastEventId ? Number(message.lastEventId) : null,
          at: Date.now(),
          data: JSON.parse(message.data) as unknown,
        } as JobEvent
        setEvents((previous) => [...previous, event])
        if (type === 'end') {
          setEnded(true)
          source.close()
        }
      })
    }
    return () => source.close()
  }, [jobId, enabled, round])

  const restart = useCallback(() => {
    setEvents([])
    setEnded(false)
    setRound((value) => value + 1)
  }, [])
  return { events, ended, restart }
}
