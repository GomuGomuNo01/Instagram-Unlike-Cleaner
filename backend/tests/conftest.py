import logging
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

from app.browser import grid, layout, native_filters, selection
from app.browser import session as session_module
from app.browser.session import BrowserSession
from app.core.config import get_settings
from app.core.logs import LOGGER_NAME
from tests.fake_instagram import NO_NETWORK_ARGS, FakeInstagram

ENV_VARS = (
    "DATA_DIR",
    "DAILY_LIMIT",
    "DELAY_MIN",
    "DELAY_MAX",
    "BATCH_SIZE",
    "LOG_LEVEL",
    "API_DOCS",
)


@pytest.fixture
def anyio_backend() -> str:
    """Les tests marqués `anyio` tournent sur asyncio, comme Playwright et FastAPI."""
    return "asyncio"


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Chaque test part d'un environnement vierge, sans les variables ni le .env du poste."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.propagate = True


@pytest.fixture(autouse=True)
def fast_timings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raccourcit les pauses prévues pour le vrai Instagram : la fausse page répond vite."""
    monkeypatch.setattr(session_module, "DIALOG_SETTLE", 0.05)
    monkeypatch.setattr(native_filters, "SETTLE_DELAY", 0.4)
    monkeypatch.setattr(grid, "SCROLL_PAUSE", (0.2, 0.3))
    monkeypatch.setattr(selection, "CLICK_PAUSE", (0.0, 0.02))
    monkeypatch.setattr(selection, "REMOVAL_TIMEOUT", 2.0)
    monkeypatch.setattr(layout, "ELEMENT_WAIT_MS", 400)


@pytest.fixture
def fake_instagram() -> FakeInstagram:
    return FakeInstagram()


@pytest.fixture
async def session(tmp_path: Path, fake_instagram: FakeInstagram) -> AsyncIterator[BrowserSession]:
    """Navigateur sans fenêtre branché sur la fausse version d'Instagram."""
    async with BrowserSession(
        tmp_path / "profile", headless=True, extra_args=NO_NETWORK_ARGS
    ) as browser_session:
        await fake_instagram.install(browser_session.context)
        yield browser_session
