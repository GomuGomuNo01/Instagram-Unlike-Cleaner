"""Cycle de vie d'un nettoyage (job), vue d'ensemble, exclusions et journal technique."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.models.columns import utcnow
from app.models.schemas import CleanupFilters
from app.models.tables import EventLog, ItemStatus, Job, JobStatus, LikedItem, can_transition

_FINISHED = frozenset({JobStatus.COMPLETED, JobStatus.STOPPED, JobStatus.FAILED})
# Statuts depuis lesquels `iuc run` peut lancer ou reprendre un nettoyage. RUNNING signifie
# que l'exécution précédente a été interrompue brutalement (fenêtre fermée, coupure...).
RUNNABLE = frozenset({JobStatus.READY, JobStatus.PAUSED, JobStatus.RUNNING})

STATUS_LABELS: dict[JobStatus, str] = {
    JobStatus.CREATED: "créé",
    JobStatus.COLLECTING: "collecte",
    JobStatus.READY: "prêt",
    JobStatus.RUNNING: "en cours",
    JobStatus.PAUSED: "en pause",
    JobStatus.COMPLETED: "terminé",
    JobStatus.STOPPED: "arrêté",
    JobStatus.FAILED: "échec",
}


class InvalidTransitionError(RuntimeError):
    """Changement de statut non prévu par la machine d'états (par exemple collecte → unlike)."""


class JobActionRefused(RuntimeError):
    """Action impossible sur ce nettoyage : inexistant, terminé, ou préparé sur un autre compte."""


@dataclass(frozen=True)
class JobOverview:
    id: int
    status: JobStatus
    created_at: datetime
    account_id: str | None
    filters: CleanupFilters
    counts: dict[ItemStatus, int]

    @property
    def to_process(self) -> int:
        """Likes ciblés qui n'ont pas encore été traités ni exclus."""
        return self.counts.get(ItemStatus.PENDING, 0) + self.counts.get(ItemStatus.SELECTED, 0)


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


def stop_job(engine: Engine, job_id: int) -> JobStatus:
    """Arrête définitivement un nettoyage : les likes non traités ne seront jamais retirés.

    Un nettoyage en cours d'exécution dans un autre terminal le remarque avant son lot
    suivant et s'arrête. Renvoie le statut qu'avait le nettoyage avant l'arrêt.
    """
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if job is None:
            raise JobActionRefused(f"Aucun nettoyage n°{job_id}.")
        if job.status not in RUNNABLE:
            raise JobActionRefused(
                f"Le nettoyage n°{job_id} est « {STATUS_LABELS[job.status]} » : "
                "il n'y a rien à arrêter."
            )
        previous = job.status
        change_status(job, JobStatus.STOPPED)
        log_event(db, job_id, "Nettoyage arrêté par l'utilisateur")
        db.commit()
        return previous


def job_overview(engine: Engine, job_id: int) -> JobOverview | None:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        return None if job is None else _overview(db, job)


def list_jobs(engine: Engine) -> list[JobOverview]:
    with Session(engine) as db:
        return [_overview(db, job) for job in db.exec(select(Job).order_by(col(Job.id))).all()]


def _overview(db: Session, job: Job) -> JobOverview:
    assert job.id is not None
    statuses = db.exec(select(LikedItem.status).where(LikedItem.job_id == job.id)).all()
    return JobOverview(
        id=job.id,
        status=job.status,
        created_at=job.created_at,
        account_id=job.account_id,
        filters=CleanupFilters.model_validate(job.filters),
        counts=dict(Counter(ItemStatus(status) for status in statuses)),
    )


def set_excluded(
    engine: Engine,
    job_id: int,
    *,
    ranks: list[int],
    authors: list[str],
    restore: bool = False,
) -> int:
    """Exclut du nettoyage (ou y remet, avec `restore`) les likes désignés par leur rang
    dans le CSV d'aperçu ou par leur auteur. Renvoie le nombre de likes modifiés."""
    positions = {rank - 1 for rank in ranks}
    wanted_authors = {author.strip().removeprefix("@").lower() for author in authors}
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if job is None:
            raise JobActionRefused(f"Aucun nettoyage n°{job_id}.")
        if job.status not in (JobStatus.READY, JobStatus.PAUSED):
            raise JobActionRefused(
                f"Le nettoyage n°{job_id} est « {STATUS_LABELS[job.status]} » : "
                "les exclusions ne se modifient que s'il est prêt ou en pause."
            )
        back_to = ItemStatus.PENDING if job.status is JobStatus.READY else ItemStatus.SELECTED
        sources = {ItemStatus.EXCLUDED} if restore else {ItemStatus.PENDING, ItemStatus.SELECTED}
        items = db.exec(
            select(LikedItem).where(LikedItem.job_id == job_id, col(LikedItem.status).in_(sources))
        ).all()
        changed = [
            item
            for item in items
            if item.position in positions or (item.author or "") in wanted_authors
        ]
        for item in changed:
            item.status = back_to if restore else ItemStatus.EXCLUDED
            db.add(item)
        action = "remis dans le nettoyage" if restore else "exclus"
        log_event(db, job_id, f"{len(changed)} likes {action} à la demande de l'utilisateur")
        db.commit()
        return len(changed)
