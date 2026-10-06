import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { NavLink, useLocation } from 'react-router'

import { useScrollLock, useScrolled, useSectionSpy } from '../lib/motion'
import { ArrowRightIcon, CloseIcon, DownloadIcon, MenuIcon } from './icons'
import { jobsLink, presentationLink, sectionIds, sections, WINDOWS_DOWNLOAD } from './navigation'
import { ThemeToggle } from './ThemeToggle'
import { AppLink, ButtonLink } from './ui'

export function Logo() {
  return (
    <AppLink
      to="/"
      className="group inline-flex min-h-11 items-center gap-3 rounded-full font-semibold text-fg"
    >
      <img
        src={`${import.meta.env.BASE_URL}favicon.svg`}
        alt=""
        width={32}
        height={32}
        className="h-8 w-8 transition-transform duration-component ease-emphasized motion-safe:group-hover:-rotate-6 motion-safe:group-hover:scale-105"
      />
      <span className="text-body tracking-tight">
        IUC <span className="sr-only">: retour à l’accueil</span>
      </span>
    </AppLink>
  )
}

const mobileItems = [
  presentationLink,
  ...sections.map((s) => ({ to: `/#${s.id}`, label: s.label })),
  jobsLink,
]

// Démo en ligne : téléchargement de la vraie version, mis en avant dans la navigation.
const DEMO = import.meta.env.VITE_DEMO === 'true'
const DOWNLOAD_LABEL = 'Télécharger pour Windows'

/** En-tête : logo, menu limité aux sections utiles, thème et action principale. Intégré à
 * la page en haut, il prend un fond translucide dès que la page défile. Sur mobile, un menu
 * plein écran aux grandes cibles tactiles. */
export function Header() {
  const { pathname } = useLocation()
  const scrolled = useScrolled()
  const current = useSectionSpy(pathname === '/' ? sectionIds : [])
  const [open, setOpen] = useState(false)
  const [lastPath, setLastPath] = useState(pathname)
  const toggleRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLElement>(null)
  useScrollLock(open)

  // Un changement d'écran referme le menu.
  if (pathname !== lastPath) {
    setLastPath(pathname)
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return
    menuRef.current?.querySelector<HTMLElement>('a')?.focus()
    // Le reste de la page devient inactif tant que le menu le recouvre.
    const covered = [...document.querySelectorAll<HTMLElement>('main, footer')]
    covered.forEach((element) => (element.inert = true))
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setOpen(false)
      toggleRef.current?.focus()
    }
    window.addEventListener('keydown', onKey)
    return () => {
      covered.forEach((element) => (element.inert = false))
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const close = () => setOpen(false)
  return (
    <>
      <header
        className="site-header"
        data-scrolled={scrolled || undefined}
        data-menu-open={open || undefined}
      >
        <div className="mx-auto flex h-16 w-full max-w-page items-center gap-4 px-4 sm:px-6 lg:px-8">
          <Logo />
          <nav
            aria-label="Navigation principale"
            className="ml-6 hidden items-center gap-1 lg:flex xl:ml-8"
          >
            <NavLink to={presentationLink.to} viewTransition className="nav-link whitespace-nowrap">
              {presentationLink.label}
            </NavLink>
            {sections.map((section) => (
              <AppLink
                key={section.id}
                to={`/#${section.id}`}
                aria-current={current === section.id ? 'location' : undefined}
                className="nav-link"
              >
                {section.label}
              </AppLink>
            ))}
            {DEMO && (
              <a
                href={WINDOWS_DOWNLOAD}
                download
                aria-label={DOWNLOAD_LABEL}
                title={DOWNLOAD_LABEL}
                className="ml-2 inline-flex min-h-9 shrink-0 items-center gap-2 rounded-full border border-primary bg-primary-soft px-3 text-small font-semibold whitespace-nowrap text-primary-strong transition-colors hover:bg-primary-soft-hover xl:ml-3 xl:px-4"
              >
                <DownloadIcon className="h-4 w-4" />
                {/* Icône seule sur les écrans moyens, pour que la barre tienne sur une ligne. */}
                <span className="hidden xl:inline">{DOWNLOAD_LABEL}</span>
              </a>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <NavLink
              to={jobsLink.to}
              viewTransition
              className="nav-link hidden whitespace-nowrap lg:inline-flex"
            >
              {jobsLink.label}
            </NavLink>
            <ThemeToggle />
            <ButtonLink to="/commencer" className="hidden sm:inline-flex">
              Commencer
            </ButtonLink>
            <button
              ref={toggleRef}
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              aria-controls="menu-mobile"
              aria-label={open ? 'Fermer le menu' : 'Ouvrir le menu'}
              className="menu-toggle btn btn-ghost btn-icon lg:hidden"
            >
              <MenuIcon data-icon="menu" />
              <CloseIcon data-icon="close" />
            </button>
          </div>
        </div>
      </header>

      <nav
        ref={menuRef}
        id="menu-mobile"
        aria-label="Menu"
        data-open={open || undefined}
        inert={!open}
        className="mobile-menu lg:hidden"
      >
        <ul className="flex flex-col gap-1">
          {mobileItems.map((item, index) => (
            <li
              key={item.to}
              className="mobile-menu-item"
              style={{ '--i': index } as CSSProperties}
            >
              <AppLink
                to={item.to}
                onClick={close}
                className="flex min-h-14 items-center justify-between gap-4 rounded-lg px-3 text-h3 transition-colors hover:bg-fill"
              >
                {item.label}
                <ArrowRightIcon className="h-5 w-5 text-fg-subtle" />
              </AppLink>
            </li>
          ))}
        </ul>
        <div
          className="mobile-menu-item mt-8"
          style={{ '--i': mobileItems.length } as CSSProperties}
        >
          <ButtonLink to="/commencer" onClick={close} size="lg" className="w-full">
            Commencer le nettoyage
          </ButtonLink>
          {DEMO && (
            <a
              href={WINDOWS_DOWNLOAD}
              download
              onClick={close}
              className="btn btn-secondary btn-lg mt-3 w-full"
            >
              <DownloadIcon className="h-5 w-5" />
              {DOWNLOAD_LABEL}
            </a>
          )}
        </div>
      </nav>
    </>
  )
}
