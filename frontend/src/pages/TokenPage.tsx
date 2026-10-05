import { useState, type FormEvent } from 'react'

import { saveToken } from '../api/token'
import { Button, Card, Field, inputClass, PageHeader } from '../components/ui'

/** Écran de développement (`npm run dev`) : l'interface servie par `iuc serve` reçoit le
 * jeton automatiquement et n'affiche jamais cet écran. */
export function TokenPage() {
  const [token, setToken] = useState('')

  const submit = (event: FormEvent) => {
    event.preventDefault()
    saveToken(token)
    window.location.reload()
  }

  return (
    <main className="mx-auto max-w-xl px-4 py-16 sm:px-6">
      <PageHeader
        title="Jeton de l’API"
        description="Mode développement : colle le jeton affiché par `iuc serve` dans ton terminal."
      />
      <Card>
        <form onSubmit={submit} className="space-y-6">
          <Field id="jeton" label="Jeton">
            {(aria) => (
              <input
                {...aria}
                value={token}
                onChange={(event) => setToken(event.target.value)}
                autoComplete="off"
                className={`${inputClass} font-mono`}
              />
            )}
          </Field>
          <Button type="submit" disabled={!token.trim()} className="w-full sm:w-auto">
            Continuer
          </Button>
        </form>
      </Card>
    </main>
  )
}
