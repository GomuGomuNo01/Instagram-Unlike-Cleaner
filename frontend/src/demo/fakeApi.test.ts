import { describe, expect, it, vi } from 'vitest'

import type { JobEventType } from '../api/events'
import type { ItemsPage, Job, JobReport, SessionStatus, UpdateInfo } from '../api/types'
import { FakeApi } from './fakeApi'

const FAST = { latency: 0, login: 0, scanStep: 500, scanMs: 1, batchMs: 1 }

async function call<T>(api: FakeApi, method: string, path: string, body?: unknown) {
  const response = await api.handle(
    new Request(`http://demo.test${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  )
  const text = await response.text()
  return {
    status: response.status,
    body: (text.startsWith('{') || text.startsWith('[') ? JSON.parse(text) : text) as T,
  }
}

async function loggedIn(): Promise<FakeApi> {
  const api = new FakeApi(FAST)
  await call(api, 'POST', '/api/session/start')
  const status = await call<SessionStatus>(api, 'GET', '/api/session/status')
  expect(status.body.logged_in).toBe(true)
  return api
}

async function waitForStatus(api: FakeApi, id: number, status: Job['status']): Promise<Job> {
  let job: Job | undefined
  await vi.waitFor(async () => {
    job = (await call<Job>(api, 'GET', `/api/jobs/${id}`)).body
    expect(job.status).toBe(status)
  })
  return job!
}

describe('démo en ligne : fausse API', () => {
  it('commence avec trois nettoyages fictifs : terminé, en pause et prêt', async () => {
    const jobs = await call<Job[]>(new FakeApi(FAST), 'GET', '/api/jobs')

    expect(jobs.body.map((job) => job.status)).toEqual(['completed', 'paused', 'ready'])
    expect(
      jobs.body.every(
        (job) => Object.keys(job.filters).sort().join() === 'end_date,sort,start_date',
      ),
    ).toBe(true)
  })

  it('simule la connexion faite par la personne elle-même', async () => {
    const api = new FakeApi({ ...FAST, login: 60_000 })
    expect((await call<SessionStatus>(api, 'GET', '/api/session/status')).body.browser_open).toBe(
      false,
    )

    const opened = await call<SessionStatus>(api, 'POST', '/api/session/start')

    expect(opened.status).toBe(200)
    expect(opened.body).toMatchObject({ browser_open: true, logged_in: false })
  })

  it('refuse un aperçu sans connexion, ou avec un critère hors du filtre d’Instagram', async () => {
    expect((await call(new FakeApi(FAST), 'POST', '/api/jobs', {})).status).toBe(409)
    const api = await loggedIn()

    expect((await call(api, 'POST', '/api/jobs', { content: 'reels' })).status).toBe(422)
    const inverted = await call<{ detail: { msg: string }[] }>(api, 'POST', '/api/jobs', {
      start_date: '2022-01-01',
      end_date: '2021-01-01',
    })
    expect(inverted.status).toBe(422)
    expect(inverted.body.detail[0]?.msg).toContain('précéder')
  })

  it('applique le filtre d’Instagram : période du like, puis tri', async () => {
    const api = await loggedIn()

    const created = await call<Job>(api, 'POST', '/api/jobs', {
      sort: 'oldest_first',
      start_date: '2022-01-01',
      end_date: '2022-03-31',
      max_scanned: null,
    })
    expect(created.status).toBe(202)
    const job = await waitForStatus(api, created.body.id, 'ready')
    const page = await call<ItemsPage>(api, 'GET', `/api/jobs/${job.id}/items?limit=500`)

    expect(page.body.total).toBeGreaterThan(20)
    expect(page.body.items.every((item) => item.status === 'pending')).toBe(true)
    expect(page.body.items.map((item) => item.rank)).toEqual(
      page.body.items.map((_, index) => index + 1),
    )
  })

  it('décoche, retire par lots, met en pause à la limite, reprend et produit le rapport', async () => {
    const api = await loggedIn()
    const created = await call<Job>(api, 'POST', '/api/jobs', {
      start_date: '2024-01-01',
      end_date: '2024-02-29',
    })
    const ready = await waitForStatus(api, created.body.id, 'ready')
    const page = await call<ItemsPage>(api, 'GET', `/api/jobs/${ready.id}/items`)
    const kept = page.body.items[0]!.id

    const patched = await call<{ changed: number; job: Job }>(
      api,
      'PATCH',
      `/api/jobs/${ready.id}/items`,
      {
        item_ids: [kept],
        excluded: true,
      },
    )
    expect(patched.body.changed).toBe(1)

    await call(api, 'POST', `/api/jobs/${ready.id}/start`, { limit: 5 })
    const paused = await waitForStatus(api, ready.id, 'paused')
    expect(
      (paused.counts.done ?? 0) + (paused.counts.failed ?? 0) + (paused.counts.skipped ?? 0),
    ).toBe(5)

    await call(api, 'POST', `/api/jobs/${ready.id}/resume`, {})
    const completed = await waitForStatus(api, ready.id, 'completed')
    expect(completed.to_process).toBe(0)
    expect(completed.counts.excluded).toBe(1)

    const report = await call<JobReport>(api, 'GET', `/api/jobs/${ready.id}/report`)
    expect(report.body.executions).toBe(2)
    const csv = await api.handle(
      new Request(`http://demo.test/api/jobs/${ready.id}/report?format=csv`),
    )
    const bytes = new Uint8Array(await csv.arrayBuffer())
    expect([...bytes.slice(0, 3)]).toEqual([0xef, 0xbb, 0xbf]) // BOM : Excel lit l'UTF-8
    expect(new TextDecoder().decode(bytes).split('\r\n')[0]).toBe(
      'rang;auteur;type;partagée le (selon Instagram);statut;traité le;heure;détail;identifiant',
    )

    // Les likes retirés ont disparu de la page des likes : un nouvel aperçu ne les voit plus.
    const again = await call<Job>(api, 'POST', '/api/jobs', {
      start_date: '2024-01-01',
      end_date: '2024-02-29',
    })
    const second = await waitForStatus(api, again.body.id, 'ready')
    expect(second.counts.pending).toBe(
      (completed.counts.excluded ?? 0) +
        (completed.counts.failed ?? 0) +
        (completed.counts.skipped ?? 0),
    )
  })

  it('diffuse les événements comme l’API : snapshot, état, lots, puis fin', async () => {
    const api = await loggedIn()
    const types: JobEventType[] = []

    await call(api, 'POST', '/api/jobs/3/start', { limit: 3 })
    api.subscribe(3, (type) => types.push(type))
    await vi.waitFor(() => expect(types.at(-1)).toBe('end'))

    expect(types[0]).toBe('snapshot')
    expect(types).toContain('status')
    expect(types).toContain('batch')
  })

  it('ne propose jamais de mise à jour', async () => {
    const api = new FakeApi(FAST)

    const update = await call<UpdateInfo>(api, 'GET', '/api/update')
    const install = await call(api, 'POST', '/api/update/install')

    expect(update.body.available).toBe(false)
    expect(install.status).toBe(409)
  })

  it('« Supprimer mes données locales » repart d’une base vide', async () => {
    const api = new FakeApi(FAST)

    await call(api, 'DELETE', '/api/data')

    expect((await call<Job[]>(api, 'GET', '/api/jobs')).body).toEqual([])
  })
})
