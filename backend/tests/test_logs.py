import logging
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.logs import LOG_FILE_NAME, RedactSecretsFilter, setup_logging


@pytest.mark.parametrize(
    ("message", "secret"),
    [
        ("cookie sessionid=abc123; path=/", "abc123"),
        ("csrftoken: tok-987", "tok-987"),
        ("password=hunter2", "hunter2"),
    ],
)
def test_redacts_secrets(message: str, secret: str) -> None:
    record = logging.LogRecord("app", logging.INFO, __file__, 1, message, None, None)

    RedactSecretsFilter().filter(record)

    assert secret not in record.getMessage()
    assert "***" in record.getMessage()


def test_redacts_secrets_passed_as_arguments() -> None:
    record = logging.LogRecord(
        "app", logging.INFO, __file__, 1, "en-tête %s", ("sessionid=x1",), None
    )

    RedactSecretsFilter().filter(record)

    assert record.getMessage() == "en-tête sessionid=***"


def test_setup_logging_writes_to_file_without_duplicates(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path)

    setup_logging(settings)
    logger = setup_logging(settings)
    logging.getLogger("app.browser").info("navigation sessionid=secret42")

    assert len(logger.handlers) == 2
    content = (settings.logs_dir / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert content.count("navigation") == 1
    assert "secret42" not in content
