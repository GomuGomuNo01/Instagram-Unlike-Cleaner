"""Nettoyage par lots : retrait des likes validés, avec limites, pauses et vérifications.

Pour chaque lot : rechargement de la page des likes, filtre d'Instagram du nettoyage, mode
sélection, lecture de la grille jusqu'aux likes du lot, sélection vérifiée, « Je n’aime
plus », puis attente de leur disparition. Le rechargement suivant sert aussi de contrôle :
un like retiré qui réapparaît passe en échec. Chaque résultat est écrit en base avant le lot
suivant ; au moindre signal d'Instagram, le nettoyage passe en pause et pourra reprendre.

Une pause ou un arrêt demandés (CleanupControl, ou `iuc stop` depuis un autre terminal) sont
pris en compte entre deux lots, après le contrôle du dernier lot traité.
"""

import asyncio
import contextlib
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page
from sqlalchemy import Engine
from sqlmodel import Session, col, func, select

from app.browser.grid import GridInterrupted, Thumbnail, load_grid
from app.browser.native_filters import NativeFilterError, apply_native_filters
from app.browser.selection import (
    SelectionError,
    UnlikeOutcome,
    enter_selection_mode,
    select_batch,
    unlike_selected,
)
from app.browser.session import OUTCOME_MESSAGES, BrowserSession, NavigationOutcome
from app.core.config import Settings
from app.models.columns import utcnow
from app.models.schemas import CleanupFilters
from app.models.tables import DailyCounter, ItemStatus, Job, JobStatus, LikedItem
from app.services.jobs import JobActionRefused, change_status, log_event

logger = logging.getLogger(__name__)

# Vignettes relues au-delà de la position attendue, pour absorber les nouveaux likes faits
# depuis l'aperçu (recherche) ou un léger décalage de la grille (contrôle après retrait).
SEARCH_MARGIN = 500
VERIFY_MARGIN = 18


class StopReason(StrEnum):
    COMPLETED = "completed"
    RUN_LIMIT = "run_limit"
    DAILY_LIMIT = "daily_limit"
    ACTION_BLOCKED = "action_blocked"
    UNKNOWN_DIALOG = "unknown_dialog"
    SELECTION_MISMATCH = "selection_mismatch"
    NOT_REMOVED = "not_removed"
    PAGE_UNAVAILABLE = "page_unavailable"
    USER_PAUSE = "user_pause"
    USER_STOP = "user_stop"


STOP_MESSAGES: dict[StopReason, str] = {
    StopReason.COMPLETED: "Nettoyage terminé : tous les likes validés ont été traités.",
    StopReason.RUN_LIMIT: (
        "Nombre de likes demandé pour cette exécution atteint. Relance la même commande pour "
        "continuer."
    ),
    StopReason.DAILY_LIMIT: (
        "Limite quotidienne atteinte (DAILY_LIMIT). Relance demain : le nettoyage reprendra "
        "là où il s'est arrêté."
    ),
    StopReason.ACTION_BLOCKED: (
        "Instagram a signalé une limite ou une erreur. Nettoyage en pause : attends au moins "
        "quelques heures avant de relancer."
    ),
    StopReason.UNKNOWN_DIALOG: (
        "Instagram a affiché une fenêtre inconnue après « Je n’aime plus ». Rien n'a été "
        "confirmé ; un diagnostic a été enregistré."
    ),
    StopReason.SELECTION_MISMATCH: (
        "Les cases cochées ne correspondaient pas exactement au lot prévu : la sélection a été "
        "annulée et rien n'a été retiré. Un diagnostic a été enregistré."
    ),
    StopReason.NOT_REMOVED: (
        "Certains likes sont restés affichés après « Je n’aime plus » : ils sont marqués en "
        "échec et le nettoyage est en pause. Un diagnostic a été enregistré."
    ),
    StopReason.PAGE_UNAVAILABLE: "La page des likes n'est plus utilisable. Nettoyage en pause.",
    StopReason.USER_PAUSE: (
        "Nettoyage mis en pause à ta demande. Relance la même commande pour continuer."
    ),
    StopReason.USER_STOP: (
        "Nettoyage arrêté à ta demande : les likes non traités ne seront pas retirés."
    ),
}
_NORMAL_STOPS = frozenset(
    {
        StopReason.COMPLETED,
        StopReason.RUN_LIMIT,
        StopReason.DAILY_LIMIT,
        StopReason.USER_PAUSE,
        StopReason.USER_STOP,
    }
)
_FINAL_STATUS = {StopReason.COMPLETED: JobStatus.COMPLETED, StopReason.USER_STOP: JobStatus.STOPPED}
# Repères écrits dans le journal à chaque lancement, et au lancement qui suit une exécution
# interrompue brutalement : le rapport s'en sert pour calculer la durée active.
RUN_STARTED_EVENT = "Exécution lancée"
RUN_INTERRUPTED_EVENT = "Exécution précédente interrompue"


