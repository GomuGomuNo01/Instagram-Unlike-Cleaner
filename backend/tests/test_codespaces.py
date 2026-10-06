"""Vraie version dans GitHub Codespaces : seul l'hôte du Codespace s'ajoute à 127.0.0.1."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.codespaces import desktop_url, forwarded_host
from app.core.config import Settings
from app.main import create_app
from tests.test_frontend import TOKEN, make_dist

CODESPACE = {
    "CODESPACES": "true",
    "CODESPACE_NAME": "fictif-iuc-7x9q",
    "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev",
}
PUBLIC_HOST = "fictif-iuc-7x9q-8765.app.github.dev"


def test_nothing_changes_outside_codespaces() -> None:
    assert forwarded_host(8765, {}) is None
    assert desktop_url({}) is None
    assert forwarded_host(8765, {**CODESPACE, "CODESPACES": "false"}) is None


def test_codespace_addresses() -> None:
    assert forwarded_host(8765, CODESPACE) == PUBLIC_HOST
    assert desktop_url(CODESPACE) == (
        "https://fictif-iuc-7x9q-6080.app.github.dev/vnc.html?autoconnect=true&resize=scale"
    )


@pytest.mark.parametrize(
    "variables",
    [
        {"CODESPACE_NAME": 'x" onload="alert(1)'},
        {"CODESPACE_NAME": "nom/avec/barre"},
        {"GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "exemple.com/chemin"},
        {"CODESPACE_NAME": ""},
    ],
)
def test_unexpected_values_are_ignored(variables: dict[str, str]) -> None:
    assert forwarded_host(8765, {**CODESPACE, **variables}) is None


@pytest.fixture
def in_codespace(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in CODESPACE.items():
        monkeypatch.setenv(name, value)


@pytest.mark.anyio
@pytest.mark.usefixtures("in_codespace")
async def test_codespace_host_is_accepted_and_desktop_announced(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None, data_dir=tmp_path / "data", frontend_dist=make_dist(tmp_path)
    )
    app = create_app(settings, token=TOKEN)
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url=f"https://{PUBLIC_HOST}") as http:
            page = await http.get("/")
            status = await http.get("/api/session/status", headers={"X-IUC-Token": TOKEN})
            other = await http.get("/", headers={"Host": "fictif-iuc-7x9q-9999.app.github.dev"})
    finally:
        app.state.iuc.engine.dispose()

    assert page.status_code == 200
    assert '<meta name="iuc-desktop" content="https://fictif-iuc-7x9q-6080.app.github.dev/' in (
        page.text
    )
    assert status.status_code == 200
    assert other.status_code == 400  # un autre port du même Codespace reste refusé
