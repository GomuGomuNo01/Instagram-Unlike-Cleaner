import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { api, ApiError, errorMessage, unwrap } from '../api/client'
import type { SortOrder } from '../api/types'
import { FlowSteps } from '../components/FlowSteps'
import { AppPage } from '../components/Layout'
import { ArrowRightIcon, InfoIcon } from '../components/icons'
import {
  Alert,
  Badge,
  Button,
  Card,
  ChoiceGroup,
  Field,
  PageHeader,
  Switch,
  TextLink,
} from '../components/ui'
import { sortOrderLabels } from '../i18n/fr'
import {
  buildJobRequest,
  emptyFilters,
  localToday,
  validateFilters,
  type FiltersErrors,
  type FiltersForm,
} from '../lib/filters'

const FIELD_ORDER: (keyof FiltersForm)[] = ['startDate', 'endDate', 'maxScanned']
const FIELD_IDS: Record<string, string> = {
  startDate: 'date-debut',
  endDate: 'date-fin',
  maxScanned: 'maximum',
}

const sortOptions = (Object.keys(sortOrderLabels) as SortOrder[]).map((value) => ({
  value,
  label: sortOrderLabels[value],
}))

/** Critères du nettoyage : le filtre d'Instagram, identique à son panneau « Trier et
 * filtrer » (tri, date de début, date de fin du like). C'est le seul filtre qu'Instagram
 * web propose, et IUC n'en ajoute aucun : le tri fin se fait ensuite dans l'aperçu. */
export function FiltersPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<FiltersForm>(emptyFilters)
  const [trial, setTrial] = useState(false)
  const [errors, setErrors] = useState<FiltersErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [needsLogin, setNeedsLogin] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const today = localToday()

  const update = <K extends keyof FiltersForm>(key: K, value: FiltersForm[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }))
    setErrors((previous) => ({ ...previous, [key]: undefined }))
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    // Le nombre saisi est conservé quand l'essai est désactivé, mais n'est envoyé qu'avec lui.
    const sent: FiltersForm = { ...form, maxScanned: trial ? form.maxScanned : '' }
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
        description="Les mêmes réglages que sur Instagram. Rien n’est retiré à cette étape : IUC prépare d’abord un aperçu que tu pourras vérifier."
      />
      <form onSubmit={submit} noValidate className="space-y-4">
        <Card padding="lg">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-h3 text-fg">Trier et filtrer</h2>
            <Badge tone="info">Filtre d’Instagram</Badge>
          </div>
          <p className="mt-1 text-small text-fg-muted">
            IUC remplit pour toi ce panneau de ta page des likes. Les dates sont celles du like ;
            laisse-les vides pour tout l’historique.
          </p>
          <div className="mt-6">
            <ChoiceGroup
              legend="Trier par"
              name="ordre"
              options={sortOptions}
              value={form.sort}
              onChange={(sort) => update('sort', sort)}
            />
          </div>
          <div className="mt-6 grid gap-6 sm:grid-cols-2">
            <Field id="date-debut" label="Date de début" error={errors.startDate}>
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
            <Field id="date-fin" label="Date de fin" error={errors.endDate}>
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
          <p className="mt-6 flex gap-3 border-t border-border pt-6 text-small text-fg-muted">
            <InfoIcon className="mt-1 h-4 w-4 shrink-0 text-info-strong" />
            <span>
              Instagram web ne filtre ni par compte ni par type de contenu. L’aperçu indique le
              compte et le type de chaque like : tu décocheras ceux que tu veux garder.
            </span>
          </p>
        </Card>

        <Card padding="lg">
          <Switch
            checked={trial}
            onChange={(value) => {
              setTrial(value)
              setErrors((previous) => ({ ...previous, maxScanned: undefined }))
            }}
            label="Faire d’abord un essai"
            description="Ne lire que les premiers likes de la liste filtrée, pour tester sur un petit volume."
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
