"""Routes des nettoyages : aperçu, sélection, lancement, contrôle, progression et rapport."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import Field

from app.api.deps import StateDep
from app.api.schemas import ItemOut, ItemsPage, ItemsPatch, ItemsPatchOut, JobOut, StartRequest
from app.api.security import require_token
from app.api.state import ApiState
from app.api.tasks import cleanup_task, job_payload, preview_task
from app.models.schemas import CleanupFilters
from app.models.tables import ItemStatus, JobStatus
from app.services.cleanup import CleanupControl
from app.services.jobs import (
    RUNNABLE,
    STATUS_LABELS,
    JobActionRefused,
    JobOverview,
    create_job,
    job_overview,
    list_items,
    list_jobs,
    set_excluded,
    stop_job,
)
from app.services.report import build_report, write_report_files

# Commentaire SSE envoyé régulièrement pour garder la connexion ouverte.
KEEPALIVE_SECONDS = 15.0

router = APIRouter(prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(require_token)])


class JobCreate(CleanupFilters):
    """Critères du nettoyage, et limite facultative de vignettes à lire (pour un essai)."""

    max_scanned: int | None = Field(default=None, ge=1)


@router.get("", response_model=list[JobOut])
async def get_jobs(state: StateDep) -> list[JobOut]:
    return [_job_out(state, overview) for overview in list_jobs(state.engine)]


@router.post("", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_cleanup(body: JobCreate, state: StateDep) -> JobOut:
    """Crée un nettoyage et lance en arrière-plan la collecte de son aperçu (rien n'est
    retiré). Suivre l'avancement avec GET /api/jobs/{id}/events."""
    _ensure_idle(state)
    session_status = await state.browser.status()
    if not session_status.logged_in:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Connecte-toi d'abord à Instagram dans la fenêtre du navigateur.",
        )
    filters = CleanupFilters.model_validate(body.model_dump(exclude={"max_scanned"}))
    job_id = create_job(state.engine, filters, session_status.account_id)

    async def work(control: CleanupControl) -> None:
        await preview_task(
            state,
            job_id,
            filters,
            account_id=session_status.account_id,
            max_scanned=body.max_scanned,
            _control=control,
        )

    state.runner.launch(job_id, "preview", work)
    return _job_out(state, _overview_or_404(state, job_id))


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, state: StateDep) -> JobOut:
    return _job_out(state, _overview_or_404(state, job_id))


