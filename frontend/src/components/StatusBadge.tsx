import type { ItemStatus, JobStatus } from '../api/types'
import { itemStatusLabels, jobStatusLabels } from '../i18n/fr'
import { Badge } from './ui'

const jobTones = {
  created: 'neutral',
  collecting: 'info',
  ready: 'info',
  running: 'info',
  paused: 'warning',
  completed: 'success',
  stopped: 'neutral',
  failed: 'danger',
} as const satisfies Record<JobStatus, string>

const itemTones = {
  pending: 'info',
  selected: 'info',
  excluded: 'neutral',
  done: 'success',
  failed: 'danger',
  skipped: 'warning',
} as const satisfies Record<ItemStatus, string>

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return <Badge tone={jobTones[status]}>{jobStatusLabels[status]}</Badge>
}

export function ItemStatusBadge({ status }: { status: ItemStatus }) {
  return <Badge tone={itemTones[status]}>{itemStatusLabels[status]}</Badge>
}
