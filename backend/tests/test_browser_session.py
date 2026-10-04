"""Tests de la session navigateur sur de fausses pages Instagram, sans aucun accès réseau."""

import asyncio
import time
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.async_api import BrowserContext, Route

from app.browser import locators
from app.browser.session import BrowserSession, NavigationOutcome

pytestmark = [pytest.mark.anyio, pytest.mark.browser]

LIKES_PATH = urlparse(locators.LIKES_URL).path


def html(body: str) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>"


LIKES_PAGE_FR = html(
    "<h1>J'aime</h1>"
    "<div role='button'>Trier et filtrer</div>"
    "<div role='button'>Sélectionner</div>"
    "<a href='/p/ABC123/'>vignette</a>"
)
LIKES_PAGE_EN = html("<h1>Likes</h1><div role='button'>Select</div>")


class FakeInstagram:
    """Sert des pages locales à la place d'instagram.com et bloque toute autre requête."""

    def __init__(self) -> None:
        self.offline = False
        self._pages: dict[str, tuple[int, str, dict[str, str]]] = {
            "/": (200, html("<h1>Accueil</h1>"), {}),
        }

    def page(self, path: str, body: str) -> None:
        self._pages[path] = (200, body, {})

    def redirect(self, path: str, location: str) -> None:
        self._pages[path] = (302, "", {"location": location})

    async def install(self, context: BrowserContext) -> None:
        # Le dernier gestionnaire enregistré passe en premier : tout ce qui n'est pas
        # instagram.com tombe sur le blocage général.
        await context.route("**/*", lambda route: route.abort())
        await context.route(f"{locators.BASE_URL}/**", self._handle)

    async def _handle(self, route: Route) -> None:
        if self.offline:
            await route.abort("internetdisconnected")
            return
        path = urlparse(route.request.url).path
        status, body, headers = self._pages.get(path, (404, html("introuvable"), {}))
        await route.fulfill(
            status=status, headers=headers, body=body, content_type="text/html; charset=utf-8"
        )


async def log_in(context: BrowserContext, account_id: str = "1234567890") -> None:
    """Simule une connexion manuelle réussie : Instagram pose ses cookies de session."""
    expires = time.time() + 3600
    await context.add_cookies(
        [
            {
                "name": name,
                "value": value,
                "domain": ".instagram.com",
                "path": "/",
                "expires": expires,
                "secure": True,
            }
            for name, value in (
                (locators.SESSION_COOKIE, "faux-jeton"),
                (locators.ACCOUNT_ID_COOKIE, account_id),
            )
        ]
    )


@pytest.fixture
def fake_instagram() -> FakeInstagram:
    return FakeInstagram()


@pytest.fixture
async def session(tmp_path: Path, fake_instagram: FakeInstagram) -> AsyncIterator[BrowserSession]:
    async with BrowserSession(tmp_path / "profile", headless=True) as browser_session:
        await fake_instagram.install(browser_session.context)
        yield browser_session


async def test_not_logged_in_without_session_cookie(session: BrowserSession) -> None:
    await session.open_home()

    status = await session.status()

    assert status.browser_open
    assert not status.logged_in
    assert status.account_id is None


async def test_logged_in_with_session_cookie(session: BrowserSession) -> None:
    await log_in(session.context, account_id="42")
    await session.open_home()

    status = await session.status()

    assert status.logged_in
    assert status.account_id == "42"


async def test_not_logged_in_while_on_login_page(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.page("/accounts/login/", html("<h1>Connexion</h1>"))
    await log_in(session.context)
    await session.page.goto(f"{locators.BASE_URL}/accounts/login/")

    assert not (await session.status()).logged_in


async def test_wait_for_login_detects_manual_login(session: BrowserSession) -> None:
    await session.open_home()

    async def user_logs_in() -> None:
        await asyncio.sleep(0.3)
        await log_in(session.context)

    user = asyncio.create_task(user_logs_in())
    status = await session.wait_for_login(timeout=5, poll_interval=0.1)
    await user

    assert status.logged_in


async def test_wait_for_login_gives_up_after_timeout(session: BrowserSession) -> None:
    await session.open_home()

    status = await session.wait_for_login(timeout=0.3, poll_interval=0.1)

    assert not status.logged_in


@pytest.mark.parametrize("body", [LIKES_PAGE_FR, LIKES_PAGE_EN], ids=["fr", "en"])
async def test_opens_likes_page(
    session: BrowserSession, fake_instagram: FakeInstagram, body: str
) -> None:
    fake_instagram.page(LIKES_PATH, body)
    await log_in(session.context)

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK


async def test_detects_server_redirect_to_login(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.redirect(LIKES_PATH, "/accounts/login/?next=/your_activity/")
    fake_instagram.page("/accounts/login/", html("<h1>Connexion</h1>"))

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.LOGIN_REQUIRED


async def test_detects_client_redirect_to_challenge(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.page(LIKES_PATH, html("<script>location.replace('/challenge/action/')</script>"))
    fake_instagram.page("/challenge/action/", html("<h1>Vérification de sécurité</h1>"))
    await log_in(session.context)

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.CHALLENGE
    assert (await session.status()).challenge_required


async def test_detects_unknown_layout(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.page(LIKES_PATH, html("<h1>Nouvelle interface</h1>"))
    await log_in(session.context)

    assert await session.open_likes_page(timeout=0.5) is NavigationOutcome.LAYOUT_CHANGED


async def test_detects_unreachable_instagram(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.offline = True

    assert await session.open_likes_page(timeout=1) is NavigationOutcome.UNREACHABLE


async def test_save_diagnostic_lists_links_and_structure(
    session: BrowserSession, fake_instagram: FakeInstagram, tmp_path: Path
) -> None:
    fake_instagram.page(LIKES_PATH, LIKES_PAGE_FR)
    await log_in(session.context)
    await session.open_likes_page(timeout=5)

    report = await session.save_diagnostic(tmp_path / "diagnostics", "likes")

    content = report.read_text(encoding="utf-8")
    assert LIKES_PATH in content
    assert "/p/ABC123/" in content
    assert "Sélectionner" in content
    assert report.with_suffix(".png").is_file()


async def test_status_after_user_closes_the_window(session: BrowserSession) -> None:
    await session.context.close()

    status = await session.status()

    assert not status.browser_open
    assert not status.logged_in


async def test_session_survives_a_restart(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    async with BrowserSession(profile_dir, headless=True) as first:
        await FakeInstagram().install(first.context)
        await log_in(first.context, account_id="777")

    async with BrowserSession(profile_dir, headless=True) as second:
        await FakeInstagram().install(second.context)
        await second.open_home()
        status = await second.status()

    assert status.logged_in
    assert status.account_id == "777"
