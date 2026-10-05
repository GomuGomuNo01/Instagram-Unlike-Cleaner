"""Aperçu complet : collecte sur la fausse page, enregistrement en base et export CSV."""

import csv
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, select

from app.browser import locators
from app.browser.session import BrowserSession, NavigationOutcome
from app.core.db import init_db, make_engine
from app.models.schemas import CleanupFilters, ContentFilter
from app.models.tables import EventLog, ItemStatus, Job, JobStatus, LikedItem, MediaKind
from app.services.preview import (
    PreviewError,
    export_csv,
    pending_items,
    run_preview,
    summarize,
)
from tests.fake_instagram import FakeInstagram, interactive_likes_page, log_in, make_likes


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = make_engine(tmp_path / "iuc.db")
    init_db(engine)
    yield engine
    engine.dispose()


async def open_page(session: BrowserSession, fake_instagram: FakeInstagram, body: str) -> None:
    fake_instagram.page(locators.LIKES_PATH, body)
    await log_in(session.context)
    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK


def job_events(engine: Engine, job_id: int) -> list[EventLog]:
    with Session(engine) as db:
        return list(db.exec(select(EventLog).where(EventLog.job_id == job_id)).all())


@pytest.mark.anyio
@pytest.mark.browser
async def test_run_preview_saves_only_targeted_likes(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine
) -> None:
    likes = make_likes(30)
    await open_page(session, fake_instagram, interactive_likes_page(likes))
    filters = CleanupFilters(content=ContentFilter.REELS, exclude_authors=("auteur_a",))

    result = await run_preview(session, engine, filters, account_id="42")

    expected = [
        (position, like.key)
        for position, like in enumerate(likes)
        if like.kind == "Vidéo" and like.author != "auteur_a"
    ]
    assert (result.scanned, result.targeted) == (30, len(expected))
    items = pending_items(engine, result.job_id)
    assert [(item.position, item.media_key) for item in items] == expected
    assert {item.media_kind for item in items} == {MediaKind.VIDEO}
    with Session(engine) as db:
        job = db.get(Job, result.job_id)
        assert job is not None
        assert job.status is JobStatus.READY
        assert job.account_id == "42"
        assert CleanupFilters.model_validate(job.filters) == filters
    assert any("Aperçu prêt" in event.message for event in job_events(engine, result.job_id))


@pytest.mark.anyio
@pytest.mark.browser
async def test_interrupted_collection_marks_the_job_failed(
    session: BrowserSession, fake_instagram: FakeInstagram, engine: Engine
) -> None:
    page = interactive_likes_page(make_likes(80), blocking_dialog_after_ms=1000)
    await open_page(session, fake_instagram, page)

    with pytest.raises(PreviewError, match="fenêtre"):
        await run_preview(session, engine, CleanupFilters(), account_id="42")

    with Session(engine) as db:
        [job] = db.exec(select(Job)).all()
        assert job.status is JobStatus.FAILED
        assert job.finished_at is not None
        assert db.exec(select(LikedItem)).all() == []
    assert job.id is not None
    assert [event.level for event in job_events(engine, job.id)] == ["INFO", "ERROR"]


def make_item(position: int, author: str | None, kind: MediaKind | None) -> LikedItem:
    return LikedItem(
        job_id=1,
        media_key=f"{position}_1_1_n",
        position=position,
        label="libellé",
        author=author,
        media_kind=kind,
        published_on=date(2026, 10, 3),
        status=ItemStatus.PENDING,
    )


def test_summarize_counts_types_and_authors() -> None:
    items = [
        make_item(0, "auteur_a", MediaKind.VIDEO),
        make_item(1, "auteur_a", MediaKind.PHOTO),
        make_item(2, "auteur_b", MediaKind.VIDEO),
        make_item(3, None, None),
    ]

    summary = summarize(items, top=1)

    assert summary.total == 4
    assert summary.by_kind == {MediaKind.VIDEO: 2, MediaKind.PHOTO: 1, None: 1}
    assert summary.top_authors == [("auteur_a", 2)]


def test_export_csv_is_readable_by_excel(tmp_path: Path) -> None:
    items = [make_item(0, "auteur_a", MediaKind.VIDEO), make_item(4, None, MediaKind.CAROUSEL)]

    path = export_csv(items, tmp_path / "rapports" / "apercu-1.csv")

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM : Excel lit l'UTF-8
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file, delimiter=";"))
    assert rows == [
        ["rang", "auteur", "type", "partagée le (selon Instagram)", "identifiant"],
        ["1", "@auteur_a", "vidéo", "03/10/2026", "0_1_1_n"],
        ["5", "", "carrousel", "03/10/2026", "4_1_1_n"],
    ]
