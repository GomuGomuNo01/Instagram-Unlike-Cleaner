"""Routes de la session navigateur et des données locales."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import StateDep
from app.api.schemas import DeletedOut, SessionStatusOut
from app.api.security import require_token
from app.api.state import ApiState
from app.browser.session import BrowserStartError
from app.core.db import init_db, make_engine
from app.core.logs import close_logging, setup_logging
from app.services.local_data import LocalDataError, delete_browser_profile, delete_local_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["session"], dependencies=[Depends(require_token)])


@router.post("/session/start", response_model=SessionStatusOut)
async def start_session(state: StateDep) -> SessionStatusOut:
    """Ouvre le navigateur visible sur instagram.com : l'utilisateur s'y connecte lui-même."""
    try:
        session_status = await state.browser.start()
    except BrowserStartError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return SessionStatusOut.build(session_status, busy=state.runner.busy)


@router.get("/session/status", response_model=SessionStatusOut)
async def session_status(state: StateDep) -> SessionStatusOut:
    """Indique si le navigateur est ouvert et si l'utilisateur est connecté (à interroger
    régulièrement pendant la connexion manuelle)."""
    return SessionStatusOut.build(await state.browser.status(), busy=state.runner.busy)


@router.delete("/session", response_model=DeletedOut)
async def delete_session(state: StateDep) -> DeletedOut:
    """Ferme le navigateur et supprime son profil local, donc la session Instagram."""
    _ensure_idle(state)
    await state.browser.close()
    try:
        deleted = delete_browser_profile(state.settings)
    except LocalDataError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return DeletedOut(deleted=[str(state.settings.browser_profile_dir)] if deleted else [])


@router.delete("/data", response_model=DeletedOut)
async def delete_data(state: StateDep) -> DeletedOut:
    """Supprime toutes les données locales d'IUC (profil, base, rapports, diagnostics,
    journaux), puis repart d'une base vide."""
    _ensure_idle(state)
    await state.browser.close()
    state.engine.dispose()
    logging_was_open = close_logging()
    try:
        deleted = delete_local_data(state.settings)
    except LocalDataError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    finally:
        state.settings.ensure_dirs()
        state.engine = make_engine(state.settings.db_path)
        init_db(state.engine)
        if logging_was_open:
            setup_logging(state.settings)
    logger.warning("Données locales supprimées depuis l'interface (%d éléments)", len(deleted))
    return DeletedOut(deleted=[str(path) for path in deleted])


def _ensure_idle(state: ApiState) -> None:
    if state.runner.busy:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Une collecte ou un nettoyage est en cours : mets-le en pause d'abord.",
        )
