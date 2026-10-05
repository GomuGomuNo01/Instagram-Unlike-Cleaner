import { AppPage } from '../components/Layout'
import { ArrowRightIcon } from '../components/icons'
import { ButtonLink, PageHeader } from '../components/ui'

export function NotFoundPage() {
  return (
    <AppPage>
      <PageHeader
        eyebrow="Erreur 404"
        title="Page introuvable"
        description="Cette adresse ne correspond à aucun écran d’IUC."
        actions={
          <ButtonLink to="/" trailingIcon={<ArrowRightIcon />}>
            Revenir à l’accueil
          </ButtonLink>
        }
      />
    </AppPage>
  )
}
