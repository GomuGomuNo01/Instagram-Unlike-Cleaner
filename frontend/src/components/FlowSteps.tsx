import { CheckIcon } from './icons'

const steps = ['Connexion', 'Critères', 'Aperçu', 'Nettoyage', 'Rapport'] as const

export type FlowStep = 1 | 2 | 3 | 4 | 5

/** Où en est l'utilisateur dans le parcours. L'état est donné par le texte et l'icône, pas
 * seulement par la couleur. Les étapes restent en place pendant la transition d'écran. */
export function FlowSteps({ current }: { current: FlowStep }) {
  return (
    <nav aria-label="Étapes du nettoyage" className="flow-steps mb-8 sm:mb-12">
      <p className="text-small text-fg-muted sm:hidden">
        Étape {current} sur {steps.length} :{' '}
        <span className="font-semibold text-fg">{steps[current - 1]}</span>
      </p>
      <div aria-hidden="true" className="mt-3 flex gap-1 sm:hidden">
        {steps.map((label, index) => (
          <span
            key={label}
            className={`h-1 flex-1 rounded-full transition-colors duration-component ${
              index < current ? 'bg-primary' : 'bg-fill-strong'
            }`}
          />
        ))}
      </div>
      <ol className="hidden items-center gap-3 sm:flex">
        {steps.map((label, index) => {
          const step = index + 1
          const state = step < current ? 'done' : step === current ? 'current' : 'todo'
          return (
            <li
              key={label}
              aria-current={state === 'current' ? 'step' : undefined}
              className="flex flex-1 items-center gap-3 last:flex-none"
            >
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-small font-semibold transition-colors duration-component ${
                  state === 'todo'
                    ? 'border border-border-strong text-fg-muted'
                    : state === 'current'
                      ? 'bg-primary text-on-primary elevation-sm'
                      : 'bg-primary-soft text-primary-strong'
                }`}
              >
                {state === 'done' ? <CheckIcon className="h-4 w-4" /> : step}
                <span className="sr-only">
                  {state === 'done' ? ' (terminée)' : state === 'current' ? ' (en cours)' : ''}
                </span>
              </span>
              <span
                className={`text-small whitespace-nowrap ${
                  state === 'current' ? 'font-semibold text-fg' : 'text-fg-muted'
                }`}
              >
                {label}
              </span>
              {step < steps.length && (
                <span
                  aria-hidden="true"
                  className={`h-px min-w-4 flex-1 ${step < current ? 'bg-primary' : 'bg-border'}`}
                />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
