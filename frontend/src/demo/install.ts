// Branche l'interface sur la fausse API de démonstration : les appels à /api et le flux
// d'événements sont servis dans le navigateur, sans aucune requête vers un serveur.
// Chargé uniquement par la version « démo » (npm run build:demo), jamais par IUC installé.

import type { JobEventType } from '../api/events'
import { FakeApi } from './fakeApi'

const API_PREFIX = '/api/'

export function installDemo(api = new FakeApi()): FakeApi {
  // Le jeton n'a pas de sens ici : une valeur fixe évite l'écran de saisie du jeton.
  const meta = document.createElement('meta')
  meta.name = 'iuc-token'
  meta.content = 'demo'
  document.head.append(meta)

  const realFetch = globalThis.fetch.bind(globalThis)
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init)
    const url = new URL(request.url)
    return url.origin === globalThis.location.origin && url.pathname.startsWith(API_PREFIX)
      ? api.handle(request)
      : realFetch(input, init)
  }

  globalThis.EventSource = class DemoEventSource extends EventTarget {
    static readonly CONNECTING = 0
    static readonly OPEN = 1
    static readonly CLOSED = 2
    readonly url: string
    readonly withCredentials = false
    readyState = 0
    onopen = null
    onmessage = null
    onerror = null
    private unsubscribe: () => void = () => {}

    constructor(url: string | URL) {
      super()
      this.url = String(url)
      const jobId = Number(/\/api\/jobs\/(\d+)\/events/.exec(this.url)?.[1])
      // Comme une vraie connexion : les événements arrivent après la création de l'objet.
      setTimeout(() => {
        if (this.readyState === 2) return
        this.readyState = 1
        this.unsubscribe = api.subscribe(jobId, (type: JobEventType, data, id) => {
          if (this.readyState === 2) return
          this.dispatchEvent(
            new MessageEvent(type, {
              data: JSON.stringify(data),
              lastEventId: id === null ? '' : String(id),
            }),
          )
        })
      }, 0)
    }

    close(): void {
      this.readyState = 2
      this.unsubscribe()
    }
  } as unknown as typeof EventSource

  return api
}
