"""Routes de mise à jour de l'application Windows (voir app/services/update.py)."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import StateDep
from app.api.schemas import UpdateInstallOut, UpdateOut
from app.api.security import require_token
from app.services.update import UpdateError, UpdateRefused

# Délai avant la fermeture d'IUC, le temps que l'interface reçoive la réponse.
SHUTDOWN_DELAY = 1.0

router = APIRouter(prefix="/api", tags=["mise à jour"], dependencies=[Depends(require_token)])


@router.get("/update", response_model=UpdateOut)
async def update_status(state: StateDep) -> UpdateOut:
    """Indique si une version plus récente est publiée sur GitHub (lecture seule, vérifiée
    au plus toutes les six heures)."""
    return UpdateOut.build(await state.updater.status())


@router.post("/update/install", response_model=UpdateInstallOut, status_code=202)
async def install_update(state: StateDep) -> UpdateInstallOut:
    """Télécharge l'installeur de la dernière version et vérifie son empreinte SHA-256, met
    en pause un nettoyage en cours, lance l'installeur puis ferme IUC : l'installeur remplace
    l'application et la relance. Les données locales sont gardées."""
    try:
        version = await state.updater.install(before_launch=state.runner.cancel)
    except UpdateRefused as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except UpdateError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    if state.shutdown is not None:
        asyncio.get_running_loop().call_later(SHUTDOWN_DELAY, state.shutdown)
    return UpdateInstallOut(version=version)
