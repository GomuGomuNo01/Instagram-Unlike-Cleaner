import { useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import type { Author } from '../api/types'
import { normalizeAuthor } from '../lib/filters'
import { plural } from '../lib/format'
import { CheckIcon, ChevronDownIcon, CloseIcon, SearchIcon } from './icons'
import { inputClass } from './ui'

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
  unavailable,
  unavailableLabel,
}: {
  label: string
  help: string
  error?: string
  value: string[]
  onChange: (authors: string[]) => void
  suggestions: Author[]
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

  const options = useMemo<Option[]>(() => {
    const search = query.trim().replace(/^@/, '').toLowerCase()
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
  }, [query, suggestions, unavailable, unavailableLabel])

  const total = suggestions.filter((suggestion) =>
    suggestion.author.includes(query.trim().replace(/^@/, '').toLowerCase()),
  ).length

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

  const describedBy = [`${id}-aide`, (error || typingError) && `${id}-erreur`]
    .filter(Boolean)
    .join(' ')
  const activeOption = open ? options[active] : undefined
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <p id={`${id}-aide`} className="text-small mt-1">
        {help}
      </p>

      {value.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label={`${label} : comptes choisis`}>
          {value.map((author) => (
            <li
              key={author}
              className="inline-flex min-h-9 items-center gap-1 rounded-full bg-indigo-50 py-1 pr-1 pl-3 text-sm font-medium text-indigo-900 dark:bg-indigo-950 dark:text-indigo-100"
            >
              @{author}
              <button
                type="button"
                onClick={() => onChange(value.filter((item) => item !== author))}
                aria-label={`Retirer @${author}`}
                className="inline-flex h-7 w-7 items-center justify-center rounded-full hover:bg-indigo-200 dark:hover:bg-indigo-800"
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
        <SearchIcon className="pointer-events-none absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-zinc-500" />
        <input
          ref={inputRef}
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={activeOption ? `${id}-${activeOption.author}` : undefined}
          aria-describedby={describedBy}
          aria-invalid={error || typingError ? true : undefined}
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
          className={`${inputClass} pr-12 pl-10`}
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => {
            setOpen((value) => !value)
            inputRef.current?.focus()
          }}
          aria-label={open ? 'Masquer la liste des comptes' : 'Afficher la liste des comptes'}
          className="absolute top-0 right-0 flex h-11 w-11 items-center justify-center text-zinc-600 dark:text-zinc-400"
        >
          <ChevronDownIcon className={`h-5 w-5 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>

        {open && (
          <div className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
            <p className="border-b border-zinc-200 px-4 py-2 text-xs text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
              {suggestions.length
                ? `${plural(total, 'compte trouvé', 'comptes trouvés')} dans tes likes`
                : 'La liste de tes comptes apparaîtra après un premier aperçu. Tu peux déjà saisir un nom.'}
              {total > MAX_SHOWN && `, affine ta recherche pour voir les autres`}
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
                    className={`flex min-h-11 cursor-pointer items-center gap-3 px-4 text-sm ${
                      index === active ? 'bg-zinc-100 dark:bg-zinc-800' : ''
                    } ${option.blockedBy ? 'cursor-not-allowed opacity-60' : ''}`}
                  >
                    <span
                      aria-hidden="true"
                      className={`flex h-5 w-5 items-center justify-center rounded border ${
                        selected
                          ? 'border-indigo-600 bg-indigo-600 text-white'
                          : 'border-zinc-400 dark:border-zinc-600'
                      }`}
                    >
                      {selected && <CheckIcon className="h-4 w-4" />}
                    </span>
                    <span className="flex-1 truncate font-medium">
                      {option.likes === null ? `Ajouter @${option.author}` : `@${option.author}`}
                    </span>
                    <span className="text-xs text-zinc-600 dark:text-zinc-400">
                      {option.blockedBy ?? (option.likes !== null && plural(option.likes, 'like'))}
                    </span>
                  </li>
                )
              })}
              {options.length === 0 && (
                <li className="px-4 py-3 text-sm text-zinc-600 dark:text-zinc-400">
                  Aucun compte ne correspond.
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
      {(error || typingError) && (
        <p id={`${id}-erreur`} className="mt-2 text-sm font-medium text-red-700 dark:text-red-400">
          {typingError ?? error}
        </p>
      )}
    </div>
  )
}
