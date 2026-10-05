import { CheckIcon } from './icons'

const steps = ['Connexion', 'Critères', 'Aperçu', 'Nettoyage', 'Rapport'] as const

export type FlowStep = 1 | 2 | 3 | 4 | 5

/** Où en est l'utilisateur dans le parcours. L'état est donné par le texte et l'icône, pas
 * seulement par la couleur. */
export function FlowSteps({ current }: { current: FlowStep }) {
  return (
    <nav aria-label="Étapes du nettoyage" className="mb-8">
      <p className="text-small mb-3 sm:hidden">
        Étape {current} sur {steps.length} : {steps[current - 1]}
      </p>
      <ol className="flex items-center gap-2">
        {steps.map((label, index) => {
          const step = index + 1
          const state = step < current ? 'done' : step === current ? 'current' : 'todo'
          return (
            <li
              key={label}
              aria-current={state === 'current' ? 'step' : undefined}
              className="flex flex-1 items-center gap-2"
            >
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                  state === 'todo'
                    ? 'border border-zinc-300 text-zinc-600 dark:border-zinc-700 dark:text-zinc-400'
                    : 'bg-indigo-600 text-white'
                }`}
              >
                {state === 'done' ? <CheckIcon className="h-4 w-4" /> : step}
                <span className="sr-only">
                  {state === 'done' ? ' (terminée)' : state === 'current' ? ' (en cours)' : ''}
                </span>
              </span>
              <span
                className={`hidden text-sm sm:inline ${
                  state === 'current' ? 'font-semibold' : 'text-zinc-600 dark:text-zinc-400'
                }`}
              >
                {label}
              </span>
              {step < steps.length && (
                <span aria-hidden="true" className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
