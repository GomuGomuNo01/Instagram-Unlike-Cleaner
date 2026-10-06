"""Rapport d'un nettoyage : bilan, durée active, exports CSV et JSON (base seule)."""

import csv
import json
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlmodel import Session

from app.core.db import init_db, make_engine
from app.models.schemas import CleanupFilters, SortOrder
from app.models.tables import EventLog, ItemStatus, Job, JobStatus, LikedItem, MediaKind
from app.services.cleanup import RUN_INTERRUPTED_EVENT, RUN_STARTED_EVENT, STOP_MESSAGES, StopReason
from app.services.jobs import JobActionRefused
from app.services.report import (
    build_report,
    export_report_csv,
    export_report_json,
    format_duration,
    summary_lines,
)

T0 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
STATUSES = [
    (ItemStatus.DONE, None),
    (ItemStatus.DONE, None),
    (ItemStatus.FAILED, "toujours affiché après « Je n’aime plus »"),
    (ItemStatus.SKIPPED, "introuvable dans la grille"),
    (ItemStatus.EXCLUDED, None),
    (ItemStatus.SELECTED, None),
]


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = make_engine(tmp_path / "iuc.db")
    init_db(engine)
    yield engine
    engine.dispose()


def make_job(engine: Engine, events: list[tuple[timedelta, str]]) -> int:
    with Session(engine) as db:
        job = Job(
            filters=CleanupFilters(sort=SortOrder.OLDEST_FIRST).model_dump(mode="json"),
            account_id="42",
            status=JobStatus.PAUSED,
            created_at=T0,
            started_at=T0 + timedelta(minutes=1),
        )
        db.add(job)
        db.flush()
        assert job.id is not None
        for position, (status, error) in enumerate(STATUSES):
            db.add(
                LikedItem(
                    job_id=job.id,
                    media_key=f"{position}_1_1_n",
                    position=position,
                    label="libellé",
                    author=f"auteur_{position}",
                    media_kind=MediaKind.VIDEO,
                    published_on=date(2026, 10, 3),
                    status=status,
                    error=error,
                    processed_at=T0 + timedelta(minutes=2) if status is ItemStatus.DONE else None,
                )
            )
        for offset, message in events:
            db.add(EventLog(job_id=job.id, timestamp=T0 + offset, message=message))
        db.commit()
        return job.id


def test_report_counts_and_problems(engine: Engine) -> None:
    job_id = make_job(engine, [])

    report = build_report(engine, job_id)

    assert report.targeted == 6
    assert report.counts == {
        ItemStatus.DONE: 2,
        ItemStatus.FAILED: 1,
        ItemStatus.SKIPPED: 1,
        ItemStatus.EXCLUDED: 1,
        ItemStatus.SELECTED: 1,
    }
    assert [(line.rank, line.status) for line in report.problems] == [
        (3, ItemStatus.FAILED),
        (4, ItemStatus.SKIPPED),
    ]
    assert report.filters.sort is SortOrder.OLDEST_FIRST


def test_active_time_adds_up_runs_and_ignores_interrupted_ones(engine: Engine) -> None:
    job_id = make_job(
        engine,
        [
            (timedelta(minutes=1), "Aperçu validé : 6 likes à retirer"),
            (timedelta(minutes=1), RUN_STARTED_EVENT),
            (timedelta(minutes=4), STOP_MESSAGES[StopReason.DAILY_LIMIT]),
            # Le lendemain : une exécution interrompue brutalement, puis une reprise complète.
            (timedelta(days=1), RUN_STARTED_EVENT),
            (timedelta(days=1, hours=2), f"{RUN_INTERRUPTED_EVENT} : reprise"),
            (timedelta(days=1, hours=2), RUN_STARTED_EVENT),
            (timedelta(days=1, hours=2, minutes=10), STOP_MESSAGES[StopReason.USER_PAUSE]),
        ],
    )

    report = build_report(engine, job_id)

    assert report.runs == 3
    assert report.active_time == timedelta(minutes=13)  # 3 min + 10 min


def test_report_of_unknown_job_is_refused(engine: Engine) -> None:
    with pytest.raises(JobActionRefused):
        build_report(engine, 404)


def test_csv_export_lists_every_like_with_its_status(engine: Engine, tmp_path: Path) -> None:
    report = build_report(engine, make_job(engine, []))

    path = export_report_csv(report, tmp_path / "rapport.csv")

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file, delimiter=";"))
    assert rows[0] == [
        "rang",
        "auteur",
        "type",
        "partagée le (selon Instagram)",
        "statut",
        "traité le",
        "heure",
        "détail",
        "identifiant",
    ]
    assert [row[4] for row in rows[1:]] == [
        "retiré",
        "retiré",
        "échec",
        "introuvable",
        "exclu",
        "à retirer",
    ]
    assert rows[3][7] == "toujours affiché après « Je n’aime plus »"
    # Date et heure séparées : Excel affiche « ##### » pour une date avec heure dans une
    # colonne de largeur par défaut.
    processed = (T0 + timedelta(minutes=2)).astimezone()
    assert rows[1][5:7] == [f"{processed:%d/%m/%Y}", f"{processed:%H:%M}"]
    assert rows[6][5:7] == ["", ""]


def test_json_export_round_trips(engine: Engine, tmp_path: Path) -> None:
    report = build_report(engine, make_job(engine, []))

    data = json.loads(export_report_json(report, tmp_path / "rapport.json").read_text("utf-8"))

    assert data["nettoyage"] == report.job_id
    assert data["likes_cibles"] == 6
    assert data["par_statut"]["done"] == 2
    assert data["criteres"]["sort"] == "oldest_first"
    assert data["likes"][2]["statut"] == "failed"


def test_summary_lines(engine: Engine) -> None:
    job_id = make_job(engine, [])

    lines = summary_lines(build_report(engine, job_id))

    assert lines[0].startswith(f"Nettoyage n°{job_id} : en pause, du ")
    assert "retirés : 2 | échecs : 1 | introuvables : 1 | exclus : 1 | à traiter : 1" in lines[1]


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(42, "42 s"), (77, "1 min 17 s"), (3600 * 2 + 180, "2 h 03 min")],
)
def test_format_duration(seconds: int, text: str) -> None:
    assert format_duration(timedelta(seconds=seconds)) == text
