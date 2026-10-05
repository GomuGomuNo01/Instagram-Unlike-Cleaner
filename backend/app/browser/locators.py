"""Adresses, cookies et sélecteurs Instagram, centralisés pour absorber les changements d'interface.

Tout ce qui dépend du HTML d'Instagram doit passer par ce module. Les textes sont donnés en
français et en anglais, car la langue de l'interface suit le réglage du compte.

Les éléments marqués « confirmé » ont été observés sur l'interface web française
(diagnostics `iuc login --snapshot` et `iuc probe` d'octobre 2026). Les autres, dont toutes
les variantes anglaises, restent à vérifier.

Le module s'appelle `locators` et non `selectors` pour ne pas masquer le module standard.
"""

import re
from enum import StrEnum

from playwright.async_api import Locator, Page

BASE_URL = "https://www.instagram.com"
HOME_URL = f"{BASE_URL}/"
LIKES_PATH = "/your_activity/interactions/likes/"  # confirmé
LIKES_URL = f"{BASE_URL}{LIKES_PATH}"

# On ne teste que la présence de ces cookies : leur valeur n'est jamais lue ni journalisée,
# sauf l'identifiant numérique du compte.
SESSION_COOKIE = "sessionid"
ACCOUNT_ID_COOKIE = "ds_user_id"

_LOGIN_PATH = re.compile(r"^/accounts/login(/|$)")
_CHALLENGE_PATH = re.compile(r"^/(challenge|checkpoint|accounts/suspended|accounts/disabled)(/|$)")
# Écran Meta « s'abonner ou continuer avec des publicités » : confirmé.
_CONSENT_PATH = re.compile(r"^/consent(/|$)")


class PageKind(StrEnum):
    """Nature d'une page Instagram. Les valeurs servent aussi dans les journaux, à la place
    de l'adresse, qui peut contenir le nom d'un compte."""

    HOME = "accueil"
    LIKES = "page des likes"
    LOGIN = "connexion"
    CHALLENGE = "vérification de sécurité"
    CONSENT = "consentement"
    OTHER = "autre page"


def classify_path(path: str) -> PageKind:
    if _LOGIN_PATH.match(path):
        return PageKind.LOGIN
    if _CHALLENGE_PATH.match(path):
        return PageKind.CHALLENGE
    if _CONSENT_PATH.match(path):
        return PageKind.CONSENT
    normalized = path.rstrip("/")
    if normalized == "":
        return PageKind.HOME
    if normalized == LIKES_PATH.rstrip("/"):
        return PageKind.LIKES
    return PageKind.OTHER


# --- Page des likes ---------------------------------------------------------------------

# « Sélectionner » est un simple texte cliquable, pas un bouton : confirmé.
_SELECT_TEXT = re.compile(r"^\s*(Sélectionner|Select)\s*$")
# « Trier et filtrer » est un bouton : confirmé.
_SORT_AND_FILTER_NAME = re.compile(r"^\s*(Trier et filtrer|Sort (&|and) filter)\s*$")

# Libellé d'une vignette, confirmé en français :
#   « Vidéo, 2 sur 18, de @auteur, partagée le October 3, 2026 »
#   « Carrousel avec 4 éléments, 1 sur 18, de @auteur, partagée le September 26, 2026 »
# Type : Photo, Vidéo (Reels compris) ou « Carrousel avec N éléments », avec une espace
# insécable avant « éléments ». La date est celle de la publication, pas celle du like, et
# le mois reste en anglais. La numérotation « x sur N » repart à 1 à chaque paquet de
# vignettes chargé (18 par paquet) : elle ne sert pas d'identifiant.
_KIND = r"Photo|Vidéo|Video|Carrousel\s+avec\s+\d+\s+éléments|Carousel\s+with\s+\d+\s+items"
_POSITION = r"\d+\s+(?:sur|of)\s+\d+"
_AUTHOR = r"[A-Za-z0-9._]+"

# Version sans groupe nommé : Playwright la transmet telle quelle au navigateur, en JavaScript.
THUMBNAIL_LABEL = re.compile(rf"^(?:{_KIND}),\s+{_POSITION},\s+(?:de|by)\s+@{_AUTHOR}")
# Version découpée, utilisée côté Python pour lire le libellé.
THUMBNAIL_LABEL_PARTS = re.compile(
    rf"^(?P<kind>{_KIND}),\s+{_POSITION},\s+(?:de|by)\s+@(?P<author>{_AUTHOR})"
    r"(?:,\s+(?:partagée\s+le|shared\s+on)\s+(?P<published>.+))?$"
)

