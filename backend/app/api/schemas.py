"""Schémas des requêtes et réponses de l'API, publiés dans la documentation OpenAPI."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.browser.session import SessionStatus
from app.models.schemas import CleanupFilters
from app.models.tables import ItemStatus, JobStatus, LikedItem, MediaKind
from app.services.jobs import JobOverview


class SessionStatusOut(BaseModel):
    browser_open: bool
    logged_in: bool
    account_id: str | None
    page: str | None = Field(description="Nature de la page affichée (accueil, connexion...).")
    challenge_required: bool
    consent_required: bool
    busy: bool = Field(description="Une collecte ou un nettoyage est en cours.")

    @classmethod
    def build(cls, status: SessionStatus, *, busy: bool) -> "SessionStatusOut":
        return cls(
            browser_open=status.browser_open,
            logged_in=status.logged_in,
            account_id=status.account_id,
            page=status.page.value if status.page else None,
            challenge_required=status.challenge_required,
            consent_required=status.consent_required,
            busy=busy,
        )


class JobOut(BaseModel):
    id: int
    status: JobStatus
    created_at: datetime
    account_id: str | None
    filters: CleanupFilters
    counts: dict[ItemStatus, int]
    to_process: int
    running: bool = Field(description="Une tâche de ce nettoyage tourne en ce moment.")

    @classmethod
    def build(cls, overview: JobOverview, *, running: bool) -> "JobOut":
        return cls(
            id=overview.id,
            status=overview.status,
            created_at=overview.created_at,
            account_id=overview.account_id,
            filters=overview.filters,
            counts=overview.counts,
            to_process=overview.to_process,
            running=running,
        )


class ItemOut(BaseModel):
    id: int
    rank: int = Field(description="Rang dans l'aperçu, à partir de 1.")
    media_key: str
    label: str
    author: str | None
    media_kind: MediaKind | None
    shared_on: date | None = Field(description="Date « partagée le » affichée par Instagram.")
    status: ItemStatus
    error: str | None
    processed_at: datetime | None

    @classmethod
    def build(cls, item: LikedItem) -> "ItemOut":
        assert item.id is not None
        return cls(
            id=item.id,
            rank=item.position + 1,
            media_key=item.media_key,
            label=item.label,
            author=item.author,
            media_kind=item.media_kind,
            shared_on=item.published_on,
            status=item.status,
            error=item.error,
            processed_at=item.processed_at,
        )


class ItemsPage(BaseModel):
    items: list[ItemOut]
    total: int
    offset: int
    limit: int


class ItemsPatch(BaseModel):
    item_ids: list[int] = Field(min_length=1)
    excluded: bool = Field(description="true : décocher (exclure) ; false : recocher.")


class ItemsPatchOut(BaseModel):
    changed: int
    job: JobOut


class StartRequest(BaseModel):
    limit: int | None = Field(
        default=None, ge=1, description="Nombre maximal de likes à retirer pendant cette exécution."
    )


class DeletedOut(BaseModel):
    deleted: list[str]
