"""Mise à jour de l'application Windows, sur une fausse version de GitHub : lecture seule,
installeur vérifié avant d'être lancé, données gardées."""

import hashlib
import io
import json
import urllib.error
import urllib.request
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.security import TOKEN_HEADER
from app.api.state import ApiState
from app.core.config import Settings
from app.main import create_app
from app.services.update import (
    DOWNLOAD_PREFIX,
    INSTALLER_ARGS,
    LATEST_RELEASE_API,
    InstallMode,
    UpdateError,
    Updater,
    UpdateRefused,
    detect_mode,
    is_newer,
)

pytestmark = pytest.mark.anyio

TOKEN = "jeton-de-test"
INSTALLER = b"MZ installeur de la version 1.5.0"
INSTALLER_URL = f"{DOWNLOAD_PREFIX}v1.5.0/IUC-Setup.exe"


class FakeGitHub:
    """Répond comme l'API et les téléchargements de GitHub, et garde chaque requête."""

    def __init__(
        self,
        *,
        version: str = "v1.5.0",
        content: bytes = INSTALLER,
        published: bytes = INSTALLER,
        url: str = INSTALLER_URL,
        online: bool = True,
    ) -> None:
        self.content = content
        self.online = online
        self.requests: list[urllib.request.Request] = []
        self.release = {
            "tag_name": version,
            "assets": [
                {"name": "IUC-portable.zip", "browser_download_url": "https://autre"},
                {
                    "name": "IUC-Setup.exe",
                    "browser_download_url": url,
                    "size": len(published),
                    "digest": f"sha256:{hashlib.sha256(published).hexdigest()}",
                },
            ],
        }

    def __call__(self, request: urllib.request.Request) -> io.BytesIO:
        self.requests.append(request)
        if not self.online:
            raise urllib.error.URLError("hors ligne")
        if request.full_url == LATEST_RELEASE_API:
            return io.BytesIO(json.dumps(self.release).encode())
        if request.full_url == INSTALLER_URL:
            return io.BytesIO(self.content)
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)  # type: ignore[arg-type]


class Launcher:
    def __init__(self) -> None:
        self.launched: list[tuple[Path, bytes]] = []

    def __call__(self, installer: Path) -> None:
        self.launched.append((installer, installer.read_bytes()))


def make_updater(
    tmp_path: Path,
    github: FakeGitHub,
    *,
    mode: InstallMode = "installer",
    enabled: bool = True,
    launcher: Launcher | None = None,
) -> Updater:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data", update_check=enabled)
    return Updater(
        settings, mode=mode, current="1.4.0", opener=github, launcher=launcher or Launcher()
    )


async def nothing() -> None:
    pass


def test_versions_compare_as_numbers() -> None:
    assert is_newer("v1.10.0", "1.9.0")
    assert is_newer("1.4.1", "1.4.0")
    assert not is_newer("1.4.0", "1.4.0")
    assert not is_newer("1.3.9", "1.4.0")
    with pytest.raises(UpdateError):
        is_newer("1.5.0-beta", "1.4.0")


def test_install_mode() -> None:
    assert detect_mode(frozen=False) == "source"


def test_install_mode_of_the_windows_app(tmp_path: Path) -> None:
    executable = tmp_path / "IUC.exe"
    assert detect_mode(executable, frozen=True) == "portable"

    (tmp_path / "unins000.exe").touch()  # laissé par l'installeur (Inno Setup)
    assert detect_mode(executable, frozen=True) == "installer"


async def test_disabled_check_contacts_nobody(tmp_path: Path) -> None:
    github = FakeGitHub()

    status = await make_updater(tmp_path, github, enabled=False).status()

    assert not status.enabled and not status.available
    assert github.requests == []


async def test_newer_release_is_reported_once_per_interval(tmp_path: Path) -> None:
    github = FakeGitHub()
    updater = make_updater(tmp_path, github)

    status = await updater.status()
    await updater.status()

    assert status.available and status.latest == "1.5.0" and status.current == "1.4.0"
    assert len(github.requests) == 1  # résultat gardé six heures


async def test_requests_are_anonymous_reads(tmp_path: Path) -> None:
    github = FakeGitHub()

    await make_updater(tmp_path, github).install(nothing)

    assert [r.full_url for r in github.requests] == [LATEST_RELEASE_API, INSTALLER_URL]
    for request in github.requests:
        assert request.get_method() == "GET" and request.data is None
        headers = {name.lower() for name, _ in request.header_items()}
        assert not headers & {"authorization", "cookie"}


async def test_unreachable_github_is_not_an_error_for_the_app(tmp_path: Path) -> None:
    status = await make_updater(tmp_path, FakeGitHub(online=False)).status()

    assert not status.available
    assert status.error is not None and "GitHub ne répond pas" in status.error


