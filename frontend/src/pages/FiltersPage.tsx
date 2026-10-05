import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'

import { api, ApiError, errorMessage, unwrap } from '../api/client'
import type { Author, ContentFilter, SortOrder } from '../api/types'
import { AuthorsPicker } from '../components/AuthorsPicker'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { Alert, Button, Card, Field, inputClass, PageHeader } from '../components/ui'
import { contentFilterLabels, sortOrderLabels } from '../i18n/fr'
import {
  buildJobRequest,
  emptyFilters,
  localToday,
  validateFilters,
  type FiltersErrors,
  type FiltersForm,
} from '../lib/filters'

const FIELD_ORDER: (keyof FiltersForm)[] = ['startDate', 'endDate', 'excludeAuthors', 'maxScanned']
const FIELD_IDS: Partial<Record<keyof FiltersForm, string>> = {
  startDate: 'date-debut',
  endDate: 'date-fin',
  maxScanned: 'maximum',
}

/** Critères du nettoyage. La période et l'ordre passent par le filtre d'Instagram ; le type
 * et les comptes sont filtrés par IUC (la version web d'Instagram ne les propose pas). */
export function FiltersPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<FiltersForm>(emptyFilters)
  const [errors, setErrors] = useState<FiltersErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [needsLogin, setNeedsLogin] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [authors, setAuthors] = useState<Author[]>([])
  const today = localToday()

  useEffect(() => {
    let active = true
    unwrap(api.GET('/api/authors')).then(
      (loaded) => {
        if (active) setAuthors(loaded)
      },
      () => {
        // Liste facultative : sans elle, la saisie libre reste possible.
      },
    )
    return () => {
      active = false
    }
  }, [])

  const update = <K extends keyof FiltersForm>(key: K, value: FiltersForm[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }))
    setErrors((previous) => ({ ...previous, [key]: undefined }))
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const problems = validateFilters(form, today)
    setErrors(problems)
    setServerError(null)
    setNeedsLogin(false)
    const first = FIELD_ORDER.find((key) => problems[key])
    if (first) {
      document.getElementById(FIELD_IDS[first] ?? '')?.focus()
      return
    }
    setSubmitting(true)
    try {
      const job = await unwrap(api.POST('/api/jobs', { body: buildJobRequest(form) }))
      navigate(`/nettoyages/${job.id}/apercu`)
    } catch (failure) {
      // Les valeurs saisies sont conservées : seul le message s'affiche.
      setServerError(errorMessage(failure))
      setNeedsLogin(failure instanceof ApiError && failure.status === 409)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppPage>
      <FlowSteps current={2} />
      <PageHeader
        title="Choisis les likes à cibler"
        description="Rien n’est retiré à cette étape : IUC prépare d’abord un aperçu que tu pourras vérifier."
      />
      <form onSubmit={submit} noValidate className="space-y-6">
        <Card>
          <Section
            title="Période"
            help="Date à laquelle tu as aimé la publication. Laisse vide pour tout l’historique."
          >
            <div className="grid gap-6 sm:grid-cols-2">
              <Field id="date-debut" label="Du" error={errors.startDate}>
                {(aria) => (
                  <input
                    {...aria}
                    type="date"
                    max={today}
                    value={form.startDate}
                    onChange={(event) => update('startDate', event.target.value)}
                    className={inputClass}
                  />
                )}
              </Field>
              <Field id="date-fin" label="Au" error={errors.endDate}>
                {(aria) => (
                  <input
                    {...aria}
                    type="date"
                    max={today}
                    value={form.endDate}
                    onChange={(event) => update('endDate', event.target.value)}
                    className={inputClass}
                  />
                )}
              </Field>
            </div>
            <fieldset className="mt-6">
              <legend className="text-sm font-medium">Ordre de parcours</legend>
              <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:gap-6">
                {(Object.keys(sortOrderLabels) as SortOrder[]).map((sort) => (
                  <label key={sort} className="flex min-h-11 cursor-pointer items-center gap-3">
                    <input
                      type="radio"
                      name="sort"
                      checked={form.sort === sort}
                      onChange={() => update('sort', sort)}
                      className="h-5 w-5 accent-indigo-600"
                    />
                    <span className="text-body">{sortOrderLabels[sort]}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          </Section>
        </Card>

        <Card>
          <Section
            title="Contenus et comptes"
            help="Un like dont le type ou l’auteur est illisible est toujours gardé."
          >
            <Field id="contenu" label="Type de contenu">
              {(aria) => (
                <select
                  {...aria}
                  value={form.content}
                  onChange={(event) => update('content', event.target.value as ContentFilter)}
                  className={inputClass}
                >
                  {(Object.keys(contentFilterLabels) as ContentFilter[]).map((content) => (
                    <option key={content} value={content}>
                      {contentFilterLabels[content]}
                    </option>
                  ))}
                </select>
              )}
            </Field>
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <AuthorsPicker
                label="Cibler uniquement ces comptes"
                help="Laisse vide pour cibler tous les comptes."
                value={form.includeAuthors}
                onChange={(value) => update('includeAuthors', value)}
                suggestions={authors}
                unavailable={form.excludeAuthors}
                unavailableLabel="déjà protégé"
              />
              <AuthorsPicker
                label="Ne jamais toucher à ces comptes"
                help="Leurs likes sont toujours gardés."
                error={errors.excludeAuthors}
                value={form.excludeAuthors}
                onChange={(value) => update('excludeAuthors', value)}
                suggestions={authors}
                unavailable={form.includeAuthors}
                unavailableLabel="déjà ciblé"
              />
            </div>
          </Section>
        </Card>

        <Card>
          <Section
            title="Premier essai"
            help="Facultatif : ne lire que les likes les plus récents de la période, pour tester."
          >
            <Field id="maximum" label="Nombre maximal de likes à lire" error={errors.maxScanned}>
              {(aria) => (
                <input
                  {...aria}
                  type="number"
                  min={1}
                  inputMode="numeric"
                  value={form.maxScanned}
                  onChange={(event) => update('maxScanned', event.target.value)}
                  className={`${inputClass} sm:max-w-48`}
                />
              )}
            </Field>
          </Section>
        </Card>

        {serverError && (
          <Alert tone="danger" title="L’aperçu n’a pas pu être préparé">
            <p>{serverError}</p>
            {needsLogin && (
              <p className="mt-2">
                <Link to="/connexion" className="font-medium underline">
                  Revenir à la connexion
                </Link>
              </p>
            )}
          </Alert>
        )}
        <div className="flex justify-end">
          <Button type="submit" size="lg" loading={submitting} className="w-full sm:w-auto">
            {submitting ? 'Préparation de l’aperçu…' : 'Préparer l’aperçu'}
          </Button>
        </div>
      </form>
    </AppPage>
  )
}

function Section({ title, help, children }: { title: string; help: string; children: ReactNode }) {
  return (
    <div>
      <h2 className="text-h3">{title}</h2>
      <p className="text-small mt-1">{help}</p>
      <div className="mt-6">{children}</div>
    </div>
  )
}
