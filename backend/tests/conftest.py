import logging
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

from app.browser.session import BrowserSession
from app.core.config import get_settings
from app.core.logs import LOGGER_NAME
from tests.fake_instagram import NO_NETWORK_ARGS, FakeInstagram

ENV_VARS = ("DATA_DIR", "DAILY_LIMIT", "DELAY_MIN", "DELAY_MAX", "BATCH_SIZE", "LOG_LEVEL")


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
