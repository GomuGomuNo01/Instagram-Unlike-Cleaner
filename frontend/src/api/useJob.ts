import { useCallback, useEffect, useState } from 'react'

import { api, errorMessage, unwrap } from './client'
import type { Job } from './types'

/** Charge un nettoyage ; `reload` le relit (après une action ou un événement). */
export function useJob(jobId: number) {
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchJob = useCallback(
    () => unwrap(api.GET('/api/jobs/{job_id}', { params: { path: { job_id: jobId } } })),
    [jobId],
  )

  useEffect(() => {
    let active = true // ignore une réponse arrivée après la fermeture de l'écran
    fetchJob().then(
      (loaded) => {
        if (!active) return
        setJob(loaded)
        setError(null)
      },
      (failure: unknown) => {
        if (active) setError(errorMessage(failure))
      },
    )
    return () => {
      active = false
    }
  }, [fetchJob])

  const reload = useCallback(async () => {
    try {
      const loaded = await fetchJob()
      setJob(loaded)
      setError(null)
      return loaded
    } catch (failure) {
      setError(errorMessage(failure))
      return null
    }
  }, [fetchJob])

  return { job, setJob, error, reload }
}

/** Numéro de nettoyage lu dans l'adresse (« /nettoyages/12/suivi »). */
export function parseJobId(value: string | undefined): number | null {
  const id = Number(value)
  return Number.isInteger(id) && id > 0 ? id : null
}
