import type { ComponentProps } from 'react'
import { Link, type To } from 'react-router'

function isAnchor(to: To): boolean {
  return typeof to === 'string' ? to.includes('#') : Boolean(to.hash)
}

/** Lien interne. Changer d'écran déclenche la transition animée ; une ancre de la page
 * courante défile simplement jusqu'à sa section. */
export function AppLink({ viewTransition, ...props }: ComponentProps<typeof Link>) {
  return <Link viewTransition={viewTransition ?? !isAnchor(props.to)} {...props} />
}

/** Lien dans un texte : souligné, couleur principale. */
export function TextLink({ className = '', ...props }: ComponentProps<typeof Link>) {
  return <AppLink className={`link ${className}`} {...props} />
}
