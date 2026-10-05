"""Mode sélection de la page des likes : cocher un lot, « Je n’aime plus », confirmation.

Garde-fou principal : « Je n’aime plus » n'est cliqué que si les vignettes cochées sont
exactement celles du lot demandé, d'après les cases et le compteur d'Instagram. Dans la
fenêtre qui suit, seul un bouton portant ce même nom est accepté comme confirmation : toute
autre fenêtre arrête le nettoyage sans rien confirmer.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import StrEnum

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from app.browser import locators
from app.browser.grid import normalize_label, read_thumbnails

logger = logging.getLogger(__name__)

TIMEOUT_MS = 10_000
# Pause entre deux cases cochées, au rythme d'une personne (secondes, tirée au hasard).
CLICK_PAUSE = (0.6, 1.6)
# Temps laissé à Instagram pour retirer les vignettes après « Je n’aime plus ».
REMOVAL_TIMEOUT = 15.0
_POLL = 0.3


class SelectionError(RuntimeError):
    """Les cases cochées ne correspondent pas au lot : la sélection a été annulée."""


class UnlikeOutcome(StrEnum):
    REMOVED = "removed"  # toutes les vignettes du lot ont disparu
    NOT_REMOVED = "not_removed"  # certaines vignettes sont restées affichées
    BLOCKED = "blocked"  # message d'Instagram signalant une limite ou une erreur
    UNKNOWN_DIALOG = "unknown_dialog"  # fenêtre inattendue : rien n'a été confirmé


@dataclass(frozen=True)
class UnlikeReport:
    outcome: UnlikeOutcome
    still_present: frozenset[str] = frozenset()
    message: str | None = None  # texte du message ou de la fenêtre rencontrée


async def enter_selection_mode(page: Page) -> None:
    await locators.select_toggle(page).click(timeout=TIMEOUT_MS)
    await locators.unlike_button(page).wait_for(state="visible", timeout=TIMEOUT_MS)


async def select_batch(page: Page, media_keys: list[str]) -> None:
    """Coche les vignettes du lot, puis vérifie que ce sont exactement elles qui le sont.

    En cas d'écart (case manquante, case en trop, compteur différent), la sélection est
    annulée et SelectionError levée : rien n'est retiré.
    """
    for key in media_keys:
        target = locators.thumbnail_by_media_key(page, key)
        await target.scroll_into_view_if_needed(timeout=TIMEOUT_MS)
        await target.click(timeout=TIMEOUT_MS)
        await asyncio.sleep(random.uniform(*CLICK_PAUSE))
    checked = {
        thumbnail.media_key for thumbnail in await read_thumbnails(page) if thumbnail.checked
    }
    counter = await _read_counter(page)
    if checked != set(media_keys) or counter != len(media_keys):
        await _cancel_selection(page)
        raise SelectionError(
            f"{len(media_keys)} likes attendus, {len(checked)} cases cochées, "
            f"compteur d'Instagram : {counter if counter is not None else 'illisible'}"
        )


async def unlike_selected(page: Page, media_keys: list[str]) -> UnlikeReport:
    """Clique sur « Je n’aime plus », confirme si Instagram le demande, puis attend que les
    vignettes du lot disparaissent.

    Instagram vide puis recharge toute la grille juste après la confirmation (confirmé) : la
    disparition des vignettes ne prouve donc pas le retrait. La preuve vient du rechargement
    suivant, où un like encore présent passe en échec (voir services/cleanup.py).
    """
    keys = frozenset(media_keys)
    await locators.unlike_button(page).click(timeout=TIMEOUT_MS)
    confirmed = False
    deadline = time.monotonic() + REMOVAL_TIMEOUT
    while True:
        dialog = locators.blocking_dialog(page)
        if await dialog.is_visible():
            text = normalize_label(await dialog.inner_text())
            if locators.ALERT_TEXT.search(text):
                return UnlikeReport(UnlikeOutcome.BLOCKED, keys, text)
            if not confirmed:
                confirm = dialog.get_by_role("button", name=locators.UNLIKE_NAME)
                if not await confirm.count():
                    return UnlikeReport(UnlikeOutcome.UNKNOWN_DIALOG, keys, text)
                logger.info("Confirmation demandée par Instagram : %s", text)
                await confirm.first.click(timeout=TIMEOUT_MS)
                confirmed = True
                await asyncio.sleep(_POLL)
                continue
        alert = await _alert_text(page)
        if alert and locators.ALERT_TEXT.search(alert):
            return UnlikeReport(UnlikeOutcome.BLOCKED, keys, alert)
        present = keys & {thumbnail.media_key for thumbnail in await read_thumbnails(page)}
        if not present:
            return UnlikeReport(UnlikeOutcome.REMOVED, message=alert or None)
        if time.monotonic() >= deadline:
            return UnlikeReport(UnlikeOutcome.NOT_REMOVED, frozenset(present), alert or None)
        await asyncio.sleep(_POLL)


async def _read_counter(page: Page) -> int | None:
    counter = locators.selection_counter(page)
    if not await counter.count():
        return None
    return locators.parse_counter(await counter.inner_text())


async def _cancel_selection(page: Page) -> None:
    try:
        await locators.cancel_selection(page).click(timeout=TIMEOUT_MS)
    except PlaywrightError as exc:
        logger.warning("Annulation de la sélection impossible : %s", exc)


async def _alert_text(page: Page) -> str:
    alerts = locators.alert_messages(page)
    texts = [await alerts.nth(index).inner_text() for index in range(await alerts.count())]
    return normalize_label(" ".join(texts))
