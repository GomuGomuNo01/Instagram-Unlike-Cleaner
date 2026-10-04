from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_values() -> None:
    settings = Settings(_env_file=None)

    assert settings.data_dir == Path("./data")
    assert settings.daily_limit == 150
    assert settings.delay_min <= settings.delay_max
    assert settings.log_level == "INFO"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DAILY_LIMIT", "42")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = Settings(_env_file=None)

    assert settings.daily_limit == 42
    assert settings.log_level == "DEBUG"


def test_reads_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("BATCH_SIZE=7\nDELAY_MIN=1\nDELAY_MAX=2\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.batch_size == 7
    assert (settings.delay_min, settings.delay_max) == (1, 2)


def test_rejects_delay_min_above_delay_max() -> None:
    with pytest.raises(ValidationError, match="DELAY_MIN"):
        Settings(_env_file=None, delay_min=10, delay_max=5)


@pytest.mark.parametrize("field", ["daily_limit", "batch_size"])
def test_rejects_zero_limits(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({field: 0})


def test_ensure_dirs_creates_data_layout(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data")

    settings.ensure_dirs()

    assert settings.browser_profile_dir.is_dir()
    assert settings.reports_dir.is_dir()
    assert settings.logs_dir.is_dir()
    assert settings.db_path.parent == settings.data_dir
