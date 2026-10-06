// Fausse API d'IUC pour la démo en ligne : mêmes routes, mêmes réponses et même flux
// d'événements que l'API locale, mais sur des likes fictifs gardés en mémoire. Aucune
// requête ne sort du navigateur et rien n'est enregistré : recharger la page repart de zéro.

import type { EndData, JobEventType } from '../api/events'
import type {
  Item,
  ItemStatus,
  Job,
  JobReport,
  JobStatus,
  MediaKind,
  ReportLine,
  SessionStatus,
} from '../api/types'
import { jobStatusLabels } from '../i18n/fr'
import { localToday } from '../lib/filters'

type Filters = Job['filters']

const ACCOUNT = '1000000001' // identifiant fictif
const FIRST_DAY = '2019-01-01' // premier like de l'historique fictif
const LIKES_PER_DAY = 0.5
const BATCH_SIZE = 20 // comme BATCH_SIZE par défaut
// Simulation accélérée mais lisible (le vrai nettoyage retire environ 25 likes par minute).
const TIMING = { latency: 120, login: 2500, scanStep: 18, scanMs: 160, batchMs: 2000 }

// Comptes fictifs, du plus aimé au moins aimé (mêmes noms que scripts/demo.py).
const AUTHORS = [
  'compte_humour',
  'page_memes',
  'club_sport',
  'cuisine_facile',
  'voyage_photo',
  'musique_live',
  'atelier_design',
  'cine_club',
  'jardin_urbain',
  'velo_passion',
  'recettes_maison',
  'galerie_art',
  'astuces_tech',
  'rando_alpes',
  'chats_droles',
  'ami_proche',
]
const KINDS: { kind: MediaKind; text: string; report: string }[] = [
  { kind: 'video', text: 'Vidéo', report: 'vidéo' },
  { kind: 'photo', text: 'Photo', report: 'photo' },
  { kind: 'carousel', text: 'Carrousel', report: 'carrousel' },
]
const MONTHS =
  'January February March April May June July August September October November December'
const ERRORS: Partial<Record<ItemStatus, string>> = {
  failed: 'réapparu après rechargement : Instagram n’a pas retiré ce like',
  skipped: 'introuvable dans la grille',
}
const STOP_MESSAGES = {
  completed: 'Nettoyage terminé : tous les likes validés ont été traités.',
  run_limit:
    'Nombre de likes demandé pour cette exécution atteint. Relance la même commande pour continuer.',
  user_pause: 'Nettoyage mis en pause à ta demande. Relance la même commande pour continuer.',
  user_stop: 'Nettoyage arrêté à ta demande : les likes restants ne seront pas retirés.',
} as const
type StopReason = keyof typeof STOP_MESSAGES

interface DemoLike {
  key: string
  likedOn: string // AAAA-MM-JJ, date du like (celle que filtre Instagram)
  sharedOn: string // date de publication, la seule affichée dans la grille
  author: string
  kind: (typeof KINDS)[number]
}

interface DemoJob {
  id: number
  status: JobStatus
  createdAt: string
  startedAt: string | null
  finishedAt: string | null
  filters: Filters
  items: Item[]
  runs: number
  activeSeconds: number
  task: { kind: 'preview' | 'cleanup'; request: 'pause' | 'stop' | null } | null
  history: ServerEvent[]
}

interface ServerEvent {
  id: number
  type: JobEventType
  data: unknown
}

export type EventListener = (type: JobEventType, data: unknown, id: number | null) => void

class HttpError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : 'Requête invalide')
    this.status = status
    this.detail = detail
  }
}

