import { useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router'

import { CloseIcon, MenuIcon } from './icons'
import { navigation } from './navigation'
import { ThemeToggle } from './ThemeToggle'
import { ButtonLink } from './ui'

export function Logo() {
  return (
    <Link to="/" className="flex min-h-11 items-center gap-3 rounded-lg font-semibold">
      <img src="/favicon.svg" alt="" className="h-8 w-8" width={32} height={32} />
      <span>
        IUC <span className="sr-only">: retour à l’accueil</span>
      </span>
    </Link>
  )
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? 'text-indigo-700 dark:text-indigo-300'
      : 'text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:hover:text-white'
  }`

/** En-tête fixe : logo, menu essentiel, thème et action principale ; menu tactile sur mobile. */
export function Header() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const close = () => setOpen(false)
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/90 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Logo />
        <nav aria-label="Navigation principale" className="ml-6 hidden items-center gap-1 md:flex">
          {navigation.map((item) =>
            // Les ancres de l'accueil ne sont pas des pages : pas d'état « actif » trompeur.
            item.to.includes('#') ? (
              <Link key={item.to} to={item.to} className={linkClass({ isActive: false })}>
                {item.label}
              </Link>
            ) : (
              <NavLink key={item.to} to={item.to} className={linkClass}>
                {item.label}
              </NavLink>
            ),
          )}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <ButtonLink to="/commencer" className="hidden md:inline-flex">
            Commencer
          </ButtonLink>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls="menu-mobile"
            aria-label={open ? 'Fermer le menu' : 'Ouvrir le menu'}
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-zinc-700 hover:bg-zinc-100 active:bg-zinc-200 md:hidden dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {open && (
        <nav
          id="menu-mobile"
          aria-label="Menu"
          className="border-t border-zinc-200 px-4 pt-2 pb-6 md:hidden dark:border-zinc-800"
        >
          <ul className="flex flex-col">
            {navigation.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  onClick={close}
                  className="flex min-h-12 items-center rounded-lg px-3 text-base font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <ButtonLink to="/commencer" onClick={close} size="lg" className="mt-4 w-full">
            Commencer le nettoyage
          </ButtonLink>
        </nav>
      )}
    </header>
  )
}
