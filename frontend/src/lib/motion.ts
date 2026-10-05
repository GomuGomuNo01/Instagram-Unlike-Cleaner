// Système de motion, côté script. Les durées, courbes et amplitudes vivent dans les tokens CSS
// (styles/tokens.css) ; ce module ne fait que déclencher les états (apparition, présence,
// position du curseur) et respecter les préférences de l'appareil.
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
} from 'react'

// --- Préférences de l'appareil ---------------------------------------------------------------

const REDUCED_MOTION = '(prefers-reduced-motion: reduce)'
const FINE_POINTER = '(hover: hover) and (pointer: fine)'

function mediaQuery(query: string): MediaQueryList | null {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia(query)
    : null
}

export function prefersReducedMotion(): boolean {
  return mediaQuery(REDUCED_MOTION)?.matches ?? false
}

/** Effets liés au curseur (parallaxe, halo, attraction) : souris et mouvement autorisé. */
export function pointerEffectsEnabled(): boolean {
  return (mediaQuery(FINE_POINTER)?.matches ?? false) && !prefersReducedMotion()
}

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = mediaQuery(query)
      list?.addEventListener('change', onChange)
      return () => list?.removeEventListener('change', onChange)
    },
    () => mediaQuery(query)?.matches ?? false,
    () => false,
  )
}

export const useReducedMotion = () => useMediaQuery(REDUCED_MOTION)

export type MotionToken = 'micro' | 'hover' | 'component' | 'page' | 'complex'

/** Durée d'un token de motion en millisecondes, lue dans le CSS (0 s'il n'est pas chargé). */
export function motionDuration(token: MotionToken): number {
  if (typeof document === 'undefined') return 0
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(`--transition-duration-${token}`)
    .trim()
  const amount = Number.parseFloat(value)
  if (!Number.isFinite(amount)) return 0
  return value.endsWith('ms') ? amount : amount * 1000
}

/** Active les apparitions au défilement. Sans IntersectionObserver ou en mouvement réduit,
 * rien n'est jamais masqué : le contenu s'affiche directement. */
export function initMotion(): void {
  if (typeof IntersectionObserver === 'undefined' || prefersReducedMotion()) return
  document.documentElement.classList.add('motion-ready')
}

// --- Apparition au défilement ---------------------------------------------------------------

export type RevealVariant = 'up' | 'fade' | 'scale'

let revealObserver: IntersectionObserver | null | undefined

function getRevealObserver(): IntersectionObserver | null {
  if (revealObserver !== undefined) return revealObserver
  revealObserver =
    typeof IntersectionObserver === 'undefined'
      ? null
      : new IntersectionObserver(
          (entries, observer) => {
            for (const entry of entries) {
              if (!entry.isIntersecting) continue
              ;(entry.target as HTMLElement).dataset.revealed = ''
              observer.unobserve(entry.target)
            }
          },
          { rootMargin: '0px 0px -8% 0px' },
        )
  return revealObserver
}

// Une seule observation partagée par tous les éléments : aucun calcul au défilement.
function observeReveal(element: HTMLElement | null) {
  if (!element) return
  const observer = getRevealObserver()
  if (!observer) {
    element.dataset.revealed = ''
    return
  }
  observer.observe(element)
  return () => observer.unobserve(element)
}

/** Propriétés à poser sur un élément pour le faire apparaître à son entrée dans l'écran.
 * `order` donne sa place dans la séquence : 0 pour le titre, 1 pour la description… */
export function reveal(order = 0, variant: RevealVariant = 'up') {
  return {
    ref: observeReveal,
    'data-reveal': variant,
    style: { '--reveal-order': Math.min(order, 8) } as CSSProperties,
  }
}

// --- Présence : garder un élément le temps de son animation de sortie ------------------------

export function usePresence(open: boolean, exit: MotionToken = 'micro') {
  const [previous, setPrevious] = useState(open)
  const [closing, setClosing] = useState(false)
  if (open !== previous) {
    setPrevious(open)
    setClosing(!open)
  }

  useEffect(() => {
    if (!closing) return
    const timer = window.setTimeout(() => setClosing(false), motionDuration(exit))
    return () => window.clearTimeout(timer)
  }, [closing, exit])

  return { mounted: open || closing, state: open ? ('open' as const) : ('closed' as const) }
}

/** Bloque le défilement de la page (menu mobile, fenêtre modale). */
export function useScrollLock(active: boolean): void {
  useEffect(() => {
    if (!active) return
    const root = document.documentElement
    const previous = root.style.overflow
    root.style.overflow = 'hidden'
    return () => {
      root.style.overflow = previous
    }
  }, [active])
}

// --- Défilement -----------------------------------------------------------------------------

function subscribeScroll(onChange: () => void) {
  window.addEventListener('scroll', onChange, { passive: true })
  return () => window.removeEventListener('scroll', onChange)
}

