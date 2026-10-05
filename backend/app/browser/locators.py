"""Adresses, cookies et sélecteurs Instagram, centralisés pour absorber les changements d'interface.

Tout ce qui dépend du HTML d'Instagram doit passer par ce module. Les textes sont donnés en
français et en anglais, car la langue de l'interface suit le réglage du compte.

Les éléments marqués « confirmé » ont été observés sur l'interface web française
(diagnostics `iuc login --snapshot` d'octobre 2026). Les autres, dont toutes les variantes
anglaises, restent à vérifier avec `iuc probe`.

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


# « Sélectionner » est un simple texte cliquable, pas un bouton : confirmé.
_SELECT_TEXT = re.compile(r"^\s*(Sélectionner|Select)\s*$")
# « Trier et filtrer » est un bouton : confirmé.
_SORT_AND_FILTER_NAME = re.compile(r"^\s*(Trier et filtrer|Sort (&|and) filter)\s*$")

# Libellé d'une vignette, confirmé en français :
#   « Vidéo, 2 sur 18, de @auteur, partagée le October 3, 2026 »
# Type : Photo, Vidéo (Reels compris) ou « Carrousel avec N éléments ». La date est celle de
# la publication, pas celle du like, et le mois reste en anglais. Vignettes sans lien /p/.
THUMBNAIL_LABEL = re.compile(
    r"^(Photo|Vidéo|Video|Carrousel avec \d+ éléments|Carousel with \d+ items), "
    r"\d+ (sur|of) \d+, (de|by) @"
)


def likes_page_marker(page: Page) -> Locator:
    """Élément qui prouve que la page des likes est chargée et a la structure attendue."""
    return sort_and_filter_button(page).or_(select_toggle(page)).first


def sort_and_filter_button(page: Page) -> Locator:
    return page.get_by_role("button", name=_SORT_AND_FILTER_NAME).first


def select_toggle(page: Page) -> Locator:
    """Texte « Sélectionner » qui fait passer la grille en mode sélection."""
    return page.get_by_text(_SELECT_TEXT).first


def thumbnails(page: Page) -> Locator:
    """Vignettes des publications aimées, dans l'ordre de la grille."""
    return page.get_by_role("button", name=THUMBNAIL_LABEL)