class CleanupControl:
    """Demandes de pause ou d'arrêt d'un nettoyage en cours.

    Elles sont prises en compte entre deux lots : le lot en cours se termine toujours, pour
    que son résultat soit enregistré et contrôlé. La pause entre deux lots est écourtée.
    """

    def __init__(self) -> None:
        self.pause_requested = False
        self.stop_requested = False
        self._wake = asyncio.Event()

    def request_pause(self) -> None:
        self.pause_requested = True
        self._wake.set()

    def request_stop(self) -> None:
        self.stop_requested = True
        self._wake.set()

    async def sleep(self, seconds: float) -> None:
        """Attend `seconds`, ou moins si une pause ou un arrêt est demandé entre-temps."""
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._wake.wait(), timeout=seconds)


@dataclass(frozen=True)
class CleanupResult:
    job_id: int
    reason: StopReason
    done: int  # likes retirés pendant cette exécution
    failed: int
    skipped: int
    remaining: int  # likes validés restant à traiter
    detail: str | None = None


@dataclass(frozen=True)
class _Target:
    item_id: int
    media_key: str
    position: int


def start_job(engine: Engine, job_id: int, account_id: str | None) -> None:
    """Valide l'aperçu au premier lancement (likes en attente → à retirer) et passe le
    nettoyage au statut « en cours ». Refuse s'il a été préparé sur un autre compte."""
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if job is None:
            raise JobActionRefused(f"Aucun nettoyage n°{job_id}.")
        if job.account_id and account_id and job.account_id != account_id:
            raise JobActionRefused(
                f"Le nettoyage n°{job_id} a été préparé sur un autre compte Instagram que celui "
                "qui est connecté : il ne sera pas lancé."
            )
        if job.status is JobStatus.RUNNING:
            change_status(job, JobStatus.PAUSED)
            log_event(db, job_id, f"{RUN_INTERRUPTED_EVENT} : reprise", "WARNING")
        if job.status is JobStatus.READY:
            pending = db.exec(
                select(LikedItem).where(
                    LikedItem.job_id == job_id, LikedItem.status == ItemStatus.PENDING
                )
            ).all()
            for item in pending:
                item.status = ItemStatus.SELECTED
                db.add(item)
            log_event(db, job_id, f"Aperçu validé : {len(pending)} likes à retirer")
        elif job.status is not JobStatus.PAUSED:
            raise JobActionRefused(
                f"Le nettoyage n°{job_id} est au statut « {job.status} » : rien à lancer."
            )
        change_status(job, JobStatus.RUNNING)
        log_event(db, job_id, RUN_STARTED_EVENT)
        db.commit()


