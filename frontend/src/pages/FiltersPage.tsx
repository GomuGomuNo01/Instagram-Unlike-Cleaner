import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { api, ApiError, errorMessage, unwrap } from '../api/client'
import type { Author, ContentFilter, SortOrder } from '../api/types'
import { AuthorsPicker } from '../components/AuthorsPicker'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { ArrowRightIcon } from '../components/icons'
import {
  Alert,
  Button,
  Card,
  ChoiceGroup,
  Field,
  PageHeader,
  Switch,
  TextLink,
} from '../components/ui'
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

const sortOptions = (Object.keys(sortOrderLabels) as SortOrder[]).map((value) => ({
  value,
  label: sortOrderLabels[value],
}))
const contentOptions = (Object.keys(contentFilterLabels) as ContentFilter[]).map((value) => ({
  value,
  label: contentFilterLabels[value],
}))

/** Critères du nettoyage. La période et l'ordre passent par le filtre d'Instagram ; le type
 * et les comptes sont filtrés par IUC (la version web d'Instagram ne les propose pas). */
export function FiltersPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<FiltersForm>(emptyFilters)
  const [trial, setTrial] = useState(false)
  const [errors, setErrors] = useState<FiltersErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [needsLogin, setNeedsLogin] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [authors, setAuthors] = useState<Author[]>([])
  const [authorsLoading, setAuthorsLoading] = useState(true)
  const today = localToday()

  useEffect(() => {
    let active = true
    unwrap(api.GET('/api/authors'))
      .then(
        (loaded) => {
          if (active) setAuthors(loaded)
        },
        () => {
          // Liste facultative : sans elle, la saisie libre reste possible.
        },
      )
      .finally(() => {
        if (active) setAuthorsLoading(false)
      })
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
    // Le nombre saisi est conservé même si l'essai est désactivé, mais n'est envoyé qu'avec.
    const sent = trial ? form : { ...form, maxScanned: '' }
    const problems = validateFilters(sent, today)
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
      const job = await unwrap(api.POST('/api/jobs', { body: buildJobRequest(sent) }))
      navigate(`/nettoyages/${job.id}/apercu`, { viewTransition: true })
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
      <form onSubmit={submit} noValidate className="space-y-4">
        <Card padding="lg">
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
                    className="input"
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
                    className="input"
                  />
                )}
              </Field>
            </div>
            <div className="mt-6">
              <ChoiceGroup
                legend="Ordre de parcours"
                name="ordre"
                options={sortOptions}
                value={form.sort}
                onChange={(sort) => update('sort', sort)}
              />
            </div>
          </Section>
        </Card>

        <Card padding="lg">
          <Section
            title="Contenus et comptes"
            help="Un like dont le type ou l’auteur est illisible est toujours gardé."
          >
            <ChoiceGroup
              legend="Type de contenu"
              name="contenu"
              options={contentOptions}
              value={form.content}
              onChange={(content) => update('content', content)}
            />
            <div className="mt-8 grid gap-8 lg:grid-cols-2">
              <AuthorsPicker
                label="Cibler uniquement ces comptes"
                help="Laisse vide pour cibler tous les comptes."
                value={form.includeAuthors}
                onChange={(value) => update('includeAuthors', value)}
                suggestions={authors}
                loading={authorsLoading}
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
                loading={authorsLoading}
                unavailable={form.includeAuthors}
                unavailableLabel="déjà ciblé"
              />
            </div>
          </Section>
        </Card>

        <Card padding="lg">
          <Switch
            checked={trial}
            onChange={(value) => {
              setTrial(value)
              setErrors((previous) => ({ ...previous, maxScanned: undefined }))
            }}
            label="Faire d’abord un essai"
            description="Ne lire que les likes les plus récents de la période, pour tester sur un petit volume."
          />
          {trial && (
            <Field
              id="maximum"
              label="Nombre maximal de likes à lire"
              help="Laisse vide pour lire toute la période."
              error={errors.maxScanned}
              className="mt-6 animate-fade-up"
            >
              {(aria) => (
                <input
                  {...aria}
                  type="number"
                  min={1}
                  inputMode="numeric"
                  placeholder="Par exemple 100"
                  value={form.maxScanned}
                  onChange={(event) => update('maxScanned', event.target.value)}
                  className="input sm:max-w-48"
                />
              )}
            </Field>
          )}
        </Card>

        {serverError && (
          <Alert tone="danger" title="L’aperçu n’a pas pu être préparé">
            <p>{serverError}</p>
            {needsLogin && (
              <p className="mt-2">
                <TextLink to="/connexion">Revenir à la connexion</TextLink>
              </p>
            )}
          </Alert>
        )}
        <div className="flex justify-end pt-2">
          <Button
            type="submit"
            size="lg"
            loading={submitting}
            trailingIcon={submitting ? undefined : <ArrowRightIcon />}
            className="w-full sm:w-auto"
          >
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
      <h2 className="text-h3 text-fg">{title}</h2>
      <p className="mt-1 text-small text-fg-muted">{help}</p>
      <div className="mt-6">{children}</div>
    </div>
  )
}
