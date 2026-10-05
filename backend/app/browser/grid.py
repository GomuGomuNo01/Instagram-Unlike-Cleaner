"""Lecture de la grille des likes : libellés des vignettes, identifiants et chargement complet."""

import asyncio
import logging
import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, cast
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from app.browser import locators
from app.browser.locators import PageKind
from app.models.tables import MediaKind

logger = logging.getLogger(__name__)

# Pause entre deux défilements, tirée au hasard (secondes) : laisse à Instagram le temps de
# charger le paquet suivant, sans enchaîner les requêtes à un rythme régulier.
SCROLL_PAUSE = (1.2, 2.2)

# Les dates des libellés restent en anglais, même avec l'interface en français (confirmé).
_MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        start=1,
    )
}
_PUBLISHED = re.compile(r"^(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})$")
# Nom de fichier des images, confirmé : « 825276465_18099527753527395_7647109996829922508_n.jpg ».
_MEDIA_FILE = re.compile(r"/(?P<key>\d+_\d+_\d+_n)\.[A-Za-z0-9]+$")


class GridInterrupted(RuntimeError):
    """La collecte a dû s'arrêter : page quittée ou fenêtre d'Instagram ouverte par-dessus.

    `alert` reprend le texte de la fenêtre s'il signale une limite ou une erreur.
    """

    def __init__(self, message: str, alert: str | None = None) -> None:
        super().__init__(message)
        self.alert = alert


@dataclass(frozen=True)
class Thumbnail:
    media_key: str
    label: str
    author: str | None
    media_kind: MediaKind | None
    published_on: date | None
    checked: bool = False


def normalize_label(label: str) -> str:
    """Remplace les espaces insécables et les espaces multiples par une espace simple."""
    return " ".join(label.split())


def parse_media_kind(text: str) -> MediaKind | None:
    first_word = text.split(" ", 1)[0].lower()
    return {
        "photo": MediaKind.PHOTO,
        "vidéo": MediaKind.VIDEO,
        "video": MediaKind.VIDEO,
        "carrousel": MediaKind.CAROUSEL,
        "carousel": MediaKind.CAROUSEL,
    }.get(first_word)


def parse_published(text: str | None) -> date | None:
    """Lit une date du type « October 3, 2026 ». Renvoie None si le format est inconnu."""
    match = _PUBLISHED.match(text.strip()) if text else None
    if match is None:
        return None
    month = _MONTHS.get(match["month"].lower())
    if month is None:
        return None
    try:
        return date(int(match["year"]), month, int(match["day"]))
    except ValueError:
        return None


def media_key_from_src(src: str | None) -> str | None:
    """Extrait le nom du fichier image, sans les paramètres de signature qui changent."""
    if not src:
        return None
    match = _MEDIA_FILE.search(urlparse(src).path)
    return match["key"] if match else None


def thumbnails_from_raw(raw_items: list[dict[str, Any]]) -> list[Thumbnail]:
    """Transforme les vignettes lues dans la page en objets Python, sans doublon de clé.

    Sans nom de fichier image exploitable, la clé est tirée du libellé sans sa position ;
    deux vignettes au libellé identique reçoivent alors les suffixes #1, #2...
    """
    thumbnails: list[Thumbnail] = []
    fallback_counts: dict[str, int] = {}
    for raw in raw_items:
        label = normalize_label(str(raw.get("label") or ""))
        match = locators.THUMBNAIL_LABEL_PARTS.match(label)
        if match is None:
            continue
        media_kind = parse_media_kind(match["kind"])
        published_on = parse_published(match["published"])
        key = media_key_from_src(raw.get("src"))
        if key is None:
            base = f"libelle:{media_kind}|{match['author'].lower()}|{published_on}"
            fallback_counts[base] = fallback_counts.get(base, 0) + 1
            key = f"{base}#{fallback_counts[base]}"
        icons = [str(icon) for icon in raw.get("icons") or []]
        thumbnails.append(
            Thumbnail(
                media_key=key,
                label=label,
                author=match["author"].lower(),
                media_kind=media_kind,
                published_on=published_on,
                checked=any(locators.CHECKED_ICON.match(icon) for icon in icons),
            )
        )
    return thumbnails


async def read_thumbnails(page: Page) -> list[Thumbnail]:
    raw = cast(list[dict[str, Any]], await page.evaluate(locators.READ_THUMBNAILS_JS))
    return thumbnails_from_raw(raw)


async def load_grid(
    page: Page,
    *,
    idle_rounds: int = 3,
    max_items: int | None = None,
    stop_when: Callable[[dict[str, Thumbnail]], bool] | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> list[Thumbnail]:
    """Fait défiler la grille jusqu'au bout et renvoie toutes les vignettes, dans l'ordre.

    Les vignettes sont relues à chaque tour et cumulées par clé, ce qui fonctionne même si
    Instagram retire du DOM celles qui sortent de l'écran. La collecte s'arrête quand plus
    rien n'arrive pendant `idle_rounds` tours (trois fois plus si « Chargement... » reste
    affiché), dès que `max_items` vignettes sont lues, ou dès que `stop_when` renvoie vrai
    pour les vignettes déjà lues.
    """
    collected: dict[str, Thumbnail] = {}
    idle = 0
    while True:
        await ensure_collectable(page)
        before = len(collected)
        for thumbnail in await read_thumbnails(page):
            collected.setdefault(thumbnail.media_key, thumbnail)
        if on_progress is not None:
            on_progress(len(collected))
        if max_items is not None and len(collected) >= max_items:
            break
        if stop_when is not None and stop_when(collected):
            break
        idle = idle + 1 if len(collected) == before else 0
        still_loading = await locators.loading_indicator(page).is_visible()
        if idle >= (idle_rounds * 3 if still_loading else idle_rounds):
            break
        await _scroll_to_end(page)
        await asyncio.sleep(random.uniform(*SCROLL_PAUSE))
    thumbnails = list(collected.values())
    # Niveau DEBUG : la CLI et le journal en base affichent déjà ce total, et une ligne en
    # console couperait la progression affichée sur une seule ligne.
    logger.debug("Grille lue : %d vignettes", len(thumbnails))
    return thumbnails[:max_items] if max_items is not None else thumbnails


async def ensure_collectable(page: Page) -> None:
    """Lève GridInterrupted si la page des likes a été quittée ou est recouverte."""
    kind = locators.classify_path(urlparse(page.url).path)
    if kind is not PageKind.LIKES:
        raise GridInterrupted(f"la page des likes a été quittée ({kind})")
    dialog = locators.blocking_dialog(page)
    if await dialog.is_visible():
        text = normalize_label(await dialog.inner_text())
        raise GridInterrupted(
            "une fenêtre d'Instagram recouvre la page des likes",
            alert=text if locators.ALERT_TEXT.search(text) else None,
        )


async def _scroll_to_end(page: Page) -> None:
    """Amène à l'écran l'indicateur de chargement, ou à défaut la dernière vignette :
    c'est ce qui déclenche le chargement du paquet suivant."""
    indicator = locators.loading_indicator(page)
    target = indicator if await indicator.count() else locators.thumbnails(page).last
    try:
        if await target.count():
            await target.scroll_into_view_if_needed(timeout=5_000)
    except PlaywrightError as exc:
        # La grille peut se réorganiser pendant le défilement : on réessaie au tour suivant.
        logger.debug("Défilement ignoré : %s", exc)
