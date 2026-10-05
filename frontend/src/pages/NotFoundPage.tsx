import { AppPage } from '../components/Layout'
import { ButtonLink, PageHeader } from '../components/ui'

export function NotFoundPage() {
  return (
    <AppPage>
      <PageHeader
        title="Page introuvable"
        description="Cette adresse ne correspond à aucun écran d’IUC."
        actions={<ButtonLink to="/">Revenir à l’accueil</ButtonLink>}
      />
    </AppPage>
  )
}