/** Générateur pseudo-aléatoire reproductible (mulberry32) : la démo est la même à chaque visite. */
function seededRandom(seed: number): () => number {
  let state = seed
  return () => {
    state = (state + 0x6d2b79f5) | 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function addDays(day: string, days: number): string {
  const date = new Date(`${day}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

function frenchDay(day: string): string {
  const [year, month, date] = day.split('-')
  return `${date}/${month}/${year}`
}

/** Historique fictif : environ un like tous les deux jours, du 1er janvier 2019 à aujourd'hui. */
function buildHistory(today: string): DemoLike[] {
  const random = seededRandom(2019)
  const weights = AUTHORS.map((_, index) => AUTHORS.length - index)
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0)
  const likes: DemoLike[] = []
  for (let day = FIRST_DAY; day <= today; day = addDays(day, 1)) {
    if (random() >= LIKES_PER_DAY) continue
    let draw = random() * totalWeight
    const authorIndex = weights.findIndex((weight) => (draw -= weight) < 0)
    const n = likes.length
    likes.push({
      key: `${3100000 + n}_${17841400000000000 + n * 7919}_${n}_n`,
      likedOn: day,
      sharedOn: addDays(day, -Math.floor(random() * 400)),
      author: AUTHORS[Math.max(authorIndex, 0)] ?? 'compte_humour',
      kind: KINDS[Math.floor(random() * KINDS.length)] ?? KINDS[0]!,
    })
  }
  return likes
}

function label(like: DemoLike, position: number): string {
  const [year, month, day] = like.sharedOn.split('-').map(Number)
  const shared = `${MONTHS.split(' ')[(month ?? 1) - 1]} ${day}, ${year}`
  return `${like.kind.text}, ${(position % 18) + 1} sur 18, de @${like.author}, partagée le ${shared}`
}

export class FakeApi {
  private readonly today = localToday()
  private readonly history = buildHistory(this.today)
  private readonly random = seededRandom(7)
  private readonly removed = new Set<string>()
  private readonly listeners = new Map<number, Set<EventListener>>()
  private jobs = new Map<number, DemoJob>()
  private nextJobId = 1
  private nextItemId = 1
  private nextEventId = 1
  private busyJob: number | null = null
  private session = { browserOpen: false, loggedIn: false, loginAt: 0 }

  private readonly timing: typeof TIMING

  constructor(timing = TIMING) {
    this.timing = timing
    this.seed()
  }

  // --- Requêtes HTTP ------------------------------------------------------------------------

  async handle(request: Request): Promise<Response> {
    await new Promise((resolve) => setTimeout(resolve, this.timing.latency))
    const url = new URL(request.url)
    const body =
      request.method === 'POST' || request.method === 'PATCH' ? await readJson(request) : undefined
    try {
      const result = this.route(request.method, url, body)
      if (result instanceof Response) return result
      const status = request.method === 'POST' && !url.pathname.endsWith('/stop') ? 202 : 200
      return json(result, url.pathname === '/api/session/start' ? 200 : status)
    } catch (error) {
      if (error instanceof HttpError) return json({ detail: error.detail }, error.status)
      throw error
    }
  }

  private route(method: string, url: URL, body: unknown): unknown {
    const path = url.pathname.replace(/\/$/, '')
    if (path === '/api/session/status' && method === 'GET') return this.sessionStatus()
    if (path === '/api/session/start' && method === 'POST') return this.startSession()
    if (path === '/api/session' && method === 'DELETE') return this.deleteSession()
    if (path === '/api/data' && method === 'DELETE') return this.deleteData()
    if (path === '/api/jobs' && method === 'GET')
      return [...this.jobs.values()].map((job) => this.out(job))
    if (path === '/api/jobs' && method === 'POST') return this.createJob(body)

    const match = /^\/api\/jobs\/(\d+)(?:\/(items|start|resume|pause|stop|report))?$/.exec(path)
    if (!match) throw new HttpError(404, 'Route inconnue.')
    const job = this.job(Number(match[1]))
    const action = match[2]
    if (!action && method === 'GET') return this.out(job)
    if (action === 'items' && method === 'GET') return this.items(job, url.searchParams)
    if (action === 'items' && method === 'PATCH') return this.patchItems(job, body)
    if (action === 'start' && method === 'POST') return this.launch(job, body, ['ready', 'paused'])
    if (action === 'resume' && method === 'POST') return this.launch(job, body, ['paused'])
    if (action === 'pause' && method === 'POST') return this.pause(job)
    if (action === 'stop' && method === 'POST') return this.stop(job)
    if (action === 'report' && method === 'GET') {
      return url.searchParams.get('format') === 'csv'
        ? new Response(reportCsv(this.report(job)), {
            headers: { 'Content-Type': 'text/csv; charset=utf-8' },
          })
        : this.report(job)
    }
    throw new HttpError(405, 'Méthode non autorisée.')
  }

  // --- Session ------------------------------------------------------------------------------

  private sessionStatus(): SessionStatus {
    const { session } = this
    // La « personne » se connecte elle-même quelques secondes après l'ouverture.
    if (session.browserOpen && !session.loggedIn && Date.now() >= session.loginAt) {
      session.loggedIn = true
    }
    return {
      browser_open: session.browserOpen,
      logged_in: session.loggedIn,
      account_id: session.loggedIn ? ACCOUNT : null,
      page: session.loggedIn ? 'likes' : session.browserOpen ? 'login' : null,
      challenge_required: false,
      consent_required: false,
      busy: this.busyJob !== null,
    }
  }

  private startSession(): SessionStatus {
    if (!this.session.browserOpen) {
      this.session = { browserOpen: true, loggedIn: false, loginAt: Date.now() + this.timing.login }
    }
    return this.sessionStatus()
  }

  private deleteSession() {
    this.session = { browserOpen: false, loggedIn: false, loginAt: 0 }
    return { deleted: ['browser-profile'] }
  }

  private deleteData() {
    this.deleteSession()
    this.jobs = new Map()
    this.removed.clear()
    this.nextJobId = 1
    return { deleted: ['iuc.db', 'reports', 'logs'] }
  }

  // --- Nettoyages ---------------------------------------------------------------------------

  private job(id: number): DemoJob {
    const job = this.jobs.get(id)
    if (!job) throw new HttpError(404, `Aucun nettoyage n°${id}.`)
    return job
  }

  private out(job: DemoJob): Job {
    const counts: Partial<Record<ItemStatus, number>> = {}
    for (const item of job.items) counts[item.status] = (counts[item.status] ?? 0) + 1
    return {
      id: job.id,
      status: job.status,
      created_at: job.createdAt,
      account_id: ACCOUNT,
      filters: job.filters,
      counts,
      to_process: (counts.pending ?? 0) + (counts.selected ?? 0),
      running: job.task !== null,
    }
  }

  /** Likes encore en place sur la page des likes filtrée par le panneau « Trier et filtrer ». */
  private filteredLikes(filters: Filters): DemoLike[] {
    const start = filters.start_date ?? FIRST_DAY
    const end = filters.end_date ?? this.today
    const likes = this.history.filter(
      (like) => !this.removed.has(like.key) && like.likedOn >= start && like.likedOn <= end,
    )
    return filters.sort === 'oldest_first' ? likes : likes.toReversed()
  }

  private createJob(body: unknown): Job {
    const { filters, maxScanned } = validateCriteria(body, this.today)
    this.ensureIdle()
    if (!this.sessionStatus().logged_in) {
      throw new HttpError(409, 'Connecte-toi d’abord à Instagram dans la fenêtre du navigateur.')
    }
    const job: DemoJob = {
      id: this.nextJobId++,
      status: 'collecting',
      createdAt: new Date().toISOString(),
      startedAt: null,
      finishedAt: null,
      filters,
      items: [],
      runs: 0,
      activeSeconds: 0,
      task: { kind: 'preview', request: null },
      history: [],
    }
    this.jobs.set(job.id, job)
    this.busyJob = job.id
    const likes = this.filteredLikes(filters).slice(0, maxScanned ?? undefined)
    this.publish(job, 'status', { job: this.out(job) })
    let scanned = 0
    const timer = setInterval(() => {
      if (job.task?.request === 'stop') {
        clearInterval(timer)
        job.status = 'failed'
        this.finish(job, false, 'Collecte interrompue avant la fin.', null)
        return
      }
      scanned = Math.min(scanned + this.timing.scanStep, likes.length)
      if (likes.length) this.publish(job, 'progress', { scanned })
      if (scanned < likes.length) return
      clearInterval(timer)
      job.items = likes.map((like, position) => this.item(like, position, 'pending'))
      job.status = 'ready'
      this.finish(job, true, `Aperçu prêt : ${likes.length} likes ciblés.`, {
        targeted: likes.length,
      })
    }, this.timing.scanMs)
    return this.out(job)
  }

  private item(like: DemoLike, position: number, status: ItemStatus): Item {
    return {
      id: this.nextItemId++,
      rank: position + 1,
      media_key: like.key,
      label: label(like, position),
      author: like.author,
      media_kind: like.kind.kind,
      shared_on: like.sharedOn,
      status,
      error: ERRORS[status] ?? null,
      processed_at: null,
    }
  }

  private items(job: DemoJob, params: URLSearchParams) {
    const status = params.get('status')
    const offset = Number(params.get('offset') ?? 0)
    const limit = Math.min(Number(params.get('limit') ?? 50), 500)
    const matching = status ? job.items.filter((item) => item.status === status) : job.items
    return { items: matching.slice(offset, offset + limit), total: matching.length, offset, limit }
  }

  private patchItems(job: DemoJob, body: unknown) {
    const { item_ids: ids, excluded } = (body ?? {}) as { item_ids?: number[]; excluded?: boolean }
    if (!Array.isArray(ids) || ids.length === 0 || typeof excluded !== 'boolean') {
      throw new HttpError(422, [{ msg: 'Indique au moins un like et l’action à faire.' }])
    }
    if (job.status !== 'ready' && job.status !== 'paused') {
      throw new HttpError(
        409,
        `Le nettoyage n°${job.id} est « ${jobStatusLabels[job.status]} » : les exclusions ne se modifient que s'il est prêt ou en pause.`,
      )
    }
    const wanted = new Set(ids)
    const backTo: ItemStatus = job.status === 'ready' ? 'pending' : 'selected'
    const sources: ItemStatus[] = excluded ? ['pending', 'selected'] : ['excluded']
    let changed = 0
    for (const item of job.items) {
      if (wanted.has(item.id) && sources.includes(item.status)) {
        item.status = excluded ? 'excluded' : backTo
        changed++
      }
    }
    return { changed, job: this.out(job) }
  }

  private launch(job: DemoJob, body: unknown, allowed: JobStatus[]): Job {
    if (!allowed.includes(job.status)) {
      throw new HttpError(
        409,
        `Le nettoyage n°${job.id} est « ${jobStatusLabels[job.status]} » : il ne peut pas être lancé.`,
      )
    }
    this.ensureIdle()
    const limit = (body as { limit?: number | null } | undefined)?.limit ?? null
    for (const item of job.items) if (item.status === 'pending') item.status = 'selected'
    job.status = 'running'
    job.startedAt ??= new Date().toISOString()
    job.runs++
    job.task = { kind: 'cleanup', request: null }
    this.busyJob = job.id
    this.publish(job, 'status', { job: this.out(job) })

    const runStart = Date.now()
    const totals = { done: 0, failed: 0, skipped: 0 }
    const timer = setInterval(() => {
      const queue = job.items.filter((item) => item.status === 'selected')
      const room =
        limit === null ? BATCH_SIZE : limit - totals.done - totals.failed - totals.skipped
      const now = new Date().toISOString()
      let removedInBatch = 0
      for (const item of queue.slice(0, Math.min(BATCH_SIZE, room))) {
        const draw = this.random()
        item.status = draw < 0.012 ? 'failed' : draw < 0.02 ? 'skipped' : 'done'
        item.error = ERRORS[item.status] ?? null
        item.processed_at = now
        if (item.status === 'done') {
          this.removed.add(item.media_key)
          removedInBatch++
        }
        totals[item.status as 'done' | 'failed' | 'skipped']++
      }
      this.publish(job, 'batch', { removed: removedInBatch, total: totals.done })

      const remaining = job.items.filter((item) => item.status === 'selected').length
      const handled = totals.done + totals.failed + totals.skipped
      const reason: StopReason | null =
        job.task?.request === 'stop'
          ? 'user_stop'
          : remaining === 0
            ? 'completed'
            : job.task?.request === 'pause'
              ? 'user_pause'
              : limit !== null && handled >= limit
                ? 'run_limit'
                : null
      if (reason === null) return
      clearInterval(timer)
      job.activeSeconds += Math.round((Date.now() - runStart) / 1000)
      job.status =
        reason === 'completed' ? 'completed' : reason === 'user_stop' ? 'stopped' : 'paused'
      if (job.status !== 'paused') job.finishedAt = new Date().toISOString()
      this.finish(job, true, STOP_MESSAGES[reason], {
        reason,
        ...totals,
        remaining,
        detail: null,
      })
    }, this.timing.batchMs)
    return this.out(job)
  }

  private pause(job: DemoJob): Job {
    if (job.task?.kind !== 'cleanup') throw new HttpError(409, 'Ce nettoyage n’est pas en cours.')
    job.task.request = 'pause'
    return this.out(job)
  }

  private stop(job: DemoJob): Job {
    if (job.task) {
      job.task.request = 'stop'
    } else if (job.status === 'ready' || job.status === 'paused') {
      job.status = 'stopped'
      job.finishedAt = new Date().toISOString()
    } else {
      throw new HttpError(
        409,
        `Le nettoyage n°${job.id} est « ${jobStatusLabels[job.status]} » : il n'y a rien à arrêter.`,
      )
    }
    return this.out(job)
  }

  private ensureIdle(): void {
    if (this.busyJob !== null) {
      throw new HttpError(
        409,
        'Une collecte ou un nettoyage est déjà en cours : attends sa fin ou mets-le en pause.',
      )
    }
  }

  // --- Rapport ------------------------------------------------------------------------------

  private report(job: DemoJob): JobReport {
    const byStatus: Partial<Record<ItemStatus, number>> = {}
    for (const item of job.items) byStatus[item.status] = (byStatus[item.status] ?? 0) + 1
    return {
      nettoyage: job.id,
      statut: job.status,
      compte: ACCOUNT,
      criteres: job.filters,
      cree_le: job.createdAt,
      premiere_execution: job.startedAt,
      fin: job.finishedAt,
      executions: job.runs,
      duree_active_secondes: job.activeSeconds,
      likes_cibles: job.items.length,
      par_statut: byStatus,
      likes: job.items.map((item): ReportLine => ({
        rang: item.rank,
        auteur: item.author,
        type: KINDS.find((kind) => kind.kind === item.media_kind)?.report ?? 'inconnu',
        partagee_le: item.shared_on ? frenchDay(item.shared_on) : '',
        statut: item.status,
        traite_le: item.processed_at,
        detail: item.error,
        identifiant: item.media_key,
      })),
    }
  }

  // --- Flux d'événements (Server-Sent Events) -------------------------------------------------

  /** Comme l'API : un « snapshot », puis les événements de la dernière tâche, puis la suite en
   * direct. Sans tâche en cours, le flux se termine aussitôt par « end ». */
  subscribe(jobId: number, listener: EventListener): () => void {
    const job = this.jobs.get(jobId)
    if (!job) return () => {}
    listener('snapshot', { job: this.out(job) }, null)
    const starts = job.history.flatMap((event, index) => (event.type === 'status' ? [index] : []))
    const replay = starts.length ? job.history.slice(starts.at(-1)) : []
    for (const event of replay) listener(event.type, event.data, event.id)
    if (!job.task) {
      if (replay.at(-1)?.type !== 'end') {
        const data: EndData = {
          ok: true,
          message: 'Aucune tâche en cours pour ce nettoyage.',
          result: null,
          job: this.out(job),
        }
        listener('end', data, null)
      }
      return () => {}
    }
    const listeners = this.listeners.get(jobId) ?? new Set<EventListener>()
    listeners.add(listener)
    this.listeners.set(jobId, listeners)
    return () => listeners.delete(listener)
  }

  private publish(job: DemoJob, type: JobEventType, data: unknown): void {
    const event = { id: this.nextEventId++, type, data }
    job.history.push(event)
    for (const listener of this.listeners.get(job.id) ?? []) listener(type, data, event.id)
  }

  private finish(job: DemoJob, ok: boolean, message: string, result: EndData['result']): void {
    job.task = null
    this.busyJob = null
    const data: EndData = { ok, message, result, job: this.out(job) }
    this.publish(job, 'end', data)
    this.listeners.delete(job.id)
  }

  // --- Données de départ --------------------------------------------------------------------

  /** Trois nettoyages fictifs, comme scripts/demo.py : terminé, en pause et prêt. */
  private seed(): void {
    const ago = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString()
    const add = (
      filters: Filters,
      status: JobStatus,
      hours: number,
      outcome: (index: number) => ItemStatus,
      activeSeconds: number,
    ) => {
      const likes = this.filteredLikes(filters)
      const job: DemoJob = {
        id: this.nextJobId++,
        status,
        createdAt: ago(hours),
        startedAt: status === 'ready' ? null : ago(hours - 0.1),
        finishedAt: status === 'completed' ? ago(hours - 1) : null,
        filters,
        items: likes.map((like, position) => this.item(like, position, outcome(position))),
        runs: status === 'ready' ? 0 : 1,
        activeSeconds,
        task: null,
        history: [],
      }
      for (const item of job.items) {
        if (item.status === 'done' || item.status === 'failed' || item.status === 'skipped') {
          item.processed_at = ago(hours - 0.2)
          if (item.status === 'done') this.removed.add(item.media_key)
        }
      }
      this.jobs.set(job.id, job)
    }
    add(
      { sort: 'newest_first', start_date: '2021-03-01', end_date: '2021-06-30' },
      'completed',
      50,
      (index) =>
        index === 7 ? 'failed' : index === 19 ? 'skipped' : index % 17 === 3 ? 'excluded' : 'done',
      312,
    )
    add(
      { sort: 'oldest_first', start_date: null, end_date: '2020-12-31' },
      'paused',
      5,
      (index) => (index < 150 ? 'done' : index % 23 === 0 ? 'excluded' : 'selected'),
      380,
    )
    add(
      { sort: 'newest_first', start_date: '2023-06-01', end_date: null },
      'ready',
      0.3,
      (index) => (index % 41 === 5 ? 'excluded' : 'pending'),
      0,
    )
  }
}

