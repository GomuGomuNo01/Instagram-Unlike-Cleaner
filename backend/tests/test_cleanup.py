"""Nettoyage par lots sur la fausse page des likes : retraits, limites, alertes, reprise."""

import asyncio
import random
import time
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.browser import selection
from app.browser.session import BrowserSession, NavigationOutcome
from app.core.config import Settings
from app.core.db import init_db, make_engine
from app.core.logs import LOG_FILE_NAME, setup_logging
from app.models.schemas import CleanupFilters
from app.models.tables import EventLog, ItemStatus, Job, JobStatus, LikedItem
from app.services.cleanup import (
    STOP_MESSAGES,
    CleanupControl,
    StopReason,
    run_cleanup,
    today_count,
)
from app.services.jobs import JobActionRefused, set_excluded, stop_job
from app.services.preview import run_preview
from tests.fake_instagram import FakeInstagram, FakeLike, log_in, make_likes

pytestmark = [pytest.mark.anyio, pytest.mark.browser]

ACCOUNT = "42"


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = make_engine(tmp_path / "iuc.db")
    init_db(engine)
    yield engine
    engine.dispose()


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


async def prepare(
    session: BrowserSession,
    fake_instagram: FakeInstagram,
    engine: Engine,
    likes: list[FakeLike],
    filters: CleanupFilters | None = None,
    **page_options: str,
) -> int:
    """Crée un aperçu, puis rouvre la page des likes, comme deux commandes successives."""
    fake_instagram.serve_likes(likes, **page_options)
    await log_in(session.context, account_id=ACCOUNT)
    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK
    result = await run_preview(session, engine, filters or CleanupFilters(), account_id=ACCOUNT)
    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK
    return result.job_id


def statuses(engine: Engine, job_id: int) -> dict[str, ItemStatus]:
    with Session(engine) as db:
        items = db.exec(
            select(LikedItem).where(LikedItem.job_id == job_id).order_by(col(LikedItem.position))
        ).all()
        return {item.media_key: item.status for item in items}


def job_status(engine: Engine, job_id: int) -> JobStatus:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        assert job is not None
        return job.status


def unlike_requests(fake_instagram: FakeInstagram) -> list[str]:
    return [path for path in fake_instagram.requested_paths if path.startswith("/__unlike__/")]


async def test_removes_all_validated_likes_in_batches(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    likes = make_likes(10)
    job_id = await prepare(session, fake_instagram, engine, likes)
    batches: list[int] = []

    result = await run_cleanup(
        session,
        engine,
        make_settings(tmp_path),
        job_id,
        account_id=ACCOUNT,
        on_batch=lambda removed, _total: batches.append(removed),
    )

    assert result.reason is StopReason.COMPLETED
    assert (result.done, result.failed, result.skipped, result.remaining) == (10, 0, 0, 0)
    assert batches == [4, 4, 2]
    assert fake_instagram.unliked == [like.key for like in likes]
    assert set(statuses(engine, job_id).values()) == {ItemStatus.DONE}
    assert job_status(engine, job_id) is JobStatus.COMPLETED
    assert today_count(engine) == 10


async def test_excluded_likes_are_never_removed(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    likes = make_likes(8)
    job_id = await prepare(session, fake_instagram, engine, likes)
    set_excluded(engine, job_id, ranks=[2], authors=["@auteur_a"])

    result = await run_cleanup(session, engine, make_settings(tmp_path), job_id, account_id=ACCOUNT)

    kept = {likes[1].key} | {like.key for like in likes if like.author == "auteur_a"}
    assert result.reason is StopReason.COMPLETED
    assert set(fake_instagram.unliked) == {like.key for like in likes} - kept
    assert {
        key for key, status in statuses(engine, job_id).items() if status is ItemStatus.EXCLUDED
    } == kept


async def test_run_limit_pauses_then_resume_finishes(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    likes = make_likes(7)
    job_id = await prepare(session, fake_instagram, engine, likes)
    settings = make_settings(tmp_path)

    first = await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT, max_unlikes=3)

    assert (first.reason, first.done, first.remaining) == (StopReason.RUN_LIMIT, 3, 4)
    assert job_status(engine, job_id) is JobStatus.PAUSED
    assert fake_instagram.unliked == [like.key for like in likes[:3]]

    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK
    second = await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)

    assert (second.reason, second.done, second.remaining) == (StopReason.COMPLETED, 4, 0)
    assert fake_instagram.unliked == [like.key for like in likes]


async def test_daily_limit_is_shared_and_respected(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(10))
    settings = make_settings(tmp_path, daily_limit=5)

    first = await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)
    second = await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)

    assert (first.reason, first.done) == (StopReason.DAILY_LIMIT, 5)
    assert (second.reason, second.done) == (StopReason.DAILY_LIMIT, 0)
    assert len(fake_instagram.unliked) == 5
    assert today_count(engine) == 5


