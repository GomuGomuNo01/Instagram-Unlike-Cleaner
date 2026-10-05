"""Filtre natif de la page des likes : tri et plage de dates (panneau « Trier et filtrer »)."""

import asyncio
import logging
from datetime import date

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page

from app.browser import locators
from app.browser.layout import LayoutChanged
from app.models.schemas import CleanupFilters, SortOrder

logger = logging.getLogger(__name__)

TIMEOUT_MS = 10_000
# Laisse à la grille le temps de se recharger avec le filtre appliqué.
SETTLE_DELAY = 2.0


class NativeFilterError(LayoutChanged):
    """Le filtre d'Instagram n'a pas pu être appliqué : un élément du panneau manque."""


async def apply_native_filters(page: Page, filters: CleanupFilters) -> bool:
    """Applique le tri et les dates demandés. Renvoie False s'il n'y avait rien à faire."""
    if not filters.uses_native_filters:
        return False
    step = "bouton « Trier et filtrer »"
    try:
        await locators.sort_and_filter_button(page).click(timeout=TIMEOUT_MS)
        step = "panneau « Trier et filtrer »"
        dialog = locators.filters_dialog(page)
        await dialog.wait_for(state="visible", timeout=TIMEOUT_MS)
        step = "choix du tri"
        newest_first = filters.sort is SortOrder.NEWEST_FIRST
        await locators.sort_button(dialog, newest_first=newest_first).click(timeout=TIMEOUT_MS)
        step = "listes de dates (mois, jour, année)"
        if filters.start_date is not None:
            await _select_date(dialog, 0, filters.start_date)
        if filters.end_date is not None:
            await _select_date(dialog, 1, filters.end_date)
        step = "bouton « Appliquer »"
        apply = locators.apply_button(dialog)
        if await apply.is_enabled():
            await apply.click(timeout=TIMEOUT_MS)
        else:
            # Les valeurs demandées sont déjà celles d'Instagram : on referme sans appliquer.
            await page.keyboard.press("Escape")
        await dialog.wait_for(state="hidden", timeout=TIMEOUT_MS)
    except PlaywrightError as exc:
        raise NativeFilterError(
            f"Le filtre d'Instagram n'a pas pu être appliqué : {step} introuvable ou inutilisable"
        ) from exc
    logger.info(
        "Filtre d'Instagram appliqué (tri : %s, dates : %s → %s)",
        filters.sort,
        filters.start_date or "début",
        filters.end_date or "aujourd'hui",
    )
    await asyncio.sleep(SETTLE_DELAY)
    return True


async def _select_date(dialog: Locator, position: int, value: date) -> None:
    month, day, year = locators.date_selects(dialog, position)
    # Année et mois d'abord : la liste des jours peut dépendre du mois choisi.
    await year.select_option(label=str(value.year), timeout=TIMEOUT_MS)
    # Le mois est choisi par sa position (janvier en premier), quelle que soit la langue.
    await month.select_option(index=value.month - 1, timeout=TIMEOUT_MS)
    await day.select_option(label=str(value.day), timeout=TIMEOUT_MS)
