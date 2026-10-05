"""Exploration de la page des likes, sans rien modifier, pour préparer les filtres et l'unlike.

L'exploration ouvre le panneau « Trier et filtrer », puis le mode « Sélectionner » avec une
vignette cochée, et enregistre un diagnostic à chaque étape. Elle ne clique jamais sur
« Ne plus aimer » : chaque étape se termine par un rechargement de la page, qui referme le
panneau sans appliquer de filtre et annule la sélection.
"""

import asyncio
import logging
from pathlib import Path

from playwright.async_api import Locator
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.browser import locators
from app.browser.session import BrowserSession, NavigationOutcome

logger = logging.getLogger(__name__)

CLICK_TIMEOUT_MS = 10_000
# Laisse à l'interface le temps d'afficher le résultat d'un clic avant le diagnostic.
SETTLE_DELAY = 1.5


class ProbeError(RuntimeError):
    """La page des likes n'a pas pu être rouverte entre deux étapes."""


async def run_probe(session: BrowserSession, directory: Path) -> list[Path]:
    """Explore la page des likes, déjà ouverte, et renvoie les diagnostics enregistrés."""
    page = session.page
    reports = [await session.save_diagnostic(directory, "likes")]

    if await _click(locators.sort_and_filter_button(page), "Trier et filtrer"):
        reports.append(await session.save_diagnostic(directory, "filtres"))
    await _reload(session)

    if await _click(locators.select_toggle(page), "Sélectionner"):
        reports.append(await session.save_diagnostic(directory, "selection"))
        if await _click(locators.thumbnails(page).first, "première vignette"):
            reports.append(await session.save_diagnostic(directory, "selection-1-element"))
    await _reload(session)
    return reports


async def _click(target: Locator, description: str) -> bool:
    try:
        await target.click(timeout=CLICK_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        logger.warning("Exploration : « %s » introuvable, étape ignorée", description)
        return False
    await asyncio.sleep(SETTLE_DELAY)
    return True


async def _reload(session: BrowserSession) -> None:
    # Une interface modifiée n'arrête pas l'exploration : c'est là qu'elle est la plus utile.
    outcome = await session.open_likes_page()
    if outcome not in (NavigationOutcome.OK, NavigationOutcome.LAYOUT_CHANGED):
        raise ProbeError(f"Page des likes non rouverte pendant l'exploration : {outcome}")
