"""Vérification de la structure de la page des likes : l'interface d'Instagram a-t-elle changé ?

Avant toute collecte ou tout nettoyage, chaque élément dont IUC a besoin est cherché. S'il
manque, le message dit lequel, au lieu d'un délai dépassé au milieu d'un lot. Les éléments
eux-mêmes restent décrits dans `locators.py`.
"""

from collections.abc import Callable
from typing import Any, cast

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.browser import locators
from app.browser.grid import media_key_from_src, thumbnails_from_raw

# Temps laissé à chaque élément pour apparaître, une fois la page des likes reconnue.
ELEMENT_WAIT_MS = 3_000


class LayoutChanged(RuntimeError):
    """Un élément attendu de l'interface d'Instagram est introuvable."""


def _selection_control(page: Page) -> Locator:
    # « Sélectionner », ou « Annuler » si la grille est déjà en mode sélection.
    return locators.select_toggle(page).or_(locators.cancel_selection(page)).first


_LIKES_PAGE_ELEMENTS: tuple[tuple[str, Callable[[Page], Locator]], ...] = (
    ("bouton « Trier et filtrer »", locators.sort_and_filter_button),
    ("texte « Sélectionner »", _selection_control),
)


async def missing_on_likes_page(page: Page) -> list[str]:
    """Éléments de la page des likes introuvables ; liste vide si tout est en place."""
    missing = []
    for description, find in _LIKES_PAGE_ELEMENTS:
        try:
            await find(page).wait_for(state="visible", timeout=ELEMENT_WAIT_MS)
        except PlaywrightTimeoutError:
            missing.append(description)
    if await _unreadable_thumbnails(page):
        missing.append("libellé des vignettes (type et auteur)")
    return missing


async def _unreadable_thumbnails(page: Page) -> bool:
    """Des vignettes de publications sont affichées, mais aucune n'a le libellé attendu.

    Une page sans aucun like n'est pas un changement d'interface : seules comptent les
    vignettes reconnaissables à leur image de publication.
    """
    raw = cast(list[dict[str, Any]], await page.evaluate(locators.READ_THUMBNAILS_JS))
    with_media = [item for item in raw if media_key_from_src(item.get("src"))]
    return bool(with_media) and not thumbnails_from_raw(with_media)


def layout_message(missing: list[str]) -> str:
    return "élément introuvable : " + ", ".join(missing)