@router.get("/{job_id}/items", response_model=ItemsPage)
async def get_items(
    job_id: int,
    state: StateDep,
    item_status: Annotated[ItemStatus | None, Query(alias="status")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> ItemsPage:
    """Likes ciblés, dans l'ordre de la grille, page par page."""
    _overview_or_404(state, job_id)
    items, total = list_items(state.engine, job_id, status=item_status, offset=offset, limit=limit)
    return ItemsPage(
        items=[ItemOut.build(item) for item in items], total=total, offset=offset, limit=limit
    )


@router.patch("/{job_id}/items", response_model=ItemsPatchOut)
async def patch_items(job_id: int, body: ItemsPatch, state: StateDep) -> ItemsPatchOut:
    """Décoche (exclut) ou recoche des likes de l'aperçu."""
    _overview_or_404(state, job_id)
    try:
        changed = set_excluded(
            state.engine, job_id, item_ids=body.item_ids, restore=not body.excluded
        )
    except JobActionRefused as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return ItemsPatchOut(changed=changed, job=_job_out(state, _overview_or_404(state, job_id)))


@router.post("/{job_id}/start", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def start_cleanup(job_id: int, state: StateDep, body: StartRequest | None = None) -> JobOut:
    """Lance les unlikes. Le premier lancement valide l'aperçu."""
    return await _launch_cleanup(state, job_id, body, allowed=RUNNABLE)


@router.post("/{job_id}/resume", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def resume_cleanup(job_id: int, state: StateDep, body: StartRequest | None = None) -> JobOut:
    """Reprend un nettoyage en pause, là où il s'était arrêté."""
    return await _launch_cleanup(
        state, job_id, body, allowed=frozenset({JobStatus.PAUSED, JobStatus.RUNNING})
    )


@router.post("/{job_id}/pause", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def pause_cleanup(job_id: int, state: StateDep) -> JobOut:
    """Demande une pause : le lot en cours se termine, est contrôlé, puis tout s'arrête."""
    running = state.runner.running_for(job_id)
    if running is None or running.kind != "cleanup":
        raise HTTPException(status.HTTP_409_CONFLICT, "Ce nettoyage n'est pas en cours.")
    running.control.request_pause()
    return _job_out(state, _overview_or_404(state, job_id))


@router.post("/{job_id}/stop", response_model=JobOut)
async def stop_cleanup(job_id: int, state: StateDep) -> JobOut:
    """Arrête définitivement un nettoyage : les likes non traités ne seront pas retirés.
    En cours d'exécution, l'arrêt a lieu après le lot en cours ; une collecte d'aperçu en
    cours est interrompue."""
    _overview_or_404(state, job_id)
    running = state.runner.running_for(job_id)
    if running is not None and running.kind == "cleanup":
        running.control.request_stop()
    elif running is not None:
        await state.runner.cancel()
    else:
        try:
            stop_job(state.engine, job_id)
        except JobActionRefused as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _job_out(state, _overview_or_404(state, job_id))


@router.get("/{job_id}/events")
async def job_events(job_id: int, request: Request, state: StateDep) -> StreamingResponse:
    """Progression en direct (Server-Sent Events) : « snapshot », puis « status »,
    « progress », « batch » et enfin « end ». Le jeton peut être passé en paramètre
    `token`, car EventSource ne sait pas envoyer d'en-tête."""
    _overview_or_404(state, job_id)
    return StreamingResponse(
        _event_stream(request, state, job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{job_id}/report", response_model=None)
async def job_report(
    job_id: int,
    state: StateDep,
    report_format: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
) -> dict[str, Any] | Response:
    """Rapport du nettoyage, en JSON ou en CSV ; les fichiers sont aussi écrits dans
    DATA_DIR/reports."""
    _overview_or_404(state, job_id)
    csv_path, _ = write_report_files(state.engine, state.settings.reports_dir, job_id)
    if report_format == "csv":
        return FileResponse(csv_path, media_type="text/csv", filename=csv_path.name)
    return build_report(state.engine, job_id).to_dict()


async def _launch_cleanup(
    state: ApiState, job_id: int, body: StartRequest | None, *, allowed: frozenset[JobStatus]
) -> JobOut:
    overview = _overview_or_404(state, job_id)
    if overview.status not in allowed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Le nettoyage n°{job_id} est « {STATUS_LABELS[overview.status]} » : "
            "il ne peut pas être lancé.",
        )
    _ensure_idle(state)
    session_status = await state.browser.status()
    if not session_status.logged_in:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Connecte-toi d'abord à Instagram dans la fenêtre du navigateur.",
        )
    if overview.account_id and overview.account_id != session_status.account_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Le nettoyage n°{job_id} a été préparé sur un autre compte Instagram.",
        )
    limit = body.limit if body else None

    async def work(control: CleanupControl) -> None:
        await cleanup_task(
            state, job_id, account_id=session_status.account_id, limit=limit, control=control
        )

    state.runner.launch(job_id, "cleanup", work)
    return _job_out(state, overview)


async def _event_stream(request: Request, state: ApiState, job_id: int) -> AsyncIterator[str]:
    async with state.hub.subscribe(job_id) as (history, queue):
        yield _sse("snapshot", {"job": job_payload(state, job_id)})
        # Seuls les événements de la dernière tâche sont rejoués.
        starts = [index for index, event in enumerate(history) if event.type == "status"]
        replay = history[starts[-1] :] if starts else []
        last_id = 0
        for event in replay:
            last_id = event.id
            yield _sse(event.type, event.data, event.id)
        if state.runner.running_for(job_id) is None:
            if not replay or replay[-1].type != "end":
                yield _sse(
                    "end",
                    {
                        "ok": True,
                        "message": "Aucune tâche en cours pour ce nettoyage.",
                        "result": None,
                        "job": job_payload(state, job_id),
                    },
                )
            return
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
            except TimeoutError:
                if await request.is_disconnected():
                    return
                yield ": keepalive\n\n"
                continue
            if event.id <= last_id:
                continue
            yield _sse(event.type, event.data, event.id)
            if event.type == "end":
                return


def _sse(event_type: str, data: dict[str, Any], event_id: int | None = None) -> str:
    lines = [f"id: {event_id}"] if event_id is not None else []
    lines += [f"event: {event_type}", f"data: {json.dumps(data, ensure_ascii=False)}"]
    return "\n".join(lines) + "\n\n"


def _overview_or_404(state: ApiState, job_id: int) -> JobOverview:
    overview = job_overview(state.engine, job_id)
    if overview is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aucun nettoyage n°{job_id}.")
    return overview


def _job_out(state: ApiState, overview: JobOverview) -> JobOut:
    return JobOut.build(overview, running=state.runner.running_for(overview.id) is not None)


def _ensure_idle(state: ApiState) -> None:
    if state.runner.busy:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Une collecte ou un nettoyage est déjà en cours : attends sa fin ou mets-le en pause.",
        )
