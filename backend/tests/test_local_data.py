"""Suppression des données locales : seulement ce qu'IUC a créé, jamais autre chose."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.local_data import (
    LocalDataError,
    delete_browser_profile,
    delete_local_data,
    unexpected_entries,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data")
    settings.ensure_dirs()
    (settings.browser_profile_dir / "Default").mkdir()
    (settings.browser_profile_dir / "Default" / "Cookies").write_text("cookies")
    settings.db_path.write_text("base")
    settings.db_path.with_name("iuc.db-wal").write_text("wal")
    (settings.reports_dir / "rapport-1.csv").write_text("rapport")
    settings.diagnostics_dir.mkdir()
    (settings.diagnostics_dir / "likes.txt").write_text("diagnostic")
    (settings.logs_dir / "iuc.log").write_text("journal")
    return settings


def test_delete_local_data_removes_everything_iuc_created(settings: Settings) -> None:
    deleted = delete_local_data(settings)

    assert {path.name for path in deleted} == {
        "browser-profile",
        "iuc.db",
        "iuc.db-wal",
        "reports",
        "diagnostics",
        "logs",
    }
    assert settings.data_dir.is_dir()  # le dossier lui-même est conservé
    assert list(settings.data_dir.iterdir()) == []


def test_refuses_when_the_folder_holds_something_else(settings: Settings) -> None:
    personal = settings.data_dir / "Mes documents"
    personal.mkdir()

    assert unexpected_entries(settings) == [personal]
    with pytest.raises(LocalDataError, match="Mes documents"):
        delete_local_data(settings)

    assert settings.db_path.exists()
    assert settings.browser_profile_dir.exists()


def test_delete_browser_profile_keeps_the_rest(settings: Settings) -> None:
    assert delete_browser_profile(settings)
    assert not delete_browser_profile(settings)  # déjà supprimé

    assert not settings.browser_profile_dir.exists()
    assert settings.db_path.exists()
    assert (settings.reports_dir / "rapport-1.csv").exists()


def test_missing_data_dir_is_not_an_error(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path / "absent")

    assert delete_local_data(settings) == []


def test_file_in_use_gives_a_clear_message(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def locked(path: Path) -> None:
        raise PermissionError(f"[WinError 32] {path}")

    monkeypatch.setattr("shutil.rmtree", locked)

    with pytest.raises(LocalDataError, match="utilisé par un autre programme"):
        delete_browser_profile(settings)
    assert settings.browser_profile_dir.exists()