/** Mêmes règles que le backend (CleanupFilters et JobCreate) : seul le filtre d'Instagram est
 * accepté, tout autre champ est refusé. */
function validateCriteria(
  body: unknown,
  today: string,
): { filters: Filters; maxScanned: number | null } {
  const raw = (body ?? {}) as Record<string, unknown>
  const allowed = new Set(['sort', 'start_date', 'end_date', 'max_scanned'])
  const extra = Object.keys(raw).filter((key) => !allowed.has(key))
  if (extra.length) {
    throw new HttpError(
      422,
      extra.map((key) => ({ loc: ['body', key], msg: 'Extra inputs are not permitted' })),
    )
  }
  const sort = raw.sort === 'oldest_first' ? 'oldest_first' : 'newest_first'
  const start = typeof raw.start_date === 'string' && raw.start_date ? raw.start_date : null
  const end = typeof raw.end_date === 'string' && raw.end_date ? raw.end_date : null
  for (const day of [start, end]) {
    if (day && day > today) {
      throw new HttpError(422, [
        { msg: `Value error, la date ${frenchDay(day)} est dans le futur` },
      ])
    }
  }
  if (start && end && start > end) {
    throw new HttpError(422, [
      { msg: 'Value error, la date de début doit précéder la date de fin' },
    ])
  }
  const max = raw.max_scanned
  if (max !== undefined && max !== null && !(Number.isInteger(max) && (max as number) >= 1)) {
    throw new HttpError(422, [{ msg: 'Le nombre maximal doit être un entier supérieur à 0.' }])
  }
  return {
    filters: { sort, start_date: start, end_date: end },
    maxScanned: typeof max === 'number' ? max : null,
  }
}