async def run_cleanup(
    session: BrowserSession,
    engine: Engine,
    settings: Settings,
    job_id: int,
    *,
    account_id: str | None,
    max_unlikes: int | None = None,
    snapshot: bool = False,
    on_batch: Callable[[int, int], None] | None = None,
    control: CleanupControl | None = None,
) -> CleanupResult:
    """Retire les likes validés d'un nettoyage, lot par lot, sur la page des likes ouverte.

    `max_unlikes` limite le nombre de likes retirés pendant cette exécution ; `on_batch`
    reçoit, après chaque lot, le nombre retiré dans le lot et le total de l'exécution ;
    `control` permet de demander une pause ou un arrêt depuis l'extérieur.
    """
    control = control or CleanupControl()
    start_job(engine, job_id, account_id)
    filters = _job_filters(engine, job_id)
    done = failed = skipped = 0
    previous: list[_Target] = []
    first_round = True

    async def diagnostic(label: str) -> None:
        await session.save_diagnostic(settings.diagnostics_dir, f"nettoyage{job_id}-{label}")

    def stop(reason: StopReason, detail: str | None = None) -> CleanupResult:
        return _finish(engine, job_id, reason, detail, done=done, failed=failed, skipped=skipped)

    try:
        while True:
            limit_reason = _requested_stop(engine, job_id, control) or _limit_reached(
                engine, settings, max_unlikes, done
            )
            batch = [] if limit_reason else _next_batch(engine, job_id, settings, max_unlikes, done)
            if not batch and not previous:
                return stop(limit_reason or StopReason.COMPLETED)

            page = session.page
            if not first_round:
                outcome = await session.open_likes_page()
                if outcome is not NavigationOutcome.OK:
                    return stop(StopReason.PAGE_UNAVAILABLE, OUTCOME_MESSAGES[outcome])
            first_round = False
            await apply_native_filters(page, filters)
            if batch:
                await enter_selection_mode(page)
            present = await _scan(page, batch, previous)

            reappeared = _check_previous(engine, job_id, previous, present)
            done -= reappeared
            failed += reappeared
            previous = []
            if not batch:
                return stop(limit_reason or StopReason.COMPLETED)

            missing = [target for target in batch if target.media_key not in present]
            targets = [target for target in batch if target.media_key in present]
            if missing:
                _mark(engine, job_id, missing, ItemStatus.SKIPPED, "introuvable dans la grille")
                skipped += len(missing)
            if not targets:
                continue

            keys = [target.media_key for target in targets]
            try:
                await select_batch(page, keys)
            except SelectionError as exc:
                await diagnostic("selection-refusee")
                return stop(StopReason.SELECTION_MISMATCH, str(exc))
            if snapshot:
                await diagnostic("selection")

            report = await unlike_selected(page, keys)
            if snapshot or report.outcome is not UnlikeOutcome.REMOVED:
                await diagnostic("apres-unlike")
            if report.outcome is UnlikeOutcome.BLOCKED:
                return stop(StopReason.ACTION_BLOCKED, report.message)
            if report.outcome is UnlikeOutcome.UNKNOWN_DIALOG:
                return stop(StopReason.UNKNOWN_DIALOG, report.message)

            removed = [target for target in targets if target.media_key not in report.still_present]
            not_removed = [target for target in targets if target.media_key in report.still_present]
            _record_batch(engine, job_id, removed, not_removed)
            done += len(removed)
            failed += len(not_removed)
            if on_batch is not None:
                on_batch(len(removed), done)
            if not_removed:
                return stop(StopReason.NOT_REMOVED, report.message)
            previous = removed
            await control.sleep(random.uniform(settings.delay_min, settings.delay_max))
    except asyncio.CancelledError:
        stop(StopReason.USER_PAUSE, "interruption immédiate, sans contrôle du dernier lot")
        raise
    except (GridInterrupted, NativeFilterError, PlaywrightError) as exc:
        return stop(StopReason.PAGE_UNAVAILABLE, str(exc))


def today_count(engine: Engine) -> int:
    """Unlikes tentés aujourd'hui (date locale), tous nettoyages confondus."""
    with Session(engine) as db:
        counter = db.get(DailyCounter, date.today())
        return counter.unlike_count if counter else 0


def _job_filters(engine: Engine, job_id: int) -> CleanupFilters:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        assert job is not None
        return CleanupFilters.model_validate(job.filters)


def _requested_stop(engine: Engine, job_id: int, control: CleanupControl) -> StopReason | None:
    """Arrêt ou pause demandés : par `control`, ou par `iuc stop` depuis un autre terminal
    (le nettoyage est alors déjà au statut « arrêté » en base)."""
    with Session(engine) as db:
        job = db.get(Job, job_id)
        stopped_elsewhere = job is not None and job.status is JobStatus.STOPPED
    if control.stop_requested or stopped_elsewhere:
        return StopReason.USER_STOP
    if control.pause_requested:
        return StopReason.USER_PAUSE
    return None


def _limit_reached(
    engine: Engine, settings: Settings, max_unlikes: int | None, done: int
) -> StopReason | None:
    if max_unlikes is not None and done >= max_unlikes:
        return StopReason.RUN_LIMIT
    if today_count(engine) >= settings.daily_limit:
        return StopReason.DAILY_LIMIT
    return None