/** Vrai dès que la page a défilé de quelques pixels (en-tête compact). */
export function useScrolled(threshold = 8): boolean {
  return useSyncExternalStore(
    subscribeScroll,
    () => window.scrollY > threshold,
    () => false,
  )
}

/** Identifiant de la section affichée au milieu de l'écran, parmi `ids` (menu de la page
 * d'accueil). */
export function useSectionSpy(ids: readonly string[]): string | null {
  const [current, setCurrent] = useState<string | null>(null)
  const key = ids.join(' ')

  useEffect(() => {
    if (!key || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setCurrent(entry.target.id)
          else setCurrent((value) => (value === entry.target.id ? null : value))
        }
      },
      { rootMargin: '-45% 0px -50% 0px' },
    )
    for (const id of key.split(' ')) {
      const section = document.getElementById(id)
      if (section) observer.observe(section)
    }
    return () => observer.disconnect()
  }, [key])

  return key ? current : null
}

/** Étape active d'un récit au défilement : celle qui traverse le milieu de l'écran. */
export function useActiveStep() {
  const [active, setActive] = useState(0)
  const elements = useRef<HTMLElement[]>([])

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(elements.current.indexOf(entry.target as HTMLElement))
        }
      },
      { rootMargin: '-45% 0px -45% 0px' },
    )
    elements.current.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [])

  const register = useCallback(
    (index: number) => (element: HTMLElement | null) => {
      if (element) elements.current[index] = element
    },
    [],
  )

  return { active, register }
}

// --- Curseur (bureau uniquement) -------------------------------------------------------------
// Ces fonctions sont des « ref callbacks » : elles s'attachent à un élément et renvoient leur
// nettoyage. Elles ne déclenchent aucun rendu React : seules des variables CSS changent, au
// plus une fois par image.

function trackPointer(
  element: HTMLElement,
  onMove: (event: PointerEvent, rect: DOMRect) => void,
  onLeave: () => void,
) {
  let frame = 0
  let last: PointerEvent | null = null
  const apply = () => {
    frame = 0
    if (last) onMove(last, element.getBoundingClientRect())
  }
  const move = (event: PointerEvent) => {
    if (event.pointerType !== 'mouse' || !pointerEffectsEnabled()) return
    last = event
    if (!frame) frame = requestAnimationFrame(apply)
  }
  const leave = () => {
    last = null
    onLeave()
  }
  element.addEventListener('pointermove', move, { passive: true })
  element.addEventListener('pointerleave', leave)
  return () => {
    cancelAnimationFrame(frame)
    element.removeEventListener('pointermove', move)
    element.removeEventListener('pointerleave', leave)
  }
}

const clamp = (value: number) => Math.max(-1, Math.min(1, value))

/** Pose `--px`/`--py` (position du curseur, de -1 à 1 depuis le centre) et `--gx`/`--gy`
 * (en pixels) sur l'élément : calques en profondeur ([data-depth]) et halo qui suit. */
export function pointerField(element: HTMLElement | null) {
  if (!element) return
  return trackPointer(
    element,
    (event, rect) => {
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top
      element.style.setProperty('--px', clamp((x / rect.width) * 2 - 1).toFixed(3))
      element.style.setProperty('--py', clamp((y / rect.height) * 2 - 1).toFixed(3))
      element.style.setProperty('--gx', `${Math.round(x)}px`)
      element.style.setProperty('--gy', `${Math.round(y)}px`)
    },
    () => {
      element.style.setProperty('--px', '0')
      element.style.setProperty('--py', '0')
    },
  )
}

/** Halo qui suit le curseur dans les cartes `.spotlight` d'un conteneur. */
export function spotlight(container: HTMLElement | null) {
  if (!container) return
  return trackPointer(
    container,
    (event) => {
      const card = (event.target as Element | null)?.closest<HTMLElement>('.spotlight')
      if (!card) return
      const rect = card.getBoundingClientRect()
      card.style.setProperty('--mx', `${Math.round(event.clientX - rect.left)}px`)
      card.style.setProperty('--my', `${Math.round(event.clientY - rect.top)}px`)
    },
    () => {},
  )
}

/** Attraction très légère d'un bouton vers le curseur (l'élément porte la classe `.magnetic`). */
export function magnetic(element: HTMLElement | null) {
  if (!element) return
  return trackPointer(
    element,
    (event, rect) => {
      const max = Number.parseFloat(getComputedStyle(element).getPropertyValue('--magnet-max'))
      if (!max) return
      const dx = clamp((event.clientX - rect.left) / (rect.width / 2) - 1)
      const dy = clamp((event.clientY - rect.top) / (rect.height / 2) - 1)
      element.style.setProperty('--magnet-x', `${(dx * max).toFixed(2)}px`)
      element.style.setProperty('--magnet-y', `${(dy * max).toFixed(2)}px`)
    },
    () => {
      element.style.setProperty('--magnet-x', '0px')
      element.style.setProperty('--magnet-y', '0px')
    },
  )
}
