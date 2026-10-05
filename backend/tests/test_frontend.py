"""Service de l'interface compilée par l'API : jeton injecté, protections et routes."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.anyio

TOKEN = "jeton-de-test"
INDEX = "<!doctype html><html><head><title>IUC</title></head><body>interface</body></html>"


def make_dist(root: Path) -> Path:
    dist = root / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX, encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('iuc')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (root / "secret.txt").write_text("hors du dossier dist", encoding="utf-8")
    return dist


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    app = build(tmp_path, make_dist(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as http:
        yield http
    app.state.iuc.engine.dispose()


def build(tmp_path: Path, dist: Path) -> FastAPI:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data", frontend_dist=dist)
    return create_app(settings, token=TOKEN)


async def test_index_receives_the_token_and_refuses_framing(client: AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert f'<meta name="iuc-token" content="{TOKEN}" />' in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


async def test_app_routes_serve_the_index(client: AsyncClient) -> None:
    response = await client.get("/nettoyages/6/suivi")

    assert response.status_code == 200
    assert "interface" in response.text


async def test_static_files_are_served(client: AsyncClient) -> None:
    assert (await client.get("/assets/app.js")).text == "console.log('iuc')"
    assert (await client.get("/favicon.svg")).text == "<svg/>"


async def test_unknown_api_route_stays_a_json_404(client: AsyncClient) -> None:
    response = await client.get("/api/inconnue", headers={"X-IUC-Token": TOKEN})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


async def test_files_outside_dist_are_never_served(client: AsyncClient) -> None:
    response = await client.get("/..%2Fsecret.txt")

    assert "hors du dossier dist" not in response.text


async def test_other_hosts_are_refused(client: AsyncClient) -> None:
    response = await client.get("/", headers={"Host": "site-malveillant.example"})

    assert response.status_code == 400


async def test_missing_build_explains_how_to_compile(tmp_path: Path) -> None:
    app = build(tmp_path, tmp_path / "absent")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as http:
        response = await http.get("/")
    app.state.iuc.engine.dispose()

    assert response.status_code == 503
    assert "npm run build" in response.text
    assert TOKEN not in response.text
