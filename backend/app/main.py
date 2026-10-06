"""Point d'entrée de l'API locale (FastAPI). Lancement : `iuc serve`.

L'API n'écoute que sur 127.0.0.1 et n'accepte que les hôtes 127.0.0.1 et localhost, plus,
dans GitHub Codespaces, l'adresse propre au Codespace (voir core/codespaces.py). Seul le
navigateur piloté par Playwright contacte Instagram ; l'API et la CLI passent par les mêmes
services.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api import jobs, session
from app.api.security import TOKEN_HEADER, SecurityHeadersMiddleware, new_token
from app.api.state import ApiConflict, ApiState, BrowserFactory, BrowserManager
from app.browser.session import BrowserSession
from app.core.codespaces import desktop_url, forwarded_host
from app.core.config import Settings, get_settings
from app.core.db import init_db, make_engine
from app.frontend import mount_frontend

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


def create_app(
    settings: Settings | None = None,
    *,
    token: str | None = None,
    browser_factory: BrowserFactory | None = None,
) -> FastAPI:
    """Construit l'application. `browser_factory` permet aux tests de fournir un navigateur
    branché sur une fausse version d'Instagram."""
    settings = settings or get_settings()
    settings.ensure_dirs()
    engine = make_engine(settings.db_path)
    init_db(engine)
    state = ApiState(
        settings=settings,
        engine=engine,
        token=token or new_token(),
        browser=BrowserManager(settings, browser_factory or BrowserSession),
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        # Arrêt du serveur : une tâche en cours est interrompue (un nettoyage passe en pause).
        await state.runner.cancel()
        await state.browser.close()
        state.engine.dispose()

    app = FastAPI(
        title="IUC – API locale",
        version="0.1.0",
        description=(
            "API locale d'Instagram Unlike Cleaner. Toutes les routes /api exigent le jeton "
            f"affiché par `iuc serve`, dans l'en-tête {TOKEN_HEADER}."
        ),
        lifespan=lifespan,
        # Swagger UI se charge depuis un CDN : seulement si API_DOCS est activé.
        docs_url="/docs" if settings.api_docs else None,
        redoc_url=None,
    )
    app.state.iuc = state
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=[TOKEN_HEADER, "Content-Type"],
    )
    # Refuse tout autre en-tête Host (protection contre le « DNS rebinding »).
    codespace_host = forwarded_host(settings.api_port)
    allowed_hosts = [*ALLOWED_HOSTS, codespace_host] if codespace_host else ALLOWED_HOSTS
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    # Ajouté en dernier, donc exécuté en premier : même un refus porte ces en-têtes.
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(ApiConflict)
    async def conflict(_request: Request, exc: ApiConflict) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    app.include_router(session.router)
    app.include_router(jobs.router)
    # En dernier : toute autre adresse renvoie l'interface (application à page unique).
    mount_frontend(app, settings.frontend_dist, state.token, desktop=desktop_url())
    return app