/** Même CSV que le backend : « ; », UTF-8 avec BOM, date et heure du retrait séparées. */
export function reportCsv(report: JobReport): string {
  const labels: Record<ItemStatus, string> = {
    pending: 'en attente',
    selected: 'à retirer',
    excluded: 'exclu',
    done: 'retiré',
    failed: 'échec',
    skipped: 'introuvable',
  }
  const pad = (value: number) => String(value).padStart(2, '0')
  const rows = [
    [
      'rang',
      'auteur',
      'type',
      'partagée le (selon Instagram)',
      'statut',
      'traité le',
      'heure',
      'détail',
      'identifiant',
    ],
    ...report.likes.map((line) => {
      const processed = line.traite_le ? new Date(line.traite_le) : null
      return [
        String(line.rang),
        line.auteur ? `@${line.auteur}` : '',
        line.type,
        line.partagee_le,
        labels[line.statut],
        processed
          ? `${pad(processed.getDate())}/${pad(processed.getMonth() + 1)}/${processed.getFullYear()}`
          : '',
        processed ? `${pad(processed.getHours())}:${pad(processed.getMinutes())}` : '',
        line.detail ?? '',
        line.identifiant,
      ]
    }),
  ]
  const cell = (value: string) =>
    /[;"\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
  return '﻿' + rows.map((row) => row.map(cell).join(';')).join('\r\n') + '\r\n'
}

async function readJson(request: Request): Promise<unknown> {
  const text = await request.text()
  return text ? (JSON.parse(text) as unknown) : undefined
}

function json(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}
