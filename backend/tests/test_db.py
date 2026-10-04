from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlmodel import Session, select

from app.core.db import init_db, make_engine
from app.models.tables import DailyCounter, EventLog, Job, LikedItem


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    # Un espace dans le chemin, comme dans le dossier du projet.
    db_dir = tmp_path / "dossier avec espace"
    db_dir.mkdir()
    engine = make_engine(db_dir / "test.db")
    init_db(engine)
    yield engine
    engine.dispose()


def test_creates_all_tables(engine: Engine) -> None:
    assert set(inspect(engine).get_table_names()) == {
        "job",
        "liked_item",
        "daily_counter",
        "event_log",
    }


def test_init_db_is_idempotent(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(Job())
        session.commit()

    init_db(engine)

    with Session(engine) as session:
        assert len(session.exec(select(Job)).all()) == 1


def test_job_round_trip_keeps_filters_and_utc_dates(engine: Engine) -> None:
    filters = {"type": "reels", "before": "2024-01-01", "authors": ["compte_a"]}
    paris = timezone(timedelta(hours=2))
    started = datetime(2026, 10, 4, 18, 30, tzinfo=paris)

    with Session(engine) as session:
        job = Job(filters=filters, started_at=started)
        session.add(job)
        session.commit()
        job_id = job.id

    with Session(engine) as session:
        stored = session.get(Job, job_id)
        assert stored is not None
        assert stored.filters == filters
        assert stored.created_at.tzinfo == UTC
        assert stored.started_at == started  # même instant, converti en UTC
        assert stored.started_at is not None and stored.started_at.hour == 16


def test_rejects_naive_datetime(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(Job(started_at=datetime(2026, 10, 4, 12, 0)))
        with pytest.raises(StatementError, match="fuseau"):
            session.commit()


def test_same_url_cannot_be_targeted_twice_by_a_job(engine: Engine) -> None:
    with Session(engine) as session:
        job = Job()
        session.add(job)
        session.commit()
        assert job.id is not None
        session.add(LikedItem(job_id=job.id, url="https://www.instagram.com/p/abc/"))
        session.add(LikedItem(job_id=job.id, url="https://www.instagram.com/p/abc/"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_foreign_keys_are_enforced(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(LikedItem(job_id=999, url="https://www.instagram.com/p/abc/"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_a_job_deletes_its_items_and_events(engine: Engine) -> None:
    with Session(engine) as session:
        job = Job()
        session.add(job)
        session.commit()
        assert job.id is not None
        session.add(LikedItem(job_id=job.id, url="https://www.instagram.com/reel/xyz/"))
        session.add(EventLog(job_id=job.id, message="collecte terminée"))
        session.commit()

        session.delete(job)
        session.commit()

        assert session.exec(select(LikedItem)).all() == []
        assert session.exec(select(EventLog)).all() == []


def test_daily_counter_is_keyed_by_day(engine: Engine) -> None:
    today = datetime.now().date()
    with Session(engine) as session:
        session.add(DailyCounter(day=today, unlike_count=3))
        session.commit()
        session.add(DailyCounter(day=today))
        with pytest.raises(IntegrityError):
            session.commit()
