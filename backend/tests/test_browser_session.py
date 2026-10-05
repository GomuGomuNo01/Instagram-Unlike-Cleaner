"""Tests de la session navigateur sur de fausses pages Instagram, sans aucun accès réseau."""

import asyncio
import logging
from pathlib import Path

import pytest
from playwright.async_api import Error as PlaywrightError

from app.browser import locators
from app.browser.locators import PageKind
from app.browser.session import BrowserSession, NavigationOutcome
from tests.fake_instagram import (
    LIKES_PAGE_EN,
    LIKES_PAGE_FR,
    NO_NETWORK_ARGS,
    FakeInstagram,
    html,
    log_in,
)

pytestmark = [pytest.mark.anyio, pytest.mark.browser]


async def test_requests_escaping_interception_never_reach_the_network(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    # Playwright n'intercepte pas la requête qui suit une redirection HTTP : sans le filet
    # NO_NETWORK_ARGS, elle partirait sur le vrai instagram.com.
    fake_instagram.http_redirect("/redirection/", "/accounts/login/")

    with pytest.raises(PlaywrightError, match="ERR_NAME_NOT_RESOLVED"):
        await session.page.goto(f"{locators.BASE_URL}/redirection/")

    assert "/accounts/login/" not in fake_instagram.requested_paths


async def test_not_logged_in_without_session_cookie(session: BrowserSession) -> None:
    await session.open_home()

    status = await session.status()

    assert status.browser_open
    assert not status.logged_in
    assert status.account_id is None
    assert status.page is PageKind.HOME


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
    fake_instagram.page(locators.LIKES_PATH, body)
    await log_in(session.context)

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK


async def test_detects_redirect_to_login(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.redirect(locators.LIKES_PATH, "/accounts/login/?next=/your_activity/")
    fake_instagram.page("/accounts/login/", html("<h1>Connexion</h1>"))

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.LOGIN_REQUIRED


async def test_detects_client_redirect_to_challenge(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.page(locators.LIKES_PATH, html("", "location.replace('/challenge/action/')"))
    fake_instagram.page("/challenge/action/", html("<h1>Vérification de sécurité</h1>"))
    await log_in(session.context)

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.CHALLENGE
    assert (await session.status()).challenge_required


async def test_detects_consent_screen_without_answering_it(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    # Écran observé le 04/10/2026 : Meta demande de choisir entre abonnement et publicités.
    fake_instagram.redirect(locators.LIKES_PATH, "/consent/?flow=ad_free_subscription")
    fake_instagram.page(
        "/consent/",
        html("<div role='dialog'><h1>Voulez-vous vous abonner ?</h1><button>Continuer</button>"),
    )
    await log_in(session.context)

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.CONSENT_REQUIRED
    status = await session.status()
    assert status.consent_required
    assert status.logged_in


async def test_stops_when_a_dialog_covers_the_likes_page(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    # Cas de l'essai du 05/10/2026 à 09:44, juste après une connexion.
    fake_instagram.page(
        locators.LIKES_PATH,
        LIKES_PAGE_FR.replace(
            "</body>",
            "<div role='dialog'>Enregistrer vos informations de connexion ?"
            "<button>Enregistrer les informations</button><button>Plus tard</button></div>"
            "</body>",
        ),
    )
    await log_in(session.context)

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.BLOCKING_DIALOG
    # Le script n'a pas répondu à la place de l'utilisateur : la fenêtre est toujours là.
    assert await session.page.get_by_role("button", name="Plus tard").is_visible()


async def test_detects_another_page_without_logging_its_address(
    session: BrowserSession,
    fake_instagram: FakeInstagram,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Cas de l'essai du 04/10/2026 : un clic sur le profil pendant la vérification.
    fake_instagram.page(locators.LIKES_PATH, html("", "location.replace('/compte_prive_123/')"))
    fake_instagram.page("/compte_prive_123/", html("<h1>Profil</h1><span>Sélectionner</span>"))
    await log_in(session.context)
    caplog.set_level(logging.INFO, logger="app")

    outcome = await session.open_likes_page(timeout=0.5)

    assert outcome is NavigationOutcome.UNEXPECTED_PAGE
    assert "autre page" in caplog.text
    assert "compte_prive_123" not in caplog.text


async def test_detects_unknown_layout_on_likes_page(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.page(locators.LIKES_PATH, html("<h1>Nouvelle interface</h1>"))
    await log_in(session.context)

    assert await session.open_likes_page(timeout=0.5) is NavigationOutcome.LAYOUT_CHANGED


async def test_detects_unreachable_instagram(
    session: BrowserSession, fake_instagram: FakeInstagram
) -> None:
    fake_instagram.offline = True

    assert await session.open_likes_page(timeout=1) is NavigationOutcome.UNREACHABLE


async def test_save_diagnostic_lists_structure_and_thumbnails(
    session: BrowserSession, fake_instagram: FakeInstagram, tmp_path: Path
) -> None:
    fake_instagram.page(locators.LIKES_PATH, LIKES_PAGE_FR)
    await log_in(session.context)
    await session.open_likes_page(timeout=5)

    report = await session.save_diagnostic(tmp_path / "diagnostics", "likes")

    content = report.read_text(encoding="utf-8")
    assert locators.LIKES_PATH in content
    assert "Sélectionner" in content
    assert "== Vignettes (3 chargées, HTML d'une vignette par type) ==" in content
    assert "1000_1_n.jpg" in content
    assert "signature-secrete" not in content
    assert report.with_suffix(".png").is_file()


async def test_status_after_user_closes_the_window(session: BrowserSession) -> None:
    await session.context.close()

    status = await session.status()

    assert not status.browser_open
    assert not status.logged_in


async def test_session_survives_a_restart(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    async with BrowserSession(profile_dir, headless=True, extra_args=NO_NETWORK_ARGS) as first:
        await FakeInstagram().install(first.context)
        await log_in(first.context, account_id="777")

    async with BrowserSession(profile_dir, headless=True, extra_args=NO_NETWORK_ARGS) as second:
        await FakeInstagram().install(second.context)
        await second.open_home()
        status = await second.status()

    assert status.logged_in
    assert status.account_id == "777"
