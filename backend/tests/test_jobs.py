"""Vue d'ensemble, exclusions et lancement d'un nettoyage (base seule, sans navigateur)."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, select

from app.core.db import init_db, make_engine
from app.models.schemas import CleanupFilters
from app.models.tables import EventLog, ItemStatus, Job, JobStatus, LikedItem, MediaKind
from app.services.cleanup import start_job
from app.services.jobs import (
    JobActionRefused,
    job_overview,
    known_authors,
    list_jobs,
    set_excluded,
    stop_job,
)


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = make_engine(tmp_path / "iuc.db")
    init_db(engine)
    yield engine
    engine.dispose()


def make_job(engine: Engine, status: JobStatus, authors: list[str | None]) -> int:
    with Session(engine) as db:
        job = Job(filters=CleanupFilters().model_dump(mode="json"), account_id="42", status=status)
        db.add(job)
        db.flush()
        assert job.id is not None
        for position, author in enumerate(authors):
            db.add(
                LikedItem(
                    job_id=job.id,
                    media_key=f"{position}_1_1_n",
                    position=position,
                    label="libellé",
                    author=author,
                    media_kind=MediaKind.VIDEO,
                    published_on=date(2026, 10, 3),
                )
            )
        db.commit()
        return job.id


def item_statuses(engine: Engine, job_id: int) -> list[ItemStatus]:
    with Session(engine) as db:
        items = db.exec(select(LikedItem).where(LikedItem.job_id == job_id)).all()
        return [item.status for item in sorted(items, key=lambda item: item.position)]


def test_exclude_by_rank_and_author_then_restore(engine: Engine) -> None:
    job_id = make_job(engine, JobStatus.READY, ["a", "b", "a", "c"])

    assert set_excluded(engine, job_id, ranks=[2], authors=["@A"]) == 3
    assert item_statuses(engine, job_id) == [
        ItemStatus.EXCLUDED,
        ItemStatus.EXCLUDED,
        ItemStatus.EXCLUDED,
        ItemStatus.PENDING,
    ]

    assert set_excluded(engine, job_id, ranks=[1], authors=[], restore=True) == 1
    assert item_statuses(engine, job_id)[0] is ItemStatus.PENDING


def test_restore_on_paused_job_puts_likes_back_to_remove(engine: Engine) -> None:
    job_id = make_job(engine, JobStatus.PAUSED, ["a"])
    set_excluded(engine, job_id, ranks=[1], authors=[])

    set_excluded(engine, job_id, ranks=[1], authors=[], restore=True)

    assert item_statuses(engine, job_id) == [ItemStatus.SELECTED]


@pytest.mark.parametrize("status", [JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED])
def test_exclusions_are_frozen_outside_ready_or_paused(engine: Engine, status: JobStatus) -> None:
    job_id = make_job(engine, status, ["a"])

    with pytest.raises(JobActionRefused):
        set_excluded(engine, job_id, ranks=[1], authors=[])


def test_overview_counts_items_by_status(engine: Engine) -> None:
    job_id = make_job(engine, JobStatus.READY, ["a", "b", "c"])
    set_excluded(engine, job_id, ranks=[3], authors=[])

    overview = job_overview(engine, job_id)

    assert overview is not None
    assert overview.counts == {ItemStatus.PENDING: 2, ItemStatus.EXCLUDED: 1}
    assert overview.to_process == 2
    assert [job.id for job in list_jobs(engine)] == [job_id]
    assert job_overview(engine, 999) is None


def test_first_start_validates_the_preview(engine: Engine) -> None:
    job_id = make_job(engine, JobStatus.READY, ["a", "b"])
    set_excluded(engine, job_id, ranks=[2], authors=[])

    start_job(engine, job_id, account_id="42")

    assert item_statuses(engine, job_id) == [ItemStatus.SELECTED, ItemStatus.EXCLUDED]
    with Session(engine) as db:
        job = db.get(Job, job_id)
        assert job is not None
        assert job.status is JobStatus.RUNNING
        assert job.started_at is not None


def test_start_after_a_crash_resumes(engine: Engine) -> None:
    job_id = make_job(engine, JobStatus.RUNNING, ["a"])

    start_job(engine, job_id, account_id="42")

    with Session(engine) as db:
        messages = [event.message for event in db.exec(select(EventLog)).all()]
    assert any("interrompue" in message for message in messages)


@pytest.mark.parametrize(
    ("status", "account", "message"),
    [
        (JobStatus.COMPLETED, "42", "rien à lancer"),
        (JobStatus.READY, "99", "autre compte"),
    ],
)
def test_start_refusals(engine: Engine, status: JobStatus, account: str, message: str) -> None:
    job_id = make_job(engine, status, ["a"])

    with pytest.raises(JobActionRefused, match=message):
        start_job(engine, job_id, account_id=account)


@pytest.mark.parametrize("status", [JobStatus.READY, JobStatus.PAUSED, JobStatus.RUNNING])
def test_stop_job(engine: Engine, status: JobStatus) -> None:
    job_id = make_job(engine, status, ["a"])

    assert stop_job(engine, job_id) is status

    with Session(engine) as db:
        job = db.get(Job, job_id)
        assert job is not None
        assert job.status is JobStatus.STOPPED
        assert job.finished_at is not None
    with pytest.raises(JobActionRefused, match="rien à lancer"):
        start_job(engine, job_id, account_id="42")


@pytest.mark.parametrize("status", [JobStatus.COMPLETED, JobStatus.STOPPED, JobStatus.FAILED])
def test_stop_refused_once_finished(engine: Engine, status: JobStatus) -> None:
    job_id = make_job(engine, status, ["a"])

    with pytest.raises(JobActionRefused, match="rien à arrêter"):
        stop_job(engine, job_id)


def test_known_authors_counts_likes_still_in_place(engine: Engine) -> None:
    first = make_job(engine, JobStatus.READY, ["a", "b", "a", None])
    second = make_job(engine, JobStatus.COMPLETED, ["a"])
    with Session(engine) as db:
        # Le like « 0_1_1_n » (auteur a) a été retiré par le second nettoyage.
        removed = db.exec(select(LikedItem).where(LikedItem.job_id == second)).one()
        removed.status = ItemStatus.DONE
        db.add(removed)
        db.commit()

    assert known_authors(engine, "42") == [("a", 1), ("b", 1)]
    assert known_authors(engine, "autre compte") == []
    assert first != second