def _next_batch(
    engine: Engine, job_id: int, settings: Settings, max_unlikes: int | None, done: int
) -> list[_Target]:
    size = min(settings.batch_size, settings.daily_limit - today_count(engine))
    if max_unlikes is not None:
        size = min(size, max_unlikes - done)
    with Session(engine) as db:
        items = db.exec(
            select(LikedItem)
            .where(LikedItem.job_id == job_id, LikedItem.status == ItemStatus.SELECTED)
            .order_by(col(LikedItem.position))
            .limit(size)
        ).all()
        return [_Target(item.id, item.media_key, item.position) for item in items if item.id]


async def _scan(page: Page, batch: list[_Target], previous: list[_Target]) -> set[str]:
    """Lit la grille depuis le haut jusqu'à trouver tous les likes du lot, en repassant
    forcément par l'emplacement du lot précédent (traité juste avant, donc plus haut)."""
    wanted = {target.media_key for target in batch}
    verify_depth = max((target.position for target in previous), default=-1) + 1
    if batch:
        cap = max(target.position for target in batch) + 1 + SEARCH_MARGIN

        def found(collected: dict[str, Thumbnail]) -> bool:
            return wanted <= collected.keys()

    else:
        cap = verify_depth + VERIFY_MARGIN

        def found(collected: dict[str, Thumbnail]) -> bool:
            return False

    thumbnails = await load_grid(page, max_items=cap, stop_when=found)
    return {thumbnail.media_key for thumbnail in thumbnails}


def _check_previous(engine: Engine, job_id: int, previous: list[_Target], present: set[str]) -> int:
    """Passe en échec les likes du lot précédent qui ont réapparu après le rechargement."""
    back = [target for target in previous if target.media_key in present]
    if back:
        _mark(
            engine,
            job_id,
            back,
            ItemStatus.FAILED,
            "réapparu après rechargement : Instagram n'a pas retiré ce like",
        )
    return len(back)


def _mark(
    engine: Engine, job_id: int, targets: list[_Target], status: ItemStatus, error: str
) -> None:
    with Session(engine) as db:
        for target in targets:
            item = db.get(LikedItem, target.item_id)
            assert item is not None
            item.status = status
            item.error = error
            item.processed_at = utcnow()
            db.add(item)
        level = "ERROR" if status is ItemStatus.FAILED else "WARNING"
        log_event(db, job_id, f"{len(targets)} likes « {status} » : {error}", level)
        db.commit()


def _record_batch(
    engine: Engine, job_id: int, removed: list[_Target], not_removed: list[_Target]
) -> None:
    """Enregistre le résultat d'un lot et l'ajoute au compteur du jour, en une transaction."""
    with Session(engine) as db:
        now = utcnow()
        for targets, status, error in (
            (removed, ItemStatus.DONE, None),
            (not_removed, ItemStatus.FAILED, "toujours affiché après « Je n’aime plus »"),
        ):
            for target in targets:
                item = db.get(LikedItem, target.item_id)
                assert item is not None
                item.status = status
                item.error = error
                item.processed_at = now
                db.add(item)
        counter = db.get(DailyCounter, date.today()) or DailyCounter(day=date.today())
        # Toute tentative compte dans la limite quotidienne, réussie ou non.
        counter.unlike_count += len(removed) + len(not_removed)
        db.add(counter)
        log_event(db, job_id, f"Lot traité : {len(removed)} retirés, {len(not_removed)} en échec")
        db.commit()


def _finish(
    engine: Engine,
    job_id: int,
    reason: StopReason,
    detail: str | None,
    *,
    done: int,
    failed: int,
    skipped: int,
) -> CleanupResult:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        assert job is not None
        remaining = db.exec(
            select(func.count())
            .select_from(LikedItem)
            .where(LikedItem.job_id == job_id, LikedItem.status == ItemStatus.SELECTED)
        ).one()
        target = _FINAL_STATUS.get(reason, JobStatus.PAUSED)
        # Un nettoyage déjà arrêté depuis un autre terminal garde ce statut.
        if job.status is not target and job.status is not JobStatus.STOPPED:
            change_status(job, target)
        message = STOP_MESSAGES[reason] + (f" ({detail})" if detail else "")
        level = "INFO" if reason in _NORMAL_STOPS else "WARNING"
        log_event(db, job_id, message, level)
        db.commit()
    logger.info("Nettoyage n°%d : %s", job_id, reason)
    return CleanupResult(job_id, reason, done, failed, skipped, remaining, detail)
