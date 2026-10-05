"""Aperçu d'un nettoyage : collecte des likes ciblés, enregistrement en base et export."""

import asyncio
import csv
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.browser.grid import GridInterrupted, load_grid
from app.browser.layout import LayoutChanged
from app.browser.native_filters import apply_native_filters
from app.browser.session import BrowserSession
from app.models.schemas import CleanupFilters
from app.models.tables import ItemStatus, Job, JobStatus, LikedItem, MediaKind
from app.services.jobs import change_status, create_job, fail_job, log_event


class PreviewError(RuntimeError):
    """La collecte de l'aperçu a échoué ; la demande est passée au statut « échec »."""


@dataclass(frozen=True)
class PreviewResult:
    job_id: int
    scanned: int  # vignettes lues dans la grille, après le filtre d'Instagram
    targeted: int  # likes retenus après les critères d'IUC


@dataclass(frozen=True)
class PreviewSummary:
    total: int
    by_kind: dict[MediaKind | None, int]
    top_authors: list[tuple[str, int]]


async def run_preview(
    session: BrowserSession,
    engine: Engine,
    filters: CleanupFilters,
    *,
    account_id: str | None,
    max_scanned: int | None = None,
    on_progress: Callable[[int], None] | None = None,
    job_id: int | None = None,
) -> PreviewResult:
    """Crée une demande, collecte les likes ciblés sur la page des likes déjà ouverte, et
    les enregistre au statut « en attente » : rien n'est retiré à cette étape.

    `job_id` désigne une demande déjà créée (statut « collecte »), par exemple par l'API,
    qui doit renvoyer son numéro avant la fin de la collecte.
    """
    if job_id is None:
        job_id = create_job(engine, filters, account_id)
    try:
        await apply_native_filters(session.page, filters)
        thumbnails = await load_grid(session.page, max_items=max_scanned, on_progress=on_progress)
    except (GridInterrupted, LayoutChanged, PlaywrightError) as exc:
        message = await _interruption_message(session, exc)
        fail_job(engine, job_id, message)
        raise PreviewError(message) from exc
    except asyncio.CancelledError:
        fail_job(engine, job_id, "Collecte interrompue avant la fin")
        raise

    targeted = [
        LikedItem(
            job_id=job_id,
            media_key=thumbnail.media_key,
            position=position,
            label=thumbnail.label,
            author=thumbnail.author,
            media_kind=thumbnail.media_kind,
            published_on=thumbnail.published_on,
        )
        for position, thumbnail in enumerate(thumbnails)
        if filters.matches(thumbnail.author, thumbnail.media_kind)
    ]
    with Session(engine) as db:
        db.add_all(targeted)
        job = db.get(Job, job_id)
        assert job is not None
        change_status(job, JobStatus.READY)
        log_event(
            db, job_id, f"Aperçu prêt : {len(targeted)} likes ciblés sur {len(thumbnails)} lus"
        )
        db.commit()
    return PreviewResult(job_id=job_id, scanned=len(thumbnails), targeted=len(targeted))


async def _interruption_message(session: BrowserSession, exc: Exception) -> str:
    """Message pour l'utilisateur : signal d'Instagram (déconnexion, vérification, limite)
    s'il y en a un, sinon la cause technique."""
    outcome = await session.interruption()
    if outcome is not None:
        return f"Collecte interrompue. {session.describe(outcome)}"
    if isinstance(exc, GridInterrupted) and exc.alert:
        return f"Collecte interrompue : Instagram a signalé une limite ou une erreur ({exc.alert})."
    if isinstance(exc, LayoutChanged):
        return f"Collecte interrompue : l'interface d'Instagram a changé ({exc})."
    return f"Collecte interrompue : {exc}"


def pending_items(engine: Engine, job_id: int) -> list[LikedItem]:
    with Session(engine) as db:
        statement = (
            select(LikedItem)
            .where(LikedItem.job_id == job_id, LikedItem.status == ItemStatus.PENDING)
            .order_by(col(LikedItem.position))
        )
        return list(db.exec(statement).all())


def summarize(items: list[LikedItem], top: int = 10) -> PreviewSummary:
    authors = Counter(item.author for item in items if item.author)
    return PreviewSummary(
        total=len(items),
        by_kind=dict(Counter(item.media_kind for item in items)),
        top_authors=authors.most_common(top),
    )


_KIND_LABELS: dict[MediaKind | None, str] = {
    MediaKind.PHOTO: "photo",
    MediaKind.VIDEO: "vidéo",
    MediaKind.CAROUSEL: "carrousel",
    None: "inconnu",
}


def kind_label(kind: MediaKind | None) -> str:
    return _KIND_LABELS[kind]


def export_csv(items: list[LikedItem], path: Path) -> Path:
    """Écrit l'aperçu dans un CSV lisible par Excel (séparateur « ; », UTF-8 avec BOM)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["rang", "auteur", "type", "partagée le (selon Instagram)", "identifiant"])
        for item in items:
            writer.writerow(
                [
                    item.position + 1,
                    f"@{item.author}" if item.author else "",
                    kind_label(item.media_kind),
                    item.published_on.strftime("%d/%m/%Y") if item.published_on else "",
                    item.media_key,
                ]
            )
    return path