async def test_install_downloads_verifies_pauses_then_launches(tmp_path: Path) -> None:
    launcher = Launcher()
    updater = make_updater(tmp_path, FakeGitHub(), launcher=launcher)
    steps: list[str] = []

    async def pause_cleanup() -> None:
        steps.append(f"pause ({len(launcher.launched)} installeur lancé)")

    version = await updater.install(pause_cleanup)

    assert version == "1.5.0"
    assert steps == ["pause (0 installeur lancé)"]
    [(installer, content)] = launcher.launched
    assert content == INSTALLER
    assert installer == updater.settings.updates_dir / "IUC-Setup-1.5.0.exe"
    assert "/VERYSILENT" in INSTALLER_ARGS and "/UPDATE=1" in INSTALLER_ARGS


async def test_altered_installer_is_deleted_and_never_launched(tmp_path: Path) -> None:
    launcher = Launcher()
    github = FakeGitHub(content=INSTALLER.replace(b"1.5.0", b"6.6.6"))
    updater = make_updater(tmp_path, github, launcher=launcher)
    paused = []

    async def pause_cleanup() -> None:
        paused.append(True)

    with pytest.raises(UpdateError, match="ne correspond pas"):
        await updater.install(pause_cleanup)

    assert launcher.launched == [] and paused == []  # le nettoyage n'a pas été interrompu
    assert list(updater.settings.updates_dir.iterdir()) == []


async def test_installer_outside_the_project_releases_is_refused(tmp_path: Path) -> None:
    github = FakeGitHub(url="https://exemple.com/IUC-Setup.exe")

    with pytest.raises(UpdateError, match="Adresse de téléchargement inattendue"):
        await make_updater(tmp_path, github).install(nothing)

    assert [r.full_url for r in github.requests] == [LATEST_RELEASE_API]


@pytest.mark.parametrize(
    ("mode", "version", "message"),
    [
        ("portable", "v1.5.0", "version installée"),
        ("source", "v1.5.0", "version installée"),
        ("installer", "v1.4.0", "déjà à jour"),
    ],
)
async def test_install_refused(
    tmp_path: Path, mode: InstallMode, version: str, message: str
) -> None:
    launcher = Launcher()
    updater = make_updater(tmp_path, FakeGitHub(version=version), mode=mode, launcher=launcher)

    with pytest.raises(UpdateRefused, match=message):
        await updater.install(nothing)

    assert launcher.launched == []


async def test_previous_installer_is_removed_by_the_new_version(tmp_path: Path) -> None:
    updater = make_updater(tmp_path, FakeGitHub(version="v1.4.0"))
    leftover = updater.settings.updates_dir / "IUC-Setup-1.4.0.exe"
    leftover.parent.mkdir(parents=True)
    leftover.write_bytes(INSTALLER)

    await updater.status()

    assert not leftover.exists()


# --- Routes de l'API --------------------------------------------------------------------


@pytest.fixture
async def update_app(tmp_path: Path) -> AsyncIterator[FastAPI]:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data", update_check=True)
    application = create_app(settings, token=TOKEN, updater=make_updater(tmp_path, FakeGitHub()))
    yield application
    state: ApiState = application.state.iuc
    state.engine.dispose()


@pytest.fixture
async def client(update_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=update_app),
        base_url="http://127.0.0.1",
        headers={TOKEN_HEADER: TOKEN},
    ) as http:
        yield http


async def test_update_route_requires_the_token(client: AsyncClient) -> None:
    response = await client.get("/api/update", headers={TOKEN_HEADER: "faux"})

    assert response.status_code == 401


async def test_update_route_reports_the_new_version(client: AsyncClient) -> None:
    response = await client.get("/api/update")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "mode": "installer",
        "current": "1.4.0",
        "latest": "1.5.0",
        "available": True,
        "release_url": "https://github.com/GomuGomuNo01/Instagram-Unlike-Cleaner/releases/latest",
        "download_url": None,
        "error": None,
    }


async def test_install_route_closes_iuc_once_the_installer_runs(
    update_app: FastAPI, client: AsyncClient
) -> None:
    state: ApiState = update_app.state.iuc
    closed = []
    state.shutdown = lambda: closed.append(True)

    response = await client.post("/api/update/install")

    assert response.status_code == 202 and response.json() == {"version": "1.5.0"}
    assert closed == []  # fermeture différée : la réponse part d'abord
    second = await client.post("/api/update/install")
    assert second.status_code == 409  # un seul installeur à la fois


async def test_install_route_reports_a_failed_download(
    tmp_path: Path, update_app: FastAPI, client: AsyncClient
) -> None:
    state: ApiState = update_app.state.iuc
    state.updater = make_updater(tmp_path, FakeGitHub(online=False))

    response = await client.post("/api/update/install")

    assert response.status_code == 502
    assert "GitHub ne répond pas" in response.json()["detail"]