async def test_blocked_action_pauses_without_removing(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(6), unlike="blocked")
    settings = make_settings(tmp_path)

    result = await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)

    assert result.reason is StopReason.ACTION_BLOCKED
    assert result.detail is not None and "Réessayer plus tard" in result.detail
    assert set(statuses(engine, job_id).values()) == {ItemStatus.SELECTED}
    assert job_status(engine, job_id) is JobStatus.PAUSED
    assert list(settings.diagnostics_dir.glob("*apres-unlike.txt"))


async def test_unknown_confirmation_is_never_confirmed(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(6), confirm="unknown")

    result = await run_cleanup(session, engine, make_settings(tmp_path), job_id, account_id=ACCOUNT)

    assert result.reason is StopReason.UNKNOWN_DIALOG
    assert result.detail is not None and "Supprimer" in result.detail
    assert unlike_requests(fake_instagram) == []
    assert set(statuses(engine, job_id).values()) == {ItemStatus.SELECTED}


async def test_likes_still_shown_are_marked_failed(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    likes = make_likes(6)
    job_id = await prepare(session, fake_instagram, engine, likes, unlike="silent")

    result = await run_cleanup(session, engine, make_settings(tmp_path), job_id, account_id=ACCOUNT)

    assert (result.reason, result.done, result.failed) == (StopReason.NOT_REMOVED, 0, 4)
    first_batch = [like.key for like in likes[:4]]
    assert [statuses(engine, job_id)[key] for key in first_batch] == [ItemStatus.FAILED] * 4
    assert job_status(engine, job_id) is JobStatus.PAUSED


async def test_likes_back_after_reload_are_marked_failed(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    # Instagram retire les vignettes de l'écran sans enregistrer le retrait.
    job_id = await prepare(session, fake_instagram, engine, make_likes(6), unlike="revert")

    result = await run_cleanup(session, engine, make_settings(tmp_path), job_id, account_id=ACCOUNT)

    assert (result.reason, result.done, result.failed) == (StopReason.COMPLETED, 0, 6)
    assert set(statuses(engine, job_id).values()) == {ItemStatus.FAILED}
    with Session(engine) as db:
        errors = {item.error for item in db.exec(select(LikedItem)).all()}
    assert errors == {"réapparu après rechargement : Instagram n'a pas retiré ce like"}


async def test_like_gone_since_preview_is_skipped(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    likes = make_likes(5)
    job_id = await prepare(session, fake_instagram, engine, likes)
    fake_instagram.delete_like(likes[2].key)
    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK

    result = await run_cleanup(session, engine, make_settings(tmp_path), job_id, account_id=ACCOUNT)

    assert (result.reason, result.done, result.skipped) == (StopReason.COMPLETED, 4, 1)
    assert statuses(engine, job_id)[likes[2].key] is ItemStatus.SKIPPED


async def test_refuses_another_account(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(3))

    with pytest.raises(JobActionRefused, match="autre compte"):
        await run_cleanup(session, engine, make_settings(tmp_path), job_id, account_id="99")

    assert job_status(engine, job_id) is JobStatus.READY
    assert unlike_requests(fake_instagram) == []


async def test_interruption_pauses_the_job(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(8))
    settings = make_settings(tmp_path, delay_min=5, delay_max=5)  # longue pause après un lot
    cleanup = asyncio.create_task(
        run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)
    )
    while not fake_instagram.unliked:
        await asyncio.sleep(0.05)
    await asyncio.sleep(1.0)  # le premier lot est enregistré, la pause a commencé

    cleanup.cancel()
    with pytest.raises(asyncio.CancelledError):
        await cleanup

    assert job_status(engine, job_id) is JobStatus.PAUSED
    assert len(fake_instagram.unliked) == 4


async def test_requested_pause_waits_for_the_batch_and_skips_the_long_delay(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(8))
    settings = make_settings(tmp_path, delay_min=30, delay_max=30)
    control = CleanupControl()
    started = time.monotonic()

    result = await run_cleanup(
        session,
        engine,
        settings,
        job_id,
        account_id=ACCOUNT,
        on_batch=lambda _removed, _total: control.request_pause(),
        control=control,
    )

    assert time.monotonic() - started < 25  # la pause de 30 s entre lots a été écourtée
    assert (result.reason, result.done, result.remaining) == (StopReason.USER_PAUSE, 4, 4)
    assert job_status(engine, job_id) is JobStatus.PAUSED
    assert len(fake_instagram.unliked) == 4


async def test_requested_stop_abandons_the_remaining_likes(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(8))
    control = CleanupControl()

    result = await run_cleanup(
        session,
        engine,
        make_settings(tmp_path),
        job_id,
        account_id=ACCOUNT,
        on_batch=lambda _removed, _total: control.request_stop(),
        control=control,
    )

    assert (result.reason, result.done, result.remaining) == (StopReason.USER_STOP, 4, 4)
    assert job_status(engine, job_id) is JobStatus.STOPPED
    assert list(statuses(engine, job_id).values()).count(ItemStatus.SELECTED) == 4


async def test_stop_from_another_terminal_is_noticed(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(8))

    def stop_elsewhere(_removed: int, _total: int) -> None:
        # Équivalent de `iuc stop` lancé dans un autre terminal pendant le premier lot.
        stop_job(engine, job_id)

    result = await run_cleanup(
        session,
        engine,
        make_settings(tmp_path),
        job_id,
        account_id=ACCOUNT,
        on_batch=stop_elsewhere,
    )

    assert (result.reason, result.done) == (StopReason.USER_STOP, 4)
    assert job_status(engine, job_id) is JobStatus.STOPPED
    assert len(fake_instagram.unliked) == 4


# --- Alertes d'Instagram : arrêt immédiat, nettoyage en pause, message explicite ------------


@pytest.mark.parametrize(
    ("location", "reason"),
    [("/accounts/login/", StopReason.LOGGED_OUT), ("/challenge/", StopReason.CHALLENGE)],
    ids=["deconnexion-forcee", "verification-de-securite"],
)
async def test_instagram_signal_between_batches_pauses_at_once(
    session: BrowserSession,
    fake_instagram: FakeInstagram,
    engine: Engine,
    tmp_path: Path,
    location: str,
    reason: StopReason,
) -> None:
    likes = make_likes(10)
    job_id = await prepare(session, fake_instagram, engine, likes)

    def instagram_reacts(_removed: int, _total: int) -> None:
        fake_instagram.likes_redirect = location

    result = await run_cleanup(
        session,
        engine,
        make_settings(tmp_path),
        job_id,
        account_id=ACCOUNT,
        on_batch=instagram_reacts,
    )

    assert result.reason is reason
    assert fake_instagram.unliked == [like.key for like in likes[:4]]  # rien après le signal
    assert job_status(engine, job_id) is JobStatus.PAUSED
    assert list(statuses(engine, job_id).values()).count(ItemStatus.SELECTED) == 6
    # Message à l'utilisateur : la marche à suivre, enregistrée dans le journal du nettoyage.
    with Session(engine) as db:
        messages = [event.message for event in db.exec(select(EventLog)).all()]
    assert any(message.startswith(STOP_MESSAGES[reason]) for message in messages)


async def test_limit_window_on_reload_pauses_at_once(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    likes = make_likes(10)
    job_id = await prepare(session, fake_instagram, engine, likes)

    def instagram_limits(_removed: int, _total: int) -> None:
        fake_instagram.alert_on_load = (
            "Réessayer plus tard. Nous limitons la fréquence de certaines actions."
        )

    result = await run_cleanup(
        session,
        engine,
        make_settings(tmp_path),
        job_id,
        account_id=ACCOUNT,
        on_batch=instagram_limits,
    )

    assert result.reason is StopReason.ACTION_BLOCKED
    assert result.detail is not None and "Réessayer plus tard" in result.detail
    assert fake_instagram.unliked == [like.key for like in likes[:4]]
    assert job_status(engine, job_id) is JobStatus.PAUSED


async def test_changed_interface_pauses_and_names_the_missing_element(
    session: BrowserSession,
    fake_instagram: FakeInstagram,
    engine: Engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(selection, "TIMEOUT_MS", 800)
    # Le bouton « Je n’aime plus » a été renommé dans une nouvelle version d'Instagram.
    job_id = await prepare(session, fake_instagram, engine, make_likes(6), unlike_label="Retirer")
    settings = make_settings(tmp_path)

    result = await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)

    assert result.reason is StopReason.LAYOUT_CHANGED
    assert result.detail is not None and "Je n’aime plus" in result.detail
    assert unlike_requests(fake_instagram) == []
    assert job_status(engine, job_id) is JobStatus.PAUSED
    assert list(settings.diagnostics_dir.glob("*interface.txt"))


# --- Cadence : délais aléatoires entre actions et entre lots ------------------------------


async def test_pauses_are_drawn_at_random_within_their_bounds(
    session: BrowserSession,
    fake_instagram: FakeInstagram,
    engine: Engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = await prepare(session, fake_instagram, engine, make_likes(8))
    settings = make_settings(tmp_path, delay_min=0.01, delay_max=0.05)
    draws: list[tuple[float, float]] = []
    uniform = random.uniform

    def spy(low: float, high: float) -> float:
        draws.append((low, high))
        value = uniform(low, high)
        assert low <= value <= high
        return value

    monkeypatch.setattr(random, "uniform", spy)

    await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)

    assert draws.count(selection.CLICK_PAUSE) == 8  # entre deux cases cochées
    assert draws.count((settings.delay_min, settings.delay_max)) == 2  # après chaque lot


# --- Journaux : aucune donnée personnelle inutile -----------------------------------------


async def test_logs_never_name_the_liked_accounts(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine, tmp_path: Path
) -> None:
    settings = make_settings(tmp_path, log_level="DEBUG")
    settings.ensure_dirs()
    setup_logging(settings)
    likes = [replace(like, author="compte_canari") for like in make_likes(6)]
    job_id = await prepare(session, fake_instagram, engine, likes)

    await run_cleanup(session, engine, settings, job_id, account_id=ACCOUNT)

    log = (settings.logs_dir / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "Nettoyage n°" in log  # le journal est bien écrit, au niveau le plus détaillé
    assert "compte_canari" not in log
    assert "faux-jeton" not in log  # valeur du cookie de session
