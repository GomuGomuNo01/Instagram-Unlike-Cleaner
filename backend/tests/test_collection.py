"""Collecte de la grille et filtre d'Instagram, sur la fausse page des likes, sans réseau."""

from datetime import date

import pytest

from app.browser import locators
from app.browser.grid import GridInterrupted, load_grid, read_thumbnails
from app.browser.native_filters import apply_native_filters
from app.browser.session import BrowserSession, NavigationOutcome
from app.models.schemas import CleanupFilters, SortOrder
from app.models.tables import MediaKind
from tests.fake_instagram import (
    FakeInstagram,
    interactive_likes_page,
    log_in,
    make_likes,
    selection_mode_page,
)

pytestmark = [pytest.mark.anyio, pytest.mark.browser]


async def open_page(session: BrowserSession, fake_instagram: FakeInstagram, body: str) -> None:
    fake_instagram.page(locators.LIKES_PATH, body)
    await log_in(session.context)
    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK


def filter_requests(fake_instagram: FakeInstagram) -> list[str]:
    return [path for path in fake_instagram.requested_paths if path.startswith("/__filtre__")]


async def test_load_grid_reads_every_batch(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    likes = make_likes(40)  # trois paquets : 18, 18 et 4
    await open_page(session, fake_instagram, interactive_likes_page(likes))
    progress: list[int] = []

    thumbnails = await load_grid(session.page, on_progress=progress.append)

    assert [thumbnail.media_key for thumbnail in thumbnails] == [like.key for like in likes]
    assert progress[0] < 40 <= progress[-1]  # chargement progressif, par défilement
    assert {thumbnail.media_kind for thumbnail in thumbnails} == set(MediaKind)
    assert thumbnails[1].author == "auteur.b"
    assert thumbnails[0].published_on == date(2026, 10, 3)


async def test_load_grid_stops_at_max_items(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    likes = make_likes(40)
    await open_page(session, fake_instagram, interactive_likes_page(likes))

    thumbnails = await load_grid(session.page, max_items=20)

    assert [thumbnail.media_key for thumbnail in thumbnails] == [like.key for like in likes[:20]]


async def test_native_filter_restricts_dates_and_reverses_sort(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    likes = make_likes(40)
    await open_page(session, fake_instagram, interactive_likes_page(likes))
    filters = CleanupFilters(
        sort=SortOrder.OLDEST_FIRST, start_date=date(2026, 6, 1), end_date=date(2026, 8, 31)
    )

    assert await apply_native_filters(session.page, filters)
    thumbnails = await load_grid(session.page)

    expected = [like.key for like in reversed(likes) if "2026-06-01" <= like.liked <= "2026-08-31"]
    assert [thumbnail.media_key for thumbnail in thumbnails] == expected
    assert filter_requests(fake_instagram) == ["/__filtre__/2026-06-01/2026-08-31/oldest_first"]


async def test_native_filter_is_skipped_when_not_needed(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    await open_page(session, fake_instagram, interactive_likes_page(make_likes(5)))

    assert not await apply_native_filters(session.page, CleanupFilters())
    assert filter_requests(fake_instagram) == []


async def test_unchanged_filter_is_closed_without_applying(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    likes = make_likes(5)
    await open_page(session, fake_instagram, interactive_likes_page(likes))
    # La date de début demandée est déjà celle proposée par défaut : « Appliquer » reste grisé.
    filters = CleanupFilters(start_date=date.fromisoformat(likes[-1].liked))

    assert await apply_native_filters(session.page, filters)
    assert not await locators.filters_dialog(session.page).is_visible()
    assert filter_requests(fake_instagram) == []


async def test_collection_stops_when_instagram_opens_a_dialog(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    page = interactive_likes_page(make_likes(80), blocking_dialog_after_ms=1000)
    await open_page(session, fake_instagram, page)

    with pytest.raises(GridInterrupted, match="fenêtre"):
        await load_grid(session.page)


async def test_reads_selection_mode_without_duplicates(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    likes = make_likes(3)
    await open_page(session, fake_instagram, selection_mode_page(likes, checked=1))

    thumbnails = await read_thumbnails(session.page)

    assert [thumbnail.media_key for thumbnail in thumbnails] == [like.key for like in likes]
    assert [thumbnail.checked for thumbnail in thumbnails] == [False, True, False]
    assert await locators.thumbnails(session.page).count() == 3
