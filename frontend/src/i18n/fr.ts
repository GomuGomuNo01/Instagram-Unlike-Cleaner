// Vocabulaire partagé de l'interface, en français. Une version anglaise reprendra les mêmes
// clés (même structure, autres textes).
import type { ContentFilter, ItemStatus, JobStatus, MediaKind, SortOrder } from '../api/types'

export const jobStatusLabels: Record<JobStatus, string> = {
  created: 'créé',
  collecting: 'collecte en cours',
  ready: 'prêt',
  running: 'en cours',
  paused: 'en pause',
  completed: 'terminé',
  stopped: 'arrêté',
  failed: 'échec',
}

export const itemStatusLabels: Record<ItemStatus, string> = {
  pending: 'à retirer',
  selected: 'à retirer',
  excluded: 'gardé',
  done: 'retiré',
  failed: 'échec',
  skipped: 'introuvable',
}

export const mediaKindLabels: Record<MediaKind, string> = {
  photo: 'Photo',
  video: 'Vidéo / Reel',
  carousel: 'Carrousel',
}

export const contentFilterLabels: Record<ContentFilter, string> = {
  all: 'Tous les contenus',
  posts: 'Publications (photos et carrousels)',
  reels: 'Reels (vidéos)',
}

export const sortOrderLabels: Record<SortOrder, string> = {
  newest_first: 'Du plus récent au plus ancien',
  oldest_first: 'Du plus ancien au plus récent',
}

/** Marche à suivre affichée après un arrêt, selon sa raison (StopReason côté backend). */
export const stopAdvice: Record<string, string> = {
  completed: 'Tous les likes validés ont été traités. Le rapport final est prêt.',
  run_limit: 'Le nombre demandé est atteint. Tu peux reprendre quand tu veux.',
  daily_limit:
    'La limite quotidienne est atteinte (DAILY_LIMIT). Reprends demain : le nettoyage repartira là où il s’est arrêté.',
  action_blocked:
    'Instagram a signalé une limite ou une erreur. Attends au moins quelques heures avant de reprendre, et pense à baisser la cadence.',
  unknown_dialog:
    'Instagram a affiché une fenêtre inconnue : rien n’a été confirmé. Un diagnostic a été enregistré dans le dossier data/diagnostics.',
  selection_mismatch:
    'La sélection ne correspondait pas exactement au lot prévu : rien n’a été retiré. Un diagnostic a été enregistré.',
  not_removed:
    'Certains likes sont restés affichés : ils sont marqués en échec. Un diagnostic a été enregistré.',
  page_unavailable:
    'La page des likes n’était plus utilisable (fenêtre fermée, connexion perdue…). Vérifie la fenêtre puis reprends.',
  user_pause: 'Nettoyage en pause. Tu peux le reprendre quand tu veux.',
  user_stop: 'Nettoyage arrêté : les likes restants ne seront pas retirés.',
}
