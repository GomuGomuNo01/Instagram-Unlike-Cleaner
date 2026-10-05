"""API locale : sécurité, session, aperçu, nettoyage, contrôle, progression SSE et rapport."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.security import TOKEN_HEADER
from app.api.state import ApiState
from app.browser.session import BrowserSession
from app.core.config import Settings
from app.main import create_app
from tests.fake_instagram import NO_NETWORK_ARGS, FakeInstagram, FakeLike, log_in, make_likes

pytestmark = pytest.mark.anyio

TOKEN = "jeton-de-test"
ACCOUNT = "42"


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "data_dir": tmp_path / "data",
        "daily_limit": 100,
        "batch_size": 4,
        "delay_min": 0,
        "delay_max": 0.05,
    }
    values.update(overrides)
    return Settings.model_validate(values)


@pytest.fixture
async def app(tmp_path: Path, fake_instagram: FakeInstagram) -> AsyncIterator[FastAPI]:
    class FakeBrowser(BrowserSession):
        """Navigateur sans fenêtre, branché sur la fausse version d'Instagram."""

        async def start(self) -> None:
            await super().start()
            await fake_instagram.install(self.context)

    application = create_app(
        make_settings(tmp_path),
        token=TOKEN,
        browser_factory=lambda profile: FakeBrowser(
            profile, headless=True, extra_args=NO_NETWORK_ARGS
        ),
    )
    yield application
    # httpx ne déclenche pas le « lifespan » : on referme comme à l'arrêt du serveur.
    state = api_state(application)
    await state.runner.cancel()
    await state.browser.close()
    state.engine.dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://127.0.0.1",
        headers={TOKEN_HEADER: TOKEN},
    ) as http:
        yield http


def api_state(app: FastAPI) -> ApiState:
    state: ApiState = app.state.iuc
    return state


async def connect(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram, likes: list[FakeLike]
) -> None:
    """Ouvre la session et simule la connexion manuelle de l'utilisateur."""
    fake_instagram.serve_likes(likes)
    response = await client.post("/api/session/start")
    assert response.status_code == 200, response.text
    await log_in(api_state(app).browser.session.context, account_id=ACCOUNT)


async def create_preview(app: FastAPI, client: AsyncClient, **criteria: object) -> int:
    response = await client.post("/api/jobs", json=criteria)
    assert response.status_code == 202, response.text
    await api_state(app).runner.wait()
    job_id: int = response.json()["id"]
    return job_id


# --- Sécurité (sans navigateur) -----------------------------------------------------------


async def test_every_route_requires_the_token(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as anonymous:
        assert (await anonymous.get("/api/jobs")).status_code == 401
        wrong = await anonymous.get("/api/jobs", headers={TOKEN_HEADER: "autre"})
        assert wrong.status_code == 401
        assert (await anonymous.get(f"/api/jobs?token={TOKEN}")).status_code == 200
        assert (await anonymous.post("/api/session/start")).status_code == 401
        # La documentation reste lisible, et décrit l'en-tête du jeton.
        docs = await anonymous.get("/openapi.json")
        assert docs.status_code == 200
        assert TOKEN_HEADER in docs.text


async def test_rejects_other_host_names(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://site-malveillant.example",
        headers={TOKEN_HEADER: TOKEN},
    ) as rebinding:
        assert (await rebinding.get("/api/jobs")).status_code == 400


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [("http://localhost:5173", True), ("https://site-malveillant.example", False)],
)
async def test_cors_allows_only_the_frontend_dev_server(
    client: AsyncClient, origin: str, allowed: bool
) -> None:
    response = await client.options(
        "/api/session/start",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": TOKEN_HEADER,
        },
    )

    assert (response.headers.get("access-control-allow-origin") == origin) is allowed


