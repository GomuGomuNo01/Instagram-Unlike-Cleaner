import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { expect, it, vi } from 'vitest'

import { ConfirmDialog } from './Dialog'

function Harness({ onConfirm = () => {} }: { onConfirm?: () => void }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Ouvrir
      </button>
      <ConfirmDialog
        open={open}
        title="Tout supprimer ?"
        confirmLabel="Tout supprimer"
        danger
        requireText="SUPPRIMER"
        onConfirm={onConfirm}
        onCancel={() => setOpen(false)}
      >
        Action irréversible.
      </ConfirmDialog>
    </>
  )
}

it('demande de recopier le mot de confirmation avant de valider', async () => {
  const onConfirm = vi.fn()
  render(<Harness onConfirm={onConfirm} />)
  await userEvent.click(screen.getByRole('button', { name: 'Ouvrir' }))

  const dialog = screen.getByRole('dialog', { name: 'Tout supprimer ?' })
  expect(dialog).toHaveAccessibleDescription('Action irréversible.')
  expect(screen.getByRole('button', { name: 'Annuler' })).toHaveFocus()
  const confirm = screen.getByRole('button', { name: 'Tout supprimer' })
  expect(confirm).toBeDisabled()

  await userEvent.type(screen.getByLabelText(/Pour confirmer/), 'supprimer')
  expect(screen.getByText('Confirmation saisie.')).toBeInTheDocument()
  await userEvent.click(confirm)
  expect(onConfirm).toHaveBeenCalledOnce()
})

it('garde le focus dans la fenêtre et se ferme avec Échap', async () => {
  render(<Harness />)
  const opener = screen.getByRole('button', { name: 'Ouvrir' })
  await userEvent.click(opener)

  await userEvent.click(screen.getByLabelText(/Pour confirmer/))
  await userEvent.type(screen.getByLabelText(/Pour confirmer/), 'SUPPRIMER')
  await userEvent.tab() // Annuler
  await userEvent.tab() // Tout supprimer
  await userEvent.tab() // retour au premier élément de la fenêtre
  expect(screen.getByLabelText(/Pour confirmer/)).toHaveFocus()

  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(opener).toHaveFocus()
})