# Vignette = bouton portant un libellé, qui n'est pas lui-même dans un tel bouton : en mode
# sélection, chaque vignette contient un second bouton au même libellé (confirmé).
_OUTERMOST_LABELED_BUTTON = (
    "xpath=//*[@role='button' and @aria-label][not(ancestor::*[@role='button' and @aria-label])]"
)

# Lit toutes les vignettes affichées en un seul aller-retour avec le navigateur : libellé,
# adresse de l'image et icônes superposées (carrousel, case cochée...). Les icônes sont des
# images de masque dont le nom de fichier décrit l'icône, par exemple
# « .../icons/generated/carousel__filled__32-4x.png » (confirmé).
READ_THUMBNAILS_JS = """
() => {
  const labeled = '[role="button"][aria-label]';
  const thumbnails = [];
  for (const element of document.querySelectorAll(labeled)) {
    if (element.parentElement && element.parentElement.closest(labeled)) continue;
    const image = element.querySelector('img[src]');
    const icons = [];
    for (const node of element.querySelectorAll('[style*="mask-image"]')) {
      const match = (node.getAttribute('style') || '').match(/icons\\/generated\\/(.+?)-\\d+x\\./);
      if (match) icons.push(match[1]);
    }
    thumbnails.push({
      label: element.getAttribute('aria-label'),
      src: image ? image.getAttribute('src') : null,
      icons,
    });
  }
  return thumbnails;
}
"""

# Icône de la case cochée en mode sélection (confirmé) ; non cochée : « circle__outline__24 ».
CHECKED_ICON = re.compile(r"^circle-check__")


def likes_page_marker(page: Page) -> Locator:
    """Élément qui prouve que la page des likes est chargée et a la structure attendue."""
    return sort_and_filter_button(page).or_(select_toggle(page)).first


def sort_and_filter_button(page: Page) -> Locator:
    return page.get_by_role("button", name=_SORT_AND_FILTER_NAME).first


def select_toggle(page: Page) -> Locator:
    """Texte « Sélectionner » qui fait passer la grille en mode sélection."""
    return page.get_by_text(_SELECT_TEXT).first


def thumbnails(page: Page) -> Locator:
    """Vignettes des publications aimées, dans l'ordre de la grille, sans doublon."""
    return page.get_by_role("button", name=THUMBNAIL_LABEL).and_(
        page.locator(_OUTERMOST_LABELED_BUTTON)
    )


def loading_indicator(page: Page) -> Locator:
    """Indicateur « Chargement... » placé après la dernière vignette tant qu'il en reste."""
    return page.get_by_role("progressbar").first


def blocking_dialog(page: Page) -> Locator:
    """Fenêtre d'Instagram ouverte par-dessus la page, par exemple « Enregistrer vos
    informations de connexion ? » après une connexion (confirmé)."""
    return page.get_by_role("dialog").first


# --- Panneau « Trier et filtrer » (confirmé) ----------------------------------------------
# Tri, puis date de début et date de fin, chacune en trois listes déroulantes : mois en
# toutes lettres (janvier en premier), jour de 1 à 31, année de l'année en cours à 1919.
# « Appliquer » reste grisé tant que rien n'a changé. Aucun filtre par auteur ni par type.

_SORT_BY_TEXT = re.compile(r"(Trier par|Sort by)")
_NEWEST_FIRST_NAME = re.compile(r"^\s*(Du plus récent au plus ancien|Newest to oldest)\s*$")
_OLDEST_FIRST_NAME = re.compile(r"^\s*(Du plus ancien au plus récent|Oldest to newest)\s*$")
_MONTH_NAME = re.compile(r"^\s*(Mois|Month)")
_DAY_NAME = re.compile(r"^\s*(Jour|Day)")
_YEAR_NAME = re.compile(r"^\s*(Année|Year)")
_APPLY_NAME = re.compile(r"^\s*(Appliquer|Apply)\s*$")


def filters_dialog(page: Page) -> Locator:
    return page.get_by_role("dialog").filter(has_text=_SORT_BY_TEXT).first


def sort_button(dialog: Locator, *, newest_first: bool) -> Locator:
    name = _NEWEST_FIRST_NAME if newest_first else _OLDEST_FIRST_NAME
    return dialog.get_by_role("button", name=name).first


def date_selects(dialog: Locator, position: int) -> tuple[Locator, Locator, Locator]:
    """Listes mois, jour et année de la date de début (0) ou de fin (1)."""
    return (
        dialog.get_by_role("combobox", name=_MONTH_NAME).nth(position),
        dialog.get_by_role("combobox", name=_DAY_NAME).nth(position),
        dialog.get_by_role("combobox", name=_YEAR_NAME).nth(position),
    )


def apply_button(dialog: Locator) -> Locator:
    return dialog.get_by_role("button", name=_APPLY_NAME).first
