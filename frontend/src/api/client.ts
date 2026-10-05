import createClient, { type Middleware } from 'openapi-fetch'

import type { paths } from './schema'
import { getToken, TOKEN_HEADER } from './token'

/** Erreur renvoyée par l'API, avec un message lisible par l'utilisateur. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const withToken: Middleware = {
  onRequest({ request }) {
    const token = getToken()
    if (token) request.headers.set(TOKEN_HEADER, token)
    return request
  },
}

/** Client typé : chemins, paramètres et réponses viennent du schéma OpenAPI. */
export const api = createClient<paths>({ baseUrl: '' })
api.use(withToken)

interface FetchResult<T> {
  data?: T
  error?: unknown
  response: Response
}

/** Renvoie les données d'une réponse réussie, ou lève une ApiError avec le message de l'API. */
export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>
  try {
    result = await request
  } catch {
    throw new ApiError(0, "L'API ne répond pas : vérifie que `iuc serve` est toujours lancé.")
  }
  const { data, error, response } = result
  if (error !== undefined || !response.ok) {
    throw new ApiError(response.status, describeError(response.status, error))
  }
  return data as T
}

export function describeError(status: number, error: unknown): string {
  if (status === 401) {
    return 'Jeton refusé : recharge la page ouverte par `iuc serve` (le jeton change à chaque démarrage).'
  }
  const detail = (error as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // Erreurs de validation de FastAPI : un message par champ.
    return detail
      .map((issue) =>
        String((issue as { msg?: unknown }).msg ?? issue).replace(/^Value error, /, ''),
      )
      .join(' ; ')
  }
  return `Erreur inattendue de l'API (code ${status}).`
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
