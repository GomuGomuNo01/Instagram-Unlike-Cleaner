"""Cycle de vie d'un nettoyage (job) et journal technique associé."""

from sqlalchemy import Engine
from sqlmodel import Session

from app.models.columns import utcnow
from app.models.schemas import CleanupFilters
from app.models.tables import EventLog, Job, JobStatus, can_transition

_FINISHED = frozenset({JobStatus.COMPLETED, JobStatus.STOPPED, JobStatus.FAILED})


class InvalidTransitionError(RuntimeError):
    """Changement de statut non prévu par la machine d'états (par exemple collecte → unlike)."""


def change_status(job: Job, target: JobStatus) -> None:
    if not can_transition(job.status, target):
        raise InvalidTransitionError(f"Passage de « {job.status} » à « {target} » interdit")
    job.status = target
    if target is JobStatus.RUNNING and job.started_at is None:
        job.started_at = utcnow()
    if target in _FINISHED:
        job.finished_at = utcnow()


def log_event(db: Session, job_id: int | None, message: str, level: str = "INFO") -> None:
    db.add(EventLog(job_id=job_id, message=message, level=level))


def create_job(engine: Engine, filters: CleanupFilters, account_id: str | None) -> int:
    """Enregistre une nouvelle demande, directement au statut « collecte en cours »."""
    with Session(engine) as db:
        job = Job(filters=filters.model_dump(mode="json"), account_id=account_id)
        db.add(job)
        db.flush()
        assert job.id is not None
        change_status(job, JobStatus.COLLECTING)
        log_event(db, job.id, "Collecte de l'aperçu lancée")
        db.commit()
        return job.id


def fail_job(engine: Engine, job_id: int, reason: str) -> None:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        change_status(job, JobStatus.FAILED)
        log_event(db, job_id, reason, level="ERROR")
        db.commit()
