import logging
from collections.abc import Iterator

import pytest

from app.core.config import get_settings
from app.core.logs import LOGGER_NAME

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
