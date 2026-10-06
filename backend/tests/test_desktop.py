"""Application installée : données chez l'utilisateur, interface embarquée, navigateur du
système. Chaque réglage reste modifiable par l'utilisateur."""

import sys
import uuid
from pathlib import Path

import pytest

from app.core.config import Settings
from app.desktop import configure, first_instance, silence_missing_streams, user_data_root


def test_user_data_root(tmp_path: Path) -> None:
    assert user_data_root({"LOCALAPPDATA": str(tmp_path)}) == tmp_path / "IUC"
    assert user_data_root({}) == Path.home() / ".local" / "share" / "IUC"


def test_installed_app_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    environ = {"LOCALAPPDATA": str(tmp_path / "local")}

    root = configure(tmp_path / "bundle", environ)

    assert root == tmp_path / "local" / "IUC" and root.is_dir()
    for name, value in environ.items():
        monkeypatch.setenv(name, value)  # comme dans l'application, lus par Settings
    settings = Settings(_env_file=None)
    assert settings.data_dir == root / "data"
    assert settings.frontend_dist == tmp_path / "bundle" / "frontend" / "dist"
    assert settings.browser_channels == ["chrome", "msedge"]


def test_user_settings_win(tmp_path: Path) -> None:
    environ = {
        "LOCALAPPDATA": str(tmp_path),
        "DATA_DIR": "D:/mes-donnees",
        "BROWSER_CHANNELS": '["msedge"]',
    }

    configure(tmp_path / "bundle", environ)

    assert environ["DATA_DIR"] == "D:/mes-donnees"
    assert environ["BROWSER_CHANNELS"] == '["msedge"]'


@pytest.mark.skipif(sys.platform != "win32", reason="verrou nommé de Windows")
def test_relaunching_finds_the_first_instance() -> None:
    name = rf"Local\IUC-test-{uuid.uuid4().hex}"

    assert first_instance(name)
    assert not first_instance(name)  # IUC.exe relancé : il rouvre l'interface et s'arrête


def test_without_console_messages_go_nowhere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    silence_missing_streams()

    print("message sans console")  # ne doit pas lever d'erreur
    assert sys.stdout is not None and sys.stderr is not None
    sys.stdout.close()
    sys.stderr.close()
