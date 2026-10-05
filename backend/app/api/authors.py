"""Comptes connus, pour aider à cibler ou protéger des comptes dans les critères."""

from fastapi import APIRouter, Depends

from app.api.deps import StateDep
from app.api.schemas import AuthorOut
from app.api.security import require_token
from app.services.jobs import known_authors

router = APIRouter(prefix="/api", tags=["authors"], dependencies=[Depends(require_token)])


@router.get("/authors", response_model=list[AuthorOut])
async def get_authors(state: StateDep) -> list[AuthorOut]:
    """Comptes dont tu as aimé des publications, d'après tes aperçus déjà collectés (ceux du
    compte connecté s'il est connu), du plus fréquent au moins fréquent. Liste vide avant le
    premier aperçu."""
    account_id = (await state.browser.status()).account_id
    return [
        AuthorOut(author=author, likes=likes)
        for author, likes in known_authors(state.engine, account_id)
    ]
