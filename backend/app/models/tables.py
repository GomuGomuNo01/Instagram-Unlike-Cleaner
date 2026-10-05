"""Tables SQLite : demandes de nettoyage, likes ciblés, compteur quotidien et journal technique."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.columns import UTCDateTime, utcnow


class JobStatus(StrEnum):
    CREATED = "created"  # créé, collecte pas encore lancée
    COLLECTING = "collecting"  # collecte de l'aperçu en cours
    READY = "ready"  # aperçu prêt, en attente de validation
    RUNNING = "running"  # unlikes en cours
    PAUSED = "paused"  # pause manuelle, limite quotidienne ou alerte Instagram
    COMPLETED = "completed"
    STOPPED = "stopped"  # arrêté par l'utilisateur
    FAILED = "failed"


JOB_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.CREATED: frozenset({JobStatus.COLLECTING, JobStatus.FAILED}),
    JobStatus.COLLECTING: frozenset({JobStatus.READY, JobStatus.STOPPED, JobStatus.FAILED}),
    JobStatus.READY: frozenset({JobStatus.RUNNING, JobStatus.STOPPED}),
    JobStatus.RUNNING: frozenset(
        {JobStatus.PAUSED, JobStatus.COMPLETED, JobStatus.STOPPED, JobStatus.FAILED}
    ),
    JobStatus.PAUSED: frozenset({JobStatus.RUNNING, JobStatus.STOPPED}),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.STOPPED: frozenset(),
    JobStatus.FAILED: frozenset(),
}


def can_transition(current: JobStatus, target: JobStatus) -> bool:
    return target in JOB_TRANSITIONS[current]


class ItemStatus(StrEnum):
    PENDING = "pending"  # collecté et coché dans l'aperçu, pas encore validé
    SELECTED = "selected"  # aperçu validé : à retirer
    EXCLUDED = "excluded"  # décoché par l'utilisateur
    DONE = "done"  # like retiré
    FAILED = "failed"
    SKIPPED = "skipped"  # ignoré : contenu supprimé, compte devenu privé...


class MediaKind(StrEnum):
    """Type de publication, tel que l'indique le libellé de la vignette."""

    PHOTO = "photo"
    VIDEO = "video"  # les vidéos publiées depuis 2022 sont des Reels
    CAROUSEL = "carousel"


class Job(SQLModel, table=True):
    """Une demande de nettoyage et ses filtres."""

    __tablename__ = "job"

    id: int | None = Field(default=None, primary_key=True)
    filters: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: JobStatus = Field(default=JobStatus.CREATED, index=True)
    # Identifiant numérique du compte connecté au lancement (cookie ds_user_id) :
    # la reprise refusera d'agir sur un autre compte.
    account_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
    started_at: datetime | None = Field(default=None, sa_type=UTCDateTime)
    finished_at: datetime | None = Field(default=None, sa_type=UTCDateTime)


class LikedItem(SQLModel, table=True):
    """Un like ciblé par une demande, et son avancement."""

    __tablename__ = "liked_item"
    __table_args__ = (UniqueConstraint("job_id", "media_key"),)

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True, ondelete="CASCADE")
    # Les vignettes n'ont pas de lien vers la publication : on les identifie par le nom du
    # fichier de leur image, stable d'un chargement à l'autre.
    media_key: str
    position: int  # rang dans la grille au moment de la collecte, à partir de 0
    label: str  # libellé complet de la vignette
    author: str | None = None
    media_kind: MediaKind | None = None
    published_on: date | None = None  # date de publication ; celle du like n'est pas affichée
    status: ItemStatus = Field(default=ItemStatus.PENDING, index=True)
    error: str | None = None
    processed_at: datetime | None = Field(default=None, sa_type=UTCDateTime)


class DailyCounter(SQLModel, table=True):
    """Nombre d'unlikes faits dans la journée, pour respecter DAILY_LIMIT."""

    __tablename__ = "daily_counter"

    day: date = Field(primary_key=True)  # date locale de l'utilisateur
    unlike_count: int = 0


class EventLog(SQLModel, table=True):
    """Journal technique d'une demande, pour le diagnostic et le suivi en direct."""

    __tablename__ = "event_log"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int | None = Field(default=None, foreign_key="job.id", index=True, ondelete="CASCADE")
    timestamp: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
    level: str = "INFO"
    message: str
