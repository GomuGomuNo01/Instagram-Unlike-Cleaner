/** Tonalité stable d'une pastille d'initiales, déduite du nom du compte. */
function avatarTone(author: string): string {
  let sum = 0
  for (const char of author) sum += char.charCodeAt(0)
  return String(sum % 4)
}

/** Pastille d'initiales d'un compte (décorative : le nom est toujours écrit à côté). */
export function Avatar({ author }: { author: string | null }) {
  return (
    <span aria-hidden="true" className="avatar" data-tone={author ? avatarTone(author) : '0'}>
      {author ? author.replace(/[^a-z0-9]/gi, '').slice(0, 2) || '?' : '?'}
    </span>
  )
}
