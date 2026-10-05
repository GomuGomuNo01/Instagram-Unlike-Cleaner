import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'

import { useToast } from './toast-context'
import { ToastProvider } from './Toaster'

function Trigger() {
  const toast = useToast()
  return (
    <button type="button" onClick={() => toast({ title: 'Rapport téléchargé' })}>
      Télécharger
    </button>
  )
}

it('annonce la notification puis la retire à la fermeture', async () => {
  render(
    <ToastProvider>
      <Trigger />
    </ToastProvider>,
  )
  await userEvent.click(screen.getByRole('button', { name: 'Télécharger' }))

  const region = screen.getByRole('region', { name: 'Notifications' })
  expect(within(region).getByText('Rapport téléchargé')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Fermer la notification' }))
  await waitFor(() => expect(within(region).queryByText('Rapport téléchargé')).toBeNull())
})
