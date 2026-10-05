import { useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import type { Author } from '../api/types'
import { normalizeAuthor } from '../lib/filters'
import { plural } from '../lib/format'
import { ChevronDownIcon, CloseIcon, SearchIcon } from './icons'
import { FieldMessage, Spinner } from './ui'

const MAX_SHOWN = 50

interface Option {
  author: string
  likes: number | null // null : compte saisi à la main, absent de la liste connue
  blockedBy?: string // déjà choisi dans l'autre liste
}

/** Choix de comptes Instagram dans la liste des comptes de tes likes (recherche, clic,
 * clavier), avec saisie libre pour un compte absent de la liste.
 * Modèle d'accessibilité : combobox + listbox (ARIA). */
export function AuthorsPicker({
  label,
  help,
  error,
  value,
  onChange,
  suggestions,
  loading = false,
  unavailable,
  unavailableLabel,
}: {
  label: string
  help: string
  error?: string
  value: string[]
  onChange: (authors: string[]) => void
  suggestions: Author[]
  /** La liste des comptes est en cours de chargement. */
  loading?: boolean
  unavailable: string[]
  unavailableLabel: string
}) {
  const id = useId()
  const listId = `${id}-liste`
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [typingError, setTypingError] = useState<string | null>(null)

  const search = query.trim().replace(/^@/, '').toLowerCase()
  const options = useMemo<Option[]>(() => {
    const matches = suggestions
      .filter((suggestion) => suggestion.author.includes(search))
      .sort((a, b) => Number(b.author.startsWith(search)) - Number(a.author.startsWith(search)))
      .slice(0, MAX_SHOWN)
      .map<Option>((suggestion) => ({
        author: suggestion.author,
        likes: suggestion.likes,
        blockedBy: unavailable.includes(suggestion.author) ? unavailableLabel : undefined,
      }))
    const typed = normalizeAuthor(query)
    if (typed && !suggestions.some((suggestion) => suggestion.author === typed)) {
      matches.unshift({ author: typed, likes: null })
    }
    return matches
  }, [query, search, suggestions, unavailable, unavailableLabel])

  const total = suggestions.filter((suggestion) => suggestion.author.includes(search)).length

  const toggle = (option: Option) => {
    if (option.blockedBy) return
    onChange(
      value.includes(option.author)
        ? value.filter((author) => author !== option.author)
        : [...value, option.author],
    )
    setQuery('')
    setTypingError(null)
    inputRef.current?.focus()
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      setOpen(true)
      const step = event.key === 'ArrowDown' ? 1 : -1
      setActive((index) => Math.max(0, Math.min(options.length - 1, index + step)))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const option = open ? options[active] : undefined
      if (option) toggle(option)
      else if (query.trim())
        setTypingError(`« ${query.trim()} » n’est pas un nom de compte valide.`)
    } else if (event.key === 'Escape') {
      setOpen(false)
    } else if (event.key === 'Backspace' && !query && value.length) {
      onChange(value.slice(0, -1))
    }
  }

  const message = typingError ?? error
  const describedBy = [`${id}-aide`, message && `${id}-erreur`].filter(Boolean).join(' ')
  const activeOption = open ? options[active] : undefined
  return (
    <div>
      <label htmlFor={id} className="block text-small font-medium text-fg">
        {label}
      </label>
      <p id={`${id}-aide`} className="mt-1 text-small text-fg-muted">
        {help}
      </p>

      {value.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label={`${label} : comptes choisis`}>
          {value.map((author) => (
            <li
              key={author}
              className="inline-flex min-h-8 animate-pop items-center gap-1 rounded-full bg-primary-soft py-1 pr-1 pl-3 text-small font-medium text-primary-strong"
            >
              @{author}
              <button
                type="button"
                onClick={() => onChange(value.filter((item) => item !== author))}
                aria-label={`Retirer @${author}`}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full transition-colors hover:bg-primary-soft-hover"
              >
                <CloseIcon className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div
        className="relative mt-3"
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false)
        }}
      >
        <SearchIcon className="pointer-events-none absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-fg-subtle" />
        <input
          ref={inputRef}
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeOption ? `${id}-${activeOption.author}` : undefined}
          aria-describedby={describedBy}
          aria-invalid={message ? true : undefined}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setActive(0)
            setOpen(true)
            setTypingError(null)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder={suggestions.length ? 'Rechercher un compte' : '@compte'}
          autoComplete="off"
          className="input pr-12 pl-12"
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => {
            setOpen((value) => !value)
            inputRef.current?.focus()
          }}
          aria-label={open ? 'Masquer la liste des comptes' : 'Afficher la liste des comptes'}
          className="absolute top-0 right-0 flex h-11 w-11 items-center justify-center text-fg-muted"
        >
          <ChevronDownIcon
            className={`h-5 w-5 transition-transform duration-component ${open ? 'rotate-180' : ''}`}
          />
        </button>

        {open && (
          <div className="popover absolute z-30 mt-2 w-full overflow-hidden">
            <p className="flex items-center gap-2 border-b border-border px-4 py-2 text-caption text-fg-muted">
              {loading ? (
                <>
                  <Spinner className="h-3 w-3" />
                  Chargement de tes comptes…
                </>
              ) : suggestions.length ? (
                `${plural(total, 'compte trouvé', 'comptes trouvés')} dans tes likes${
                  total > MAX_SHOWN ? ', affine ta recherche pour voir les autres' : ''
                }`
              ) : (
                'La liste de tes comptes apparaîtra après un premier aperçu. Tu peux déjà saisir un nom.'
              )}
            </p>
            <ul
              id={listId}
              role="listbox"
              aria-label={label}
              aria-multiselectable="true"
              className="max-h-72 overflow-y-auto py-1"
            >
              {options.map((option, index) => {
                const selected = value.includes(option.author)
                return (
                  <li
                    key={option.author}
                    id={`${id}-${option.author}`}
                    role="option"
                    aria-selected={selected}
                    aria-disabled={option.blockedBy ? true : undefined}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => toggle(option)}
                    onMouseEnter={() => setActive(index)}
                    className={`flex min-h-11 cursor-pointer items-center gap-3 px-4 text-small transition-colors ${
                      index === active ? 'bg-fill' : ''
                    } ${option.blockedBy ? 'cursor-not-allowed opacity-50' : ''}`}
                  >
                    <span aria-hidden="true" className="checkbox" data-checked={selected} />
                    <span className="flex-1 truncate font-medium">
                      {option.likes === null ? `Ajouter @${option.author}` : `@${option.author}`}
                    </span>
                    <span className="text-caption text-fg-muted tabular-nums">
                      {option.blockedBy ?? (option.likes !== null && plural(option.likes, 'like'))}
                    </span>
                  </li>
                )
              })}
              {options.length === 0 && (
                <li className="px-4 py-3 text-small text-fg-muted">Aucun compte ne correspond.</li>
              )}
            </ul>
          </div>
        )}
      </div>
      {message && (
        <FieldMessage id={`${id}-erreur`} tone="error">
          {message}
        </FieldMessage>
      )}
    </div>
  )
}