async def test_status_with_browser_closed(client: AsyncClient) -> None:
    response = await client.get("/api/session/status")

    assert response.json() == {
        "browser_open": False,
        "logged_in": False,
        "account_id": None,
        "page": None,
        "challenge_required": False,
        "consent_required": False,
        "busy": False,
    }


async def test_unknown_job_is_404(client: AsyncClient) -> None:
    for path in ("/api/jobs/9", "/api/jobs/9/items", "/api/jobs/9/events", "/api/jobs/9/report"):
        assert (await client.get(path)).status_code == 404, path


async def test_preview_requires_a_logged_in_session(client: AsyncClient) -> None:
    response = await client.post("/api/jobs", json={})

    assert response.status_code == 409
    assert "Connecte-toi" in response.json()["detail"]


async def test_invalid_criteria_are_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/jobs", json={"start_date": "2026-06-01", "end_date": "2026-01-01"}
    )

    assert response.status_code == 422


# --- Parcours complet (navigateur sans fenêtre, faux Instagram) -----------------------------


@pytest.mark.browser
async def test_full_flow_from_preview_to_report(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    likes = make_likes(6)
    await connect(app, client, fake_instagram, likes)
    status = (await client.get("/api/session/status")).json()
    assert (status["logged_in"], status["account_id"]) == (True, ACCOUNT)

    job_id = await create_preview(app, client)
    job = (await client.get(f"/api/jobs/{job_id}")).json()
    assert (job["status"], job["to_process"], job["running"]) == ("ready", 6, False)

    page = (await client.get(f"/api/jobs/{job_id}/items?limit=4")).json()
    assert (len(page["items"]), page["total"]) == (4, 6)
    assert page["items"][0]["rank"] == 1
    assert page["items"][0]["media_key"] == likes[0].key

    excluded_id = page["items"][1]["id"]
    patch = await client.patch(
        f"/api/jobs/{job_id}/items", json={"item_ids": [excluded_id], "excluded": True}
    )
    assert patch.json()["changed"] == 1
    assert patch.json()["job"]["to_process"] == 5

    started = await client.post(f"/api/jobs/{job_id}/start")
    assert started.status_code == 202
    await api_state(app).runner.wait()

    job = (await client.get(f"/api/jobs/{job_id}")).json()
    assert job["status"] == "completed"
    assert fake_instagram.unliked == [like.key for like in likes if like.key != likes[1].key]

    report = (await client.get(f"/api/jobs/{job_id}/report")).json()
    assert report["par_statut"] == {"done": 5, "excluded": 1}
    csv_report = await client.get(f"/api/jobs/{job_id}/report?format=csv")
    assert csv_report.headers["content-type"].startswith("text/csv")
    assert "retiré" in csv_report.text

    # Une fois la tâche finie, le flux rejoue ses événements puis se termine.
    events = (await client.get(f"/api/jobs/{job_id}/events")).text
    assert events.startswith("event: snapshot")
    assert events.count("event: batch") == 2
    assert '"ok": true' in events.split("event: end")[-1]


@pytest.mark.browser
async def test_events_stream_follows_a_running_cleanup(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    await connect(app, client, fake_instagram, make_likes(8))
    job_id = await create_preview(app, client)

    await client.post(f"/api/jobs/{job_id}/start")
    stream = await client.get(f"/api/jobs/{job_id}/events")  # se termine avec « end »

    text = stream.text
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert text.index("event: status") < text.index("event: batch") < text.index("event: end")
    assert '"total": 8' in text
    assert '"reason": "completed"' in text


@pytest.mark.browser
async def test_pause_then_resume(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    state = api_state(app)
    await connect(app, client, fake_instagram, make_likes(8))
    job_id = await create_preview(app, client)
    state.settings.delay_min = state.settings.delay_max = 30  # longue pause après chaque lot

    await client.post(f"/api/jobs/{job_id}/start")
    while not fake_instagram.unliked:
        await asyncio.sleep(0.05)
    paused = await client.post(f"/api/jobs/{job_id}/pause")
    await state.runner.wait()

    assert paused.status_code == 202
    job = (await client.get(f"/api/jobs/{job_id}")).json()
    assert (job["status"], job["to_process"]) == ("paused", 4)
    assert (await client.post(f"/api/jobs/{job_id}/pause")).status_code == 409

    state.settings.delay_min, state.settings.delay_max = 0, 0.05
    resumed = await client.post(f"/api/jobs/{job_id}/resume")
    await state.runner.wait()

    assert resumed.status_code == 202
    assert (await client.get(f"/api/jobs/{job_id}")).json()["status"] == "completed"
    assert len(fake_instagram.unliked) == 8


@pytest.mark.browser
async def test_stop_a_running_cleanup(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    state = api_state(app)
    await connect(app, client, fake_instagram, make_likes(8))
    job_id = await create_preview(app, client)
    state.settings.delay_min = state.settings.delay_max = 30

    await client.post(f"/api/jobs/{job_id}/start")
    while not fake_instagram.unliked:
        await asyncio.sleep(0.05)
    await client.post(f"/api/jobs/{job_id}/stop")
    await state.runner.wait()

    job = (await client.get(f"/api/jobs/{job_id}")).json()
    assert (job["status"], job["to_process"]) == ("stopped", 4)
    assert (await client.post(f"/api/jobs/{job_id}/resume")).status_code == 409


@pytest.mark.browser
async def test_one_task_at_a_time(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    await connect(app, client, fake_instagram, make_likes(60))

    first = await client.post("/api/jobs", json={})
    second = await client.post("/api/jobs", json={})
    status = (await client.get("/api/session/status")).json()
    await api_state(app).runner.wait()

    assert first.status_code == 202
    assert second.status_code == 409
    assert status["busy"] is True


@pytest.mark.browser
async def test_stop_a_ready_job_without_running_it(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    await connect(app, client, fake_instagram, make_likes(3))
    job_id = await create_preview(app, client)

    stopped = await client.post(f"/api/jobs/{job_id}/stop")

    assert stopped.json()["status"] == "stopped"
    assert fake_instagram.unliked == []


@pytest.mark.browser
async def test_failed_preview_ends_the_stream_with_a_message(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    await connect(app, client, fake_instagram, make_likes(3))
    fake_instagram.serve_likes(make_likes(3), blocking_dialog_after_ms=0)

    job_id = await create_preview(app, client)

    assert (await client.get(f"/api/jobs/{job_id}")).json()["status"] == "failed"
    events = (await client.get(f"/api/jobs/{job_id}/events")).text
    assert '"ok": false' in events
    assert "recouvre la page des likes" in events


@pytest.mark.browser
async def test_delete_session_and_local_data(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    state = api_state(app)
    await connect(app, client, fake_instagram, make_likes(3))
    await create_preview(app, client)

    session_deleted = await client.delete("/api/session")
    assert session_deleted.status_code == 200
    assert not (await client.get("/api/session/status")).json()["browser_open"]
    assert not state.settings.browser_profile_dir.exists()

    data_deleted = await client.delete("/api/data")
    assert data_deleted.status_code == 200
    assert any(path.endswith("iuc.db") for path in data_deleted.json()["deleted"])
    assert (await client.get("/api/jobs")).json() == []  # base neuve, toujours utilisable


@pytest.mark.browser
async def test_authors_come_from_collected_previews(
    app: FastAPI, client: AsyncClient, fake_instagram: FakeInstagram
) -> None:
    assert (await client.get("/api/authors")).json() == []
    await connect(app, client, fake_instagram, make_likes(8))
    await create_preview(app, client)

    authors = (await client.get("/api/authors")).json()

    assert authors == [
        {"author": "auteur.b", "likes": 2},
        {"author": "auteur_a", "likes": 2},
        {"author": "auteur_c", "likes": 2},
        {"author": "auteur_d", "likes": 2},
    ]
