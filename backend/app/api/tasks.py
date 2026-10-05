"""Tâches de fond de l'API : collecte d'un aperçu et nettoyage, avec événements de progression.

Chaque tâche publie des événements pour le flux SSE du nettoyage :
- « status » au démarrage, avec l'état du nettoyage ;
- « progress » pendant la collecte (vignettes lues) ;
- « batch » après chaque lot retiré ;
- « end » à la fin, réussie ou non, avec un message pour l'utilisateur. Le flux s'arrête là.
"""

import asyncio
import logging
from typing import Any

from sqlmodel import Session

from app.api.schemas import JobOut
from app.api.state import ApiConflict, ApiState
from app.browser.session import OUTCOME_MESSAGES, NavigationOutcome
from app.models.schemas import CleanupFilters
from app.models.tables import Job, JobStatus
from app.services.cleanup import STOP_MESSAGES, CleanupControl, StopReason, run_cleanup
from app.services.jobs import JobActionRefused, fail_job, job_overview
from app.services.preview import PreviewError, export_csv, pending_items, run_preview
from app.services.report import write_report_files

logger = logging.getLogger(__name__)

_SUCCESSFUL_STOPS = frozenset(
    {
        StopReason.COMPLETED,
        StopReason.RUN_LIMIT,
        StopReason.DAILY_LIMIT,
        StopReason.USER_PAUSE,
        StopReason.USER_STOP,
    }
)


def job_payload(state: ApiState, job_id: int, *, running: bool | None = None) -> dict[str, Any]:
    overview = job_overview(state.engine, job_id)
    if overview is None:
        return {"id": job_id}
    if running is None:
        running = state.runner.running_for(job_id) is not None
    return JobOut.build(overview, running=running).model_dump(mode="json")


async def preview_task(
    state: ApiState,
    job_id: int,
    filters: CleanupFilters,
    *,
    account_id: str | None,
    max_scanned: int | None,
    _control: CleanupControl,
) -> None:
    hub = state.hub
    hub.publish(job_id, "status", {"job": job_payload(state, job_id, running=True)})

    def progress(count: int) -> None:
        hub.publish(job_id, "progress", {"scanned": count})

    try:
        session = state.browser.session
        outcome = await session.open_likes_page()
        if outcome is not NavigationOutcome.OK:
            _fail_collecting_job(state, job_id, OUTCOME_MESSAGES[outcome])
            _end(state, job_id, ok=False, message=OUTCOME_MESSAGES[outcome])
            return
        result = await run_preview(
            session,
            state.engine,
            filters,
            account_id=account_id,
            max_scanned=max_scanned,
            job_id=job_id,
            on_progress=progress,
        )
        export_csv(
            pending_items(state.engine, job_id),
            state.settings.reports_dir / f"apercu-{job_id}.csv",
        )
        _end(
            state,
            job_id,
            ok=True,
            message=f"Aperçu prêt : {result.targeted} likes ciblés sur {result.scanned} lus.",
            result={"scanned": result.scanned, "targeted": result.targeted},
        )
    except (PreviewError, ApiConflict) as exc:
        _fail_collecting_job(state, job_id, str(exc))
        _end(state, job_id, ok=False, message=str(exc))
    except asyncio.CancelledError:
        _end(state, job_id, ok=False, message="Collecte interrompue avant la fin.")
        raise
    except Exception as exc:  # une erreur inattendue ne doit pas laisser le flux ouvert
        logger.exception("Collecte de l'aperçu n°%d en échec", job_id)
        _fail_collecting_job(state, job_id, f"Erreur inattendue : {exc}")
        _end(state, job_id, ok=False, message=f"Erreur inattendue : {exc}")


async def cleanup_task(
    state: ApiState,
    job_id: int,
    *,
    account_id: str | None,
    limit: int | None,
    control: CleanupControl,
) -> None:
    hub = state.hub
    hub.publish(job_id, "status", {"job": job_payload(state, job_id, running=True)})

    def batch_done(removed: int, total: int) -> None:
        hub.publish(job_id, "batch", {"removed": removed, "total": total})

    try:
        session = state.browser.session
        outcome = await session.open_likes_page()
        if outcome is not NavigationOutcome.OK:
            _end(state, job_id, ok=False, message=OUTCOME_MESSAGES[outcome])
            return
        result = await run_cleanup(
            session,
            state.engine,
            state.settings,
            job_id,
            account_id=account_id,
            max_unlikes=limit,
            control=control,
            on_batch=batch_done,
        )
        overview = job_overview(state.engine, job_id)
        if overview is not None and overview.status in (JobStatus.COMPLETED, JobStatus.STOPPED):
            write_report_files(state.engine, state.settings.reports_dir, job_id)
        _end(
            state,
            job_id,
            ok=result.reason in _SUCCESSFUL_STOPS,
            message=STOP_MESSAGES[result.reason],
            result={
                "reason": result.reason.value,
                "done": result.done,
                "failed": result.failed,
                "skipped": result.skipped,
                "remaining": result.remaining,
                "detail": result.detail,
            },
        )
    except (JobActionRefused, ApiConflict) as exc:
        _end(state, job_id, ok=False, message=str(exc))
    except asyncio.CancelledError:
        _end(state, job_id, ok=False, message="Nettoyage interrompu : il est en pause.")
        raise
    except Exception as exc:  # une erreur inattendue ne doit pas laisser le flux ouvert
        logger.exception("Nettoyage n°%d en échec", job_id)
        _end(state, job_id, ok=False, message=f"Erreur inattendue : {exc}")


def _end(
    state: ApiState,
    job_id: int,
    *,
    ok: bool,
    message: str,
    result: dict[str, Any] | None = None,
) -> None:
    state.hub.publish(
        job_id,
        "end",
        {
            "ok": ok,
            "message": message,
            "result": result,
            "job": job_payload(state, job_id, running=False),
        },
    )


def _fail_collecting_job(state: ApiState, job_id: int, reason: str) -> None:
    """Passe en échec une demande restée « en collecte » (run_preview l'a peut-être déjà fait)."""
    with Session(state.engine) as db:
        job = db.get(Job, job_id)
        still_collecting = job is not None and job.status is JobStatus.COLLECTING
    if still_collecting:
        fail_job(state.engine, job_id, reason)
